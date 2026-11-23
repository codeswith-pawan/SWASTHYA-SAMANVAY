"""
Operational Account Provisioning & Activation Service
AI Powered Smart Hospital Referral System - Phase 1 Task 1E

Provides:
- Role & geographic provisioning triggered ONLY by final Central approval
- State (STATE_ADMIN), District (DISTRICT_ADMIN), and Hospital (HOSPITAL + Hospital entity) provisioning
- Duplicate provisioning prevention and idempotency
- Single-use, cryptographically secure activation tokens (SHA-256 hashed storage)
- Secure password creation with PBKDF2-HMAC-SHA256 (100,000 iterations)
- Post-commit email dispatch ensuring database transaction safety
"""

import re
import os
import hmac
import secrets
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from src.database.pg_models import (
    RegistrationApplication,
    AccountActivationToken,
    PasswordResetToken,
    RegistrationEmailOutbox,
    User,
    Hospital,
    Role,
)
from src.auth.auth_store import hash_password
from src.auth.rate_limiter import revoke_user_sessions
from src.services.email_service import get_email_provider, BaseEmailProvider
from src.services.email_outbox_service import EmailOutboxService
from src.services.registration_exceptions import (
    RegistrationServiceError,
    ValidationError,
    ApplicationNotFoundError,
    IneligibleForApprovalError,
    SelfApprovalError,
)

logger = logging.getLogger(__name__)

ACTIVATION_TOKEN_EXPIRY_HOURS = 72


class ProvisioningError(RegistrationServiceError):
    """Raised when operational account provisioning fails."""
    pass


class ActivationTokenError(RegistrationServiceError):
    """Raised when activation token is invalid, expired, or already consumed."""
    pass


class PasswordComplexityError(ValidationError):
    """Raised when proposed password does not satisfy complexity requirements."""
    pass


def validate_password_complexity(password: str) -> None:
    """
    Validate that password meets security complexity standards:
    - Minimum 8 characters
    - At least one uppercase letter [A-Z]
    - At least one lowercase letter [a-z]
    - At least one digit [0-9]
    - At least one special symbol
    """
    if not password or len(password) < 8:
        raise PasswordComplexityError("Password must be at least 8 characters long.")
    if not re.search(r"[A-Z]", password):
        raise PasswordComplexityError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", password):
        raise PasswordComplexityError("Password must contain at least one lowercase letter.")
    if not re.search(r"[0-9]", password):
        raise PasswordComplexityError("Password must contain at least one numerical digit.")
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        raise PasswordComplexityError("Password must contain at least one special character.")


class AccountProvisioningService:
    """
    Manages operational account provisioning, activation token lifecycle,
    and post-commit email dispatch.
    """

    def __init__(self, session: Session, email_provider: Optional[BaseEmailProvider] = None):
        self.session = session
        self.email_provider = email_provider or get_email_provider()

    def _get_base_activation_url(self, explicit_url: Optional[str] = None) -> str:
        """Derive base activation URL from explicit argument or global portal_base_url setting."""
        if explicit_url:
            return explicit_url.rstrip("/")
        env_override = os.getenv("PORTAL_BASE_URL") or os.getenv("SIH_PORTAL_BASE_URL")
        if env_override and env_override.strip():
            return f"{env_override.strip().rstrip('/')}/activate"
        env = (os.getenv("ENVIRONMENT") or os.getenv("SIH_ENV") or "").lower()
        if env in ("production", "prod", "demo", "staging") or os.getenv("RENDER"):
            return "https://swasthya-samanvay-ujxm.vercel.app/activate"
        try:
            from src.config import get_settings
            return f"{get_settings().portal_base_url}/activate"
        except Exception:
            return "http://localhost:3000/activate"

    def _get_base_reset_url(self, explicit_url: Optional[str] = None) -> str:
        """Derive base password reset URL from explicit argument or global portal_base_url setting."""
        if explicit_url:
            return explicit_url.rstrip("/")
        env_override = os.getenv("PORTAL_BASE_URL") or os.getenv("SIH_PORTAL_BASE_URL")
        if env_override and env_override.strip():
            return f"{env_override.strip().rstrip('/')}/reset-password"
        env = (os.getenv("ENVIRONMENT") or os.getenv("SIH_ENV") or "").lower()
        if env in ("production", "prod", "demo", "staging") or os.getenv("RENDER"):
            return "https://swasthya-samanvay-ujxm.vercel.app/reset-password"
        try:
            from src.config import get_settings
            return f"{get_settings().portal_base_url}/reset-password"
        except Exception:
            return "http://localhost:3000/reset-password"

    # ============================================================
    # 1. ACCOUNT PROVISIONING (POST FINAL APPROVAL)
    # ============================================================

    def provision_account(
        self,
        application_id: str,
        reviewer_user: Dict[str, Any],
        client_ip: Optional[str] = None,
        base_activation_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Provision operational account for an approved application.
        Strictly enforces:
        1. Application is in APPROVED status.
        2. Reviewer is not the applicant (self-approval prevention).
        3. Idempotent: duplicate requests return existing provisioned account.
        4. Atomic transaction safety with row locking and partial unique constraint protection.
        5. Transactional email outbox recording.
        """
        try:
            app = (
                self.session.query(RegistrationApplication)
                .filter_by(application_id=application_id)
                .with_for_update()
                .first()
            )
        except Exception:
            app = (
                self.session.query(RegistrationApplication)
                .filter_by(application_id=application_id)
                .first()
            )

        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        # 1. Enforce final approval status
        if app.status != "APPROVED":
            raise IneligibleForApprovalError(
                f"Operational account can only be provisioned after final Central Government approval. Current status: '{app.status}'."
            )

        # 2. Self-approval prevention with strict normalization across email, user_id, username, and nodal identity
        reviewer_user_id = str(reviewer_user.get("user_id") or "").strip().lower()
        reviewer_username = str(reviewer_user.get("username") or "").strip().lower()
        reviewer_email = (reviewer_user.get("email") or "").strip().lower()
        app_email = (app.applicant_email or "").strip().lower()
        app_nodal = (app.nodal_officer_name or "").strip().lower()

        if app_email and (reviewer_email == app_email or reviewer_user_id == app_email or reviewer_username == app_email):
            raise SelfApprovalError("Self-approval violation: applicant cannot provision their own operational account.")
        if app_nodal and (reviewer_user_id == app_nodal or reviewer_username == app_nodal or reviewer_email == app_nodal):
            raise SelfApprovalError("Self-approval violation: applicant cannot provision their own operational account.")

        # 3. Idempotency Check: if user already provisioned for this application
        existing_user = (
            self.session.query(User)
            .filter_by(application_id=app.application_id)
            .first()
        )
        if existing_user:
            return self._build_existing_provisioning_result(app, existing_user, base_activation_url=base_activation_url)

        # 4. Provision based on applicant_type with collision & concurrency safety
        try:
            if app.applicant_type == "STATE":
                provisioned_data = self._provision_state_admin(app)
            elif app.applicant_type == "DISTRICT":
                provisioned_data = self._provision_district_admin(app)
            elif app.applicant_type == "HOSPITAL":
                provisioned_data = self._provision_hospital_admin(app)
            else:
                raise ProvisioningError(f"Unsupported applicant_type '{app.applicant_type}'.")

            user = provisioned_data["user"]
            app.provisioned_entity_id = user.user_id
            self.session.flush()
        except IntegrityError as exc:
            logger.info("Concurrent provisioning detected or collision occurred for '%s': %s", app.application_number, exc)
            self.session.rollback()
            existing_user = self.session.query(User).filter_by(application_id=app.application_id).first()
            if existing_user:
                return self._build_existing_provisioning_result(app, existing_user, base_activation_url=base_activation_url)
            raise

        # 5. Issue cryptographic one-time activation token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        activation_token_record = AccountActivationToken(
            activation_token_id=f"ACT_{secrets.token_hex(16)}",
            application_id=app.application_id,
            user_id=user.user_id,
            token_hash=token_hash,
            is_consumed=False,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS),
        )
        self.session.add(activation_token_record)
        self.session.flush()

        # 6. Enqueue activation email in transactional outbox inside the same database transaction
        role_titles = {
            "STATE_ADMIN": "State Health Administrator",
            "DISTRICT_ADMIN": "District Health Administrator",
            "HOSPITAL": "Hospital Operational Administrator",
        }
        role_title = role_titles.get(user.role_id, "Operational Administrator")
        outbox_svc = EmailOutboxService(self.session, self.email_provider)
        base_act = self._get_base_activation_url(base_activation_url)
        outbox_record = outbox_svc.enqueue_email(
            event_type="ACCOUNT_ACTIVATION",
            recipient_email=app.applicant_email,
            recipient_name=app.applicant_name,
            subject=f"Official Portal Account Activation: {role_title} ({app.application_number})",
            payload={
                "activation_link": f"{base_act}?token={raw_token}",
                "role_title": role_title,
                "application_number": app.application_number,
                "raw_token": raw_token,
            },
        )

        logger.info(
            "Successfully provisioned operational account '%s' (role: %s) for application '%s'.",
            user.username,
            user.role_id,
            app.application_number,
        )

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id,
            "hospital_id": user.hospital_id,
            "is_already_provisioned": False,
            "raw_activation_token": raw_token,
            "outbox_id": outbox_record.outbox_id,
            "applicant_email": app.applicant_email,
            "applicant_name": app.applicant_name,
        }

    def _build_existing_provisioning_result(
        self,
        app: RegistrationApplication,
        existing_user: User,
        base_activation_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct return dictionary for already provisioned user, generating token & outbox event if needed."""
        logger.info("Application '%s' already has provisioned user '%s'. Returning existing record.", app.application_number, existing_user.user_id)
        existing_token = (
            self.session.query(AccountActivationToken)
            .filter_by(user_id=existing_user.user_id, is_consumed=False)
            .order_by(AccountActivationToken.id.desc())
            .first()
        )
        raw_token = None
        now = datetime.now(timezone.utc)
        tok_exp = (
            existing_token.expires_at
            if (existing_token and existing_token.expires_at.tzinfo)
            else (existing_token.expires_at.replace(tzinfo=timezone.utc) if existing_token else None)
        )
        outbox_id = None
        if not existing_token or (tok_exp and tok_exp < now):
            raw_token = secrets.token_urlsafe(32)
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            act_token = AccountActivationToken(
                activation_token_id=f"ACT_{secrets.token_hex(16)}",
                application_id=app.application_id,
                user_id=existing_user.user_id,
                token_hash=token_hash,
                is_consumed=False,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS),
            )
            self.session.add(act_token)
            self.session.flush()

            role_titles = {
                "STATE_ADMIN": "State Health Administrator",
                "DISTRICT_ADMIN": "District Health Administrator",
                "HOSPITAL": "Hospital Operational Administrator",
            }
            role_title = role_titles.get(existing_user.role_id, "Operational Administrator")
            outbox_svc = EmailOutboxService(self.session, self.email_provider)
            base_act = self._get_base_activation_url(base_activation_url)
            outbox_rec = outbox_svc.enqueue_email(
                event_type="ACCOUNT_ACTIVATION",
                recipient_email=app.applicant_email,
                recipient_name=app.applicant_name,
                subject=f"Official Portal Account Activation: {role_title} ({app.application_number})",
                payload={
                    "activation_link": f"{base_act}?token={raw_token}",
                    "role_title": role_title,
                    "application_number": app.application_number,
                    "raw_token": raw_token,
                },
            )
            outbox_id = outbox_rec.outbox_id

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "user_id": existing_user.user_id,
            "username": existing_user.username,
            "role_id": existing_user.role_id,
            "hospital_id": existing_user.hospital_id,
            "is_already_provisioned": True,
            "raw_activation_token": raw_token,
            "outbox_id": outbox_id,
            "applicant_email": app.applicant_email,
            "applicant_name": app.applicant_name,
        }

    def _generate_unique_username(self, base_slug: str) -> str:
        """Ensure username uniqueness by appending incrementing suffix if collision exists."""
        slug = re.sub(r"[^a-z0-9_]", "", base_slug.lower().replace(" ", "_"))[:40]
        candidate = slug
        idx = 1
        while self.session.query(User).filter_by(username=candidate).first() is not None:
            candidate = f"{slug}_{idx}"
            idx += 1
        return candidate

    def _provision_state_admin(self, app: RegistrationApplication) -> Dict[str, Any]:
        """Provision State administrative account."""
        state_slug = re.sub(r"[^a-z0-9_]", "", app.state.lower().replace(" ", "_"))
        username = self._generate_unique_username(f"state_{state_slug}")
        user_id = f"U_ST_{secrets.token_hex(4).upper()}"

        user = User(
            user_id=user_id,
            username=username,
            name=f"{app.applicant_name} Admin",
            password_hash="PENDING_ACTIVATION",
            role_id="STATE_ADMIN",
            state=app.state,
            district=None,
            hospital_id=None,
            email=app.applicant_email,
            phone_number=app.applicant_phone,
            is_active=False,  # Inactive until token activation
            application_id=app.application_id,
        )
        self.session.add(user)
        self.session.flush()
        return {"user": user}

    def _provision_district_admin(self, app: RegistrationApplication) -> Dict[str, Any]:
        """Provision District administrative account."""
        dist_slug = re.sub(r"[^a-z0-9_]", "", app.district.lower().replace(" ", "_"))
        username = self._generate_unique_username(f"dist_{dist_slug}")
        user_id = f"U_DIST_{secrets.token_hex(4).upper()}"

        user = User(
            user_id=user_id,
            username=username,
            name=f"{app.applicant_name} Admin",
            password_hash="PENDING_ACTIVATION",
            role_id="DISTRICT_ADMIN",
            state=app.state,
            district=app.district,
            hospital_id=None,
            email=app.applicant_email,
            phone_number=app.applicant_phone,
            is_active=False,  # Inactive until token activation
            application_id=app.application_id,
        )
        self.session.add(user)
        self.session.flush()
        return {"user": user}

    def _provision_hospital_admin(self, app: RegistrationApplication) -> Dict[str, Any]:
        """Provision Hospital operational entity and Hospital Admin account."""
        profile = app.profile_data or {}

        # 1. Generate unique hospital_id (e.g., sequential GH00501+ or random fallback)
        hospital_id = None
        # Check current max hospital sequence in database
        max_gh = (
            self.session.query(func.max(Hospital.hospital_id))
            .filter(Hospital.hospital_id.like("GH%"))
            .scalar()
        )
        if max_gh and max_gh.startswith("GH") and max_gh[2:].isdigit():
            next_num = int(max_gh[2:]) + 1
            hospital_id = f"GH{next_num:05d}"
        else:
            hospital_id = f"GH{secrets.randbelow(90000) + 10000}"

        # Ensure absolute uniqueness
        while self.session.query(Hospital).filter_by(hospital_id=hospital_id).first() is not None:
            num = int(hospital_id[2:]) + 1
            hospital_id = f"GH{num:05d}"

        def _to_yes_no(val, default="Yes"):
            if val is None:
                return default
            if isinstance(val, bool):
                return "Yes" if val else "No"
            s = str(val).strip().lower()
            if s in ("yes", "true", "1", "y"):
                return "Yes"
            if s in ("no", "false", "0", "n"):
                return "No"
            return default

        # 2. Create Hospital record
        hospital = Hospital(
            hospital_id=hospital_id,
            name=app.applicant_name,
            state=app.state,
            district=app.district,
            city=profile.get("city") or app.district,
            latitude=float(profile.get("latitude", 30.7046)),
            longitude=float(profile.get("longitude", 76.7179)),
            total_beds=int(profile.get("total_beds", 50)),
            available_beds=int(profile.get("available_beds", 20)),
            icu_beds=int(profile.get("icu_beds", 5)),
            available_icu_beds=int(profile.get("available_icu_beds", 2)),
            emergency_beds=int(profile.get("emergency_beds", 5)),
            available_emergency_beds=int(profile.get("available_emergency_beds", 2)),
            emergency_24x7=_to_yes_no(profile.get("emergency_24x7"), "Yes"),
            accepts_referral=_to_yes_no(profile.get("accepts_referral"), "Yes"),
            approval_status="APPROVED",
            is_grandfathered=False,
            approved_at=datetime.now(timezone.utc),
            application_id=app.application_id,
        )
        self.session.add(hospital)
        self.session.flush()

        # 3. Create User record bound to Hospital
        username = self._generate_unique_username(hospital_id.lower())
        user_id = f"U_HOSP_{hospital_id.lower()}"

        user = User(
            user_id=user_id,
            username=username,
            name=f"{app.applicant_name} Admin",
            password_hash="PENDING_ACTIVATION",
            role_id="HOSPITAL",
            state=app.state,
            district=app.district,
            hospital_id=hospital_id,
            email=app.applicant_email,
            phone_number=app.applicant_phone,
            is_active=False,
            application_id=app.application_id,
        )
        self.session.add(user)
        self.session.flush()

        # 4. Initialize operational PostgreSQL inventory records
        from src.database.pg_repository import PgReferralRepository
        repo = PgReferralRepository(self.session)

        raw_total = profile.get("total_beds")
        raw_icu = profile.get("icu_beds")
        raw_emergency = profile.get("emergency_beds")

        default_total = int(raw_total) if raw_total is not None else int(os.getenv("DEFAULT_PROVISIONED_TOTAL_BEDS", "20"))
        default_icu = int(raw_icu) if raw_icu is not None else int(os.getenv("DEFAULT_PROVISIONED_ICU_BEDS", "2"))
        default_emergency = int(raw_emergency) if raw_emergency is not None else int(os.getenv("DEFAULT_PROVISIONED_EMERGENCY_BEDS", "2"))

        # General beds = total - icu - emergency (if total is aggregate capacity), or total itself
        if default_total > (default_icu + default_emergency):
            general_capacity = default_total - default_icu - default_emergency
        else:
            general_capacity = default_total

        repo.initialize_default_inventory(
            hospital_id=hospital_id,
            capacities={
                "GENERAL": max(1, general_capacity),
                "ICU": max(0, default_icu),
                "EMERGENCY": max(0, default_emergency),
            },
            resources={
                "oxygen_support": hospital.oxygen_support,
                "ventilator": hospital.ventilator,
                "ambulance": hospital.ambulance,
                "blood_bank": hospital.blood_bank,
                "emergency_24x7": hospital.emergency_24x7,
            },
            user_id="SYSTEM_PROVISIONER",
        )

        return {"user": user, "hospital": hospital}

    # ============================================================
    # 2. POST-COMMIT EMAIL DISPATCH
    # ============================================================

    def dispatch_activation_email(
        self,
        provisioning_result: Dict[str, Any],
        base_activation_url: Optional[str] = None,
    ) -> bool:
        """
        Dispatches activation email AFTER the database transaction has committed,
        using the transactional outbox as the single source of truth.
        Atomically transitions the outbox event to SENT (or FAILED with exponential backoff)
        so that background workers never duplicate delivery.
        """
        outbox_id = provisioning_result.get("outbox_id")
        outbox_svc = EmailOutboxService(self.session, self.email_provider)

        if outbox_id:
            res = outbox_svc.process_event(outbox_id)
            self.session.commit()
            return res.get("succeeded", False)

        # Fallback for callers that did not capture outbox_id:
        email = provisioning_result.get("applicant_email")
        if email:
            pending_event = (
                self.session.query(RegistrationEmailOutbox)
                .filter(
                    RegistrationEmailOutbox.recipient_email == email.strip().lower(),
                    RegistrationEmailOutbox.event_type == "ACCOUNT_ACTIVATION",
                    RegistrationEmailOutbox.status == "PENDING",
                )
                .order_by(RegistrationEmailOutbox.id.desc())
                .first()
            )
            if pending_event:
                res = outbox_svc.process_event(pending_event.outbox_id)
                self.session.commit()
                return res.get("succeeded", False)

        return False

    # ============================================================
    # 3. ACCOUNT ACTIVATION & PASSWORD CREATION
    # ============================================================

    def activate_account(
        self,
        raw_activation_token: str,
        password: str,
        confirm_password: str,
    ) -> Dict[str, Any]:
        """
        Activate account using one-time token:
        1. Validates password complexity.
        2. Validates password matching.
        3. Looks up token by SHA-256 hash.
        4. Verifies token is not expired and not previously consumed.
        5. Atomically consumes token, hashes password (PBKDF2-SHA256), and sets is_active=True.
        """
        if not raw_activation_token or not raw_activation_token.strip():
            raise ActivationTokenError("Activation token is required.")

        if password != confirm_password:
            raise ValidationError("Password and password confirmation do not match.")

        validate_password_complexity(password)

        token_hash = hashlib.sha256(raw_activation_token.strip().encode("utf-8")).hexdigest()
        query = self.session.query(AccountActivationToken).filter_by(token_hash=token_hash)
        try:
            tok = query.with_for_update().first()
        except Exception:
            tok = query.first()
        if not tok:
            raise ActivationTokenError("Invalid or non-existent activation token.")

        if tok.is_consumed:
            raise ActivationTokenError("Activation token has already been consumed. Please log in or request a new link.")

        now = datetime.now(timezone.utc)
        exp = tok.expires_at if tok.expires_at.tzinfo else tok.expires_at.replace(tzinfo=timezone.utc)
        if exp < now:
            raise ActivationTokenError("Activation token has expired. Please request a new activation link.")

        user = tok.user
        if not user:
            raise ProvisioningError("Orphan activation token: associated user account not found.")

        # Atomic activation
        tok.is_consumed = True
        tok.consumed_at = now
        user.password_hash = hash_password(password)
        user.is_active = True
        self.session.flush()

        logger.info("Operational account '%s' (user_id: %s) successfully activated.", user.username, user.user_id)

        return {
            "user_id": user.user_id,
            "username": user.username,
            "name": user.name,
            "role_id": user.role_id,
            "hospital_id": user.hospital_id,
            "state": user.state,
            "district": user.district,
            "activated_at": now.isoformat(),
            "message": "Account successfully activated. You may now log in to the portal.",
        }

    # ============================================================
    # 4. RESEND ACTIVATION LINK
    # ============================================================

    def resend_activation_token(
        self,
        applicant_email: str,
        application_number: str,
        base_activation_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate and return a replacement activation token for an approved unactivated application:
        - Invalidates any prior active unconsumed activation tokens.
        - Issues a fresh token valid for 72 hours.
        """
        app = (
            self.session.query(RegistrationApplication)
            .filter(
                RegistrationApplication.application_number == application_number.strip(),
                func.lower(RegistrationApplication.applicant_email) == applicant_email.strip().lower(),
            )
            .first()
        )
        if not app:
            raise ApplicationNotFoundError("Invalid application number or applicant email.")

        if app.status != "APPROVED":
            raise IneligibleForApprovalError("Cannot issue activation token for an application that has not received final approval.")

        user = (
            self.session.query(User)
            .filter_by(application_id=app.application_id)
            .first()
        )
        if not user:
            raise ProvisioningError("Operational account has not yet been provisioned for this application.")

        if user.is_active:
            raise ValidationError("This account has already been activated. Please proceed to the login page.")

        # Invalidate old tokens
        old_tokens = (
            self.session.query(AccountActivationToken)
            .filter_by(user_id=user.user_id, is_consumed=False)
            .all()
        )
        for ot in old_tokens:
            ot.is_consumed = True
            ot.consumed_at = datetime.now(timezone.utc)

        # Issue fresh token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        new_token = AccountActivationToken(
            activation_token_id=f"ACT_{secrets.token_hex(16)}",
            application_id=app.application_id,
            user_id=user.user_id,
            token_hash=token_hash,
            is_consumed=False,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_TOKEN_EXPIRY_HOURS),
        )
        self.session.add(new_token)
        self.session.flush()

        # Enqueue replacement activation email in outbox inside same transaction
        role_titles = {
            "STATE_ADMIN": "State Health Administrator",
            "DISTRICT_ADMIN": "District Health Administrator",
            "HOSPITAL": "Hospital Operational Administrator",
        }
        role_title = role_titles.get(user.role_id, "Operational Administrator")
        outbox_svc = EmailOutboxService(self.session, self.email_provider)
        base_act = self._get_base_activation_url(base_activation_url)
        outbox_rec = outbox_svc.enqueue_email(
            event_type="ACCOUNT_ACTIVATION",
            recipient_email=app.applicant_email,
            recipient_name=app.applicant_name,
            subject=f"Replacement Activation Link: {role_title} ({app.application_number})",
            payload={
                "activation_link": f"{base_act}?token={raw_token}",
                "role_title": role_title,
                "application_number": app.application_number,
                "raw_token": raw_token,
            },
        )

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "user_id": user.user_id,
            "username": user.username,
            "role_id": user.role_id,
            "raw_activation_token": raw_token,
            "outbox_id": outbox_rec.outbox_id,
            "applicant_email": app.applicant_email,
            "applicant_name": app.applicant_name,
        }

    # ============================================================
    # 5. PASSWORD RECOVERY (FORGOT / RESET PASSWORD)
    # ============================================================

    def request_password_reset(
        self,
        email: str,
        base_reset_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request password reset link:
        - Avoids user enumeration: always returns identical generic response.
        - Generates 1-hour single-use cryptographic reset token for active operational users.
        - Stores only SHA-256 token hash in password_reset_tokens.
        - Enqueues reset notification in transactional outbox.
        - Timing attack defense for non-existent users.
        """
        normalized_email = (email or "").strip().lower()
        if not normalized_email or "@" not in normalized_email:
            raise ValidationError("Valid email address is required.")

        user = (
            self.session.query(User)
            .filter(func.lower(User.email) == normalized_email, User.is_active == True)
            .first()
        )

        generic_response = {
            "message": "If an active account exists for this email address, a password reset link has been dispatched.",
            "email_masked": self._mask_email(normalized_email),
        }

        if not user:
            # Timing attack mitigation: simulate hash verification time
            from src.auth.auth_store import verify_password, DUMMY_PBKDF2_HASH
            verify_password("dummy_pwd", DUMMY_PBKDF2_HASH)
            return generic_response

        now = datetime.now(timezone.utc)

        # Invalidate any active unconsumed reset tokens for this user
        existing_tokens = (
            self.session.query(PasswordResetToken)
            .filter_by(user_id=user.user_id, is_consumed=False)
            .all()
        )
        for tok in existing_tokens:
            tok.is_consumed = True
            tok.consumed_at = now

        # Generate fresh secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        reset_id = f"RST_{secrets.token_hex(16)}"

        reset_token_record = PasswordResetToken(
            reset_token_id=reset_id,
            user_id=user.user_id,
            token_hash=token_hash,
            is_consumed=False,
            expires_at=now + timedelta(hours=1),
            created_at=now,
        )
        self.session.add(reset_token_record)
        self.session.flush()

        # Enqueue in transactional email outbox
        outbox_svc = EmailOutboxService(self.session, self.email_provider)
        reset_base = self._get_base_reset_url(base_reset_url)
        reset_link = f"{reset_base}?token={raw_token}"
        outbox_svc.enqueue_email(
            event_type="PASSWORD_RESET",
            recipient_email=user.email,
            recipient_name=user.name,
            subject="Security Notification: Reset Your Portal Password",
            payload={
                "reset_link": reset_link,
                "user_id": user.user_id,
                "raw_token": raw_token,
            },
        )

        return generic_response

    def confirm_password_reset(
        self,
        raw_reset_token: str,
        password: str,
        confirm_password: str,
    ) -> Dict[str, Any]:
        """
        Confirm password reset using one-time token:
        - Validates passwords match.
        - Validates password complexity.
        - Constant-time verification of token hash.
        - Validates token is not expired and not consumed.
        - Consumes token (single-use).
        - Hashes password using PBKDF2-HMAC-SHA256 (100k iterations).
        - Prevents token replay.
        """
        if not raw_reset_token or not raw_reset_token.strip():
            raise ActivationTokenError("Password reset token is required.")

        if password != confirm_password:
            raise ValidationError("New password and confirm password do not match.")

        validate_password_complexity(password)

        input_hash = hashlib.sha256(raw_reset_token.strip().encode("utf-8")).hexdigest()
        query = self.session.query(PasswordResetToken).filter_by(token_hash=input_hash)
        try:
            token_record = query.with_for_update().first()
        except Exception:
            token_record = query.first()
        if not token_record:
            raise ActivationTokenError("Invalid or non-existent password reset token.")

        # Constant-time comparison
        if not hmac.compare_digest(token_record.token_hash, input_hash):
            raise ActivationTokenError("Invalid password reset token.")

        if token_record.is_consumed:
            raise ActivationTokenError("Password reset token has already been consumed. Please request a new link.")

        now = datetime.now(timezone.utc)
        exp = (
            token_record.expires_at
            if token_record.expires_at.tzinfo
            else token_record.expires_at.replace(tzinfo=timezone.utc)
        )
        if exp < now:
            raise ActivationTokenError("Password reset token has expired. Please request a new link.")

        user = token_record.user
        if not user:
            raise ProvisioningError("Orphan reset token: associated user account not found.")

        # Atomic password reset
        token_record.is_consumed = True
        token_record.consumed_at = now
        user.password_hash = hash_password(password)
        user.is_active = True
        user.updated_at = now
        self.session.flush()

        # Invalidate all prior active sessions/JWTs for this user
        revoke_user_sessions(user.user_id)
        if user.username:
            revoke_user_sessions(user.username)

        logger.info("Operational user '%s' (%s) password successfully reset. Prior sessions invalidated.", user.username, user.user_id)

        return {
            "message": "Password has been successfully reset. You may now log in with your new password.",
            "username": user.username,
            "user_id": user.user_id,
        }

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email address for secure responses/logging."""
        if not email or "@" not in email:
            return "***"
        parts = email.split("@", 1)
        name = parts[0]
        domain = parts[1]
        masked_name = name[0] + "***" if len(name) > 1 else "*"
        return f"{masked_name}@{domain}"
