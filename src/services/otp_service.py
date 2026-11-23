"""
Applicant OTP Service and Delivery Provider Abstraction
AI Powered Smart Hospital Referral System - Phase 1 Task 1D

Manages cryptographic 6-digit OTP generation, delivery, cooldown rate-limiting,
attempt limits, secure hashing (SHA-256), and verification token lifecycles.
Supports simulated development/testing provider and pluggable production gateways.
"""

import os
import re
import hmac
import time
import secrets
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from src.database.pg_models import VerificationToken
from src.services.registration_exceptions import ValidationError

logger = logging.getLogger("otp_service")
security_logger = logging.getLogger("sih.security.audit")

OTP_EXPIRY_MINUTES = 10
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 3
VALID_OTP_PURPOSES = frozenset({"REGISTRATION_OTP", "LOGIN_OTP", "PASSWORD_RESET_OTP", "PORTAL_ACCESS_OTP"})


# ============================================================
# OTP DELIVERY PROVIDER ABSTRACTION
# ============================================================

class BaseOTPProvider(ABC):
    """Abstract interface for OTP delivery across channels (Email, SMS)."""

    @abstractmethod
    def send_otp(self, contact_target: str, channel: str, otp: str, purpose: str) -> bool:
        """Send OTP to the recipient target. Returns True on success, False on failure."""
        pass


class SimulatedOTPProvider(BaseOTPProvider):
    """
    Simulated provider for development and automated test environments.
    Stores sent OTPs in memory for test assertions without exposing them in logs.
    """

    def __init__(self):
        self._sent_otps: Dict[str, Dict[str, Any]] = {}

    def send_otp(self, contact_target: str, channel: str, otp: str, purpose: str) -> bool:
        normalized_target = contact_target.strip().lower()
        self._sent_otps[normalized_target] = {
            "otp": otp,
            "channel": channel,
            "purpose": purpose,
            "sent_at": time.time(),
        }
        # Mask target for safe logging: e.g. a***@example.com
        masked_target = _mask_contact_target(contact_target)
        logger.info("Simulated OTP generated for %s via %s (purpose=%s)", masked_target, channel, purpose)
        return True

    def get_last_simulated_otp(self, contact_target: str) -> Optional[str]:
        """Test helper to retrieve the last simulated OTP for automated assertion."""
        normalized_target = contact_target.strip().lower()
        record = self._sent_otps.get(normalized_target)
        return record["otp"] if record else None

    def clear(self):
        self._sent_otps.clear()


class ConfigurableOTPProvider(BaseOTPProvider):
    """
    Configurable production OTP delivery provider.
    Routes email OTPs through the configured system email provider (SMTP / Simulated),
    and SMS OTPs through configured production SMS gateways.
    """

    def __init__(self):
        self.provider_type = os.getenv("SIH_OTP_PROVIDER", "SIMULATED").upper().strip()
        self._simulated = SimulatedOTPProvider()

    def get_last_simulated_otp(self, contact_target: str) -> Optional[str]:
        return self._simulated.get_last_simulated_otp(contact_target)

    def clear(self):
        self._simulated.clear()

    def send_otp(self, contact_target: str, channel: str, otp: str, purpose: str) -> bool:
        masked_target = _mask_contact_target(contact_target)
        env = os.getenv("ENVIRONMENT", os.getenv("SIH_ENV", "development")).lower().strip()
        is_prod = env in ("production", "prod")

        self._simulated.send_otp(contact_target, channel, otp, purpose)

        if self.provider_type == "SIMULATED":
            if is_prod:
                raise RuntimeError("CRITICAL SECURITY ERROR: Simulated OTP provider cannot be used in production.")
            return True

        elif self.provider_type == "CONSOLE":
            if is_prod:
                raise RuntimeError("CRITICAL SECURITY ERROR: Console OTP delivery is forbidden in production.")
            logger.info("Console OTP sent to %s via %s", masked_target, channel)
            return True

        # Production / Configured Email delivery
        if channel == "EMAIL":
            from src.services.email_service import get_email_provider, EmailDeliveryError
            email_provider = get_email_provider()
            purpose_labels = {
                "REGISTRATION_OTP": "Portal Registration",
                "LOGIN_OTP": "Login Verification",
                "PASSWORD_RESET_OTP": "Password Reset",
                "PORTAL_ACCESS_OTP": "Portal Access",
            }
            purpose_label = purpose_labels.get(purpose, purpose)
            subject = f"Your Verification Code ({purpose_label}) - SWASTHYA SAMANVAY"
            body_text = f"""Dear User,

Your single-use 6-digit verification code is: {otp}

This code was requested for: {purpose_label}.
It is valid for 10 minutes and can only be used once.

For security reasons, do not share this verification code with anyone.

Regards,
SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform
Support: pawanbussiness108@gmail.com
"""
            try:
                success = email_provider.send_email(
                    to_email=contact_target,
                    subject=subject,
                    body_text=body_text,
                )
                if not success:
                    logger.error("Email provider returned False delivering OTP to %s", masked_target)
                    return False
                logger.info("Dispatched OTP email to %s (purpose: %s)", masked_target, purpose)
                return True
            except EmailDeliveryError as exc:
                logger.error("Email delivery failed for OTP to %s: %s", masked_target, exc)
                raise ValidationError(f"Failed to deliver OTP email: {exc}") from exc

        elif channel == "SMS":
            if is_prod:
                # In production, require actual external SMS gateway adapter
                logger.error("SMS gateway not configured in production for target %s", masked_target)
                raise ValidationError("SMS OTP delivery gateway is not configured for production.")
            logger.info("SMS OTP dispatched to %s via provider '%s'", masked_target, self.provider_type)
            return True

        return False


def _mask_contact_target(target: str) -> str:
    """Mask email or phone for secure logging."""
    target = target.strip()
    if "@" in target:
        user, domain = target.split("@", 1)
        masked_user = user[0] + "***" if len(user) > 1 else "*"
        return f"{masked_user}@{domain}"
    elif len(target) >= 10:
        return f"{target[:2]}******{target[-2:]}"
    return "***"


# Global singleton provider instance
_EXPLICIT_PROVIDER: Optional[BaseOTPProvider] = None
_SIMULATED_INSTANCE: Optional[SimulatedOTPProvider] = None


def get_otp_provider() -> BaseOTPProvider:
    """
    Retrieve active OTP provider singleton.
    In production (SIH_ENV=production or ENVIRONMENT=production) or when
    SIH_OTP_PROVIDER is set to EMAIL, selects ConfigurableOTPProvider.
    Otherwise defaults to in-memory SimulatedOTPProvider for development/testing.
    """
    global _EXPLICIT_PROVIDER, _SIMULATED_INSTANCE
    if _EXPLICIT_PROVIDER is not None:
        return _EXPLICIT_PROVIDER

    provider_env = os.getenv("SIH_OTP_PROVIDER", "SIMULATED").upper().strip()
    env = os.getenv("ENVIRONMENT", os.getenv("SIH_ENV", "development")).lower().strip()
    is_prod = env in ("production", "prod")

    if is_prod or provider_env != "SIMULATED":
        return ConfigurableOTPProvider()

    if _SIMULATED_INSTANCE is None:
        _SIMULATED_INSTANCE = SimulatedOTPProvider()
    return _SIMULATED_INSTANCE


def set_otp_provider(provider: Optional[BaseOTPProvider]):
    """Override active OTP provider (used in tests)."""
    global _EXPLICIT_PROVIDER
    _EXPLICIT_PROVIDER = provider


# ============================================================
# OTP SERVICE
# ============================================================

class OTPService:
    """
    Manages OTP generation, verification, database persistence, and attempt limits.
    """

    def __init__(self, session: Session, provider: Optional[BaseOTPProvider] = None):
        self.session = session
        self.provider = provider or get_otp_provider()

    def request_otp(
        self,
        contact_target: str,
        channel: str = "EMAIL",
        purpose: str = "PORTAL_ACCESS_OTP",
        application_id: Optional[str] = None,
        application_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request a 6-digit OTP for the specified contact target and purpose:
        - Validates format (email / phone)
        - Validates cooldown against recent unexpired tokens
        - Binds to application_id if supplied or looked up via application_number
        - Persists hashed OTP in verification_tokens table
        - Dispatches OTP through configured provider
        - Returns token metadata (without exposing raw OTP)
        """
        target = contact_target.strip().lower()

        if purpose not in VALID_OTP_PURPOSES:
            raise ValidationError(
                f"Invalid OTP purpose '{purpose}'. Allowed: {', '.join(sorted(VALID_OTP_PURPOSES))}."
            )

        # Resolve application binding
        bound_app_id = application_id
        if application_number and not bound_app_id:
            from src.database.pg_models import RegistrationApplication
            app = self.session.query(RegistrationApplication).filter_by(application_number=application_number.strip()).first()
            if app:
                bound_app_id = app.application_id
                # Validate target belongs to application
                if target != app.applicant_email.lower() and target != app.applicant_phone:
                    raise ValidationError("Contact target does not match the designated applicant for this application.")

        # Format validation
        if channel == "EMAIL":
            if not re.match(r"^[\w\.\+\-]+@[\w\-]+\.[\w\.\-]+$", target):
                raise ValidationError("Invalid applicant_email format.")
        elif channel == "SMS":
            digits = re.sub(r"\D", "", target)
            if len(digits) < 10:
                raise ValidationError("Invalid phone number format for SMS OTP.")
        else:
            raise ValidationError("Unsupported token_channel. Allowed: 'EMAIL', 'SMS'.")

        now = datetime.now(timezone.utc)

        # Check for active cooldown on existing unexpired token
        recent_token = (
            self.session.query(VerificationToken)
            .filter(
                VerificationToken.contact_target == target,
                VerificationToken.token_purpose == purpose,
                VerificationToken.is_verified == False,
                VerificationToken.expires_at > now,
            )
            .order_by(VerificationToken.id.desc())
            .first()
        )

        if recent_token:
            token_resend_at = recent_token.resend_available_at
            if token_resend_at.tzinfo is None:
                token_resend_at = token_resend_at.replace(tzinfo=timezone.utc)

            if token_resend_at > now:
                remaining_sec = int((token_resend_at - now).total_seconds())
                raise ValidationError(
                    f"OTP was recently sent. Please wait {remaining_sec} seconds before requesting a new OTP."
                )

        # Generate cryptographically secure 6-digit numeric OTP
        raw_otp = f"{secrets.randbelow(900000) + 100000}"
        token_hash = hashlib.sha256(raw_otp.encode("utf-8")).hexdigest()
        token_id = f"VTOK_{secrets.token_hex(16)}"

        vtoken = VerificationToken(
            token_id=token_id,
            contact_target=target,
            token_channel=channel,
            token_purpose=purpose,
            token_hash=token_hash,
            attempt_count=0,
            max_attempts=OTP_MAX_ATTEMPTS,
            is_verified=False,
            application_id=bound_app_id,
            expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
            resend_available_at=now + timedelta(seconds=OTP_RESEND_COOLDOWN_SECONDS),
        )

        self.session.add(vtoken)
        self.session.flush()

        # Dispatch OTP via provider
        dispatched = self.provider.send_otp(target, channel, raw_otp, purpose)
        if dispatched is False:
            raise ValidationError("Failed to deliver verification code to the designated contact target. Please try again.")

        return {
            "token_id": token_id,
            "contact_target": target,
            "channel": channel,
            "application_id": bound_app_id,
            "resend_available_in_seconds": OTP_RESEND_COOLDOWN_SECONDS,
            "expires_in_seconds": OTP_EXPIRY_MINUTES * 60,
        }

    def verify_otp(
        self,
        token_id: str,
        otp: str,
        purpose: str = "PORTAL_ACCESS_OTP",
        expected_application_id: Optional[str] = None,
    ) -> str:
        """
        Verify a submitted OTP against its verification token:
        - Validates token exists, is not expired, and purpose matches
        - Enforces application binding (an OTP for one application cannot authorize another)
        - Enforces max attempt limits
        - Uses constant-time digest comparison
        - Marks token consumed (single-use)
        - Returns verified contact_target on success
        """
        if purpose not in VALID_OTP_PURPOSES:
            raise ValidationError(
                f"Invalid OTP purpose '{purpose}'. Allowed: {', '.join(sorted(VALID_OTP_PURPOSES))}."
            )

        vtoken = (
            self.session.query(VerificationToken)
            .filter_by(token_id=token_id.strip())
            .first()
        )
        if not vtoken:
            raise ValidationError("Invalid or non-existent verification token.")

        if vtoken.token_purpose != purpose:
            raise ValidationError(f"Token purpose mismatch: expected '{purpose}'.")

        # Application binding verification
        if vtoken.application_id and expected_application_id:
            if vtoken.application_id != expected_application_id:
                raise ValidationError("Verification token is bound to a different application.")
        elif vtoken.application_id and not expected_application_id:
            raise ValidationError("This token requires application identity verification.")

        if vtoken.is_verified:
            raise ValidationError("This verification token has already been consumed.")

        now = datetime.now(timezone.utc)
        token_exp = vtoken.expires_at
        if token_exp.tzinfo is None:
            token_exp = token_exp.replace(tzinfo=timezone.utc)

        if token_exp < now:
            raise ValidationError("Verification OTP has expired. Please request a new OTP.")

        if vtoken.attempt_count >= vtoken.max_attempts:
            raise ValidationError("Maximum verification attempts exceeded. Please request a new OTP.")

        # Increment attempt count
        vtoken.attempt_count += 1

        # Secure constant-time hash comparison
        input_hash = hashlib.sha256(otp.strip().encode("utf-8")).hexdigest()
        is_valid = hmac.compare_digest(vtoken.token_hash, input_hash)

        if not is_valid:
            self.session.flush()
            remaining = vtoken.max_attempts - vtoken.attempt_count
            if remaining <= 0:
                raise ValidationError("Invalid OTP. Maximum attempts exceeded. Please request a new OTP.")
            raise ValidationError(f"Invalid OTP. {remaining} attempt(s) remaining.")

        # Successfully verified: mark single-use consumption
        vtoken.is_verified = True
        vtoken.verified_at = now
        self.session.flush()

        return vtoken.contact_target
