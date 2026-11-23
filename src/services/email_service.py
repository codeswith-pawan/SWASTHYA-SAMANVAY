"""
Email Dispatch & Notification Service for Account Activation
AI Powered Smart Hospital Referral System - Phase 1 Task 1E

Provides:
- Configurable email providers (SimulatedEmailProvider, SMTPEmailProvider)
- Single-use cryptographic activation link delivery
- Strict privacy: NEVER transmits plaintext passwords
- Post-commit outbox / asynchronous delivery support
"""

import os
import ssl
import smtplib
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class EmailDeliveryError(Exception):
    """Raised when email delivery fails."""
    pass


class BaseEmailProvider(ABC):
    """Abstract interface for dispatching system emails."""

    @abstractmethod
    def send_activation_email(
        self,
        to_email: str,
        recipient_name: str,
        activation_link: str,
        role_title: str,
        application_number: str,
    ) -> bool:
        """
        Send an account activation invitation containing a secure one-time activation link.
        Must NOT contain any plaintext passwords.
        """
        pass

    @abstractmethod
    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        """Send a general notification email."""
        pass


class SimulatedEmailProvider(BaseEmailProvider):
    """
    In-memory email provider for testing and development:
    - Stores sent emails for verification
    - Supports forced delivery failure simulation
    """

    def __init__(self):
        self.sent_emails: List[Dict[str, Any]] = []
        self.fail_next: bool = False

    def send_activation_email(
        self,
        to_email: str,
        recipient_name: str,
        activation_link: str,
        role_title: str,
        application_number: str,
    ) -> bool:
        if self.fail_next:
            self.fail_next = False
            logger.warning("SimulatedEmailProvider: Simulating delivery failure to '%s'.", to_email)
            raise EmailDeliveryError(f"Simulated email delivery network failure to {to_email}.")

        record = {
            "to_email": to_email,
            "recipient_name": recipient_name,
            "activation_link": activation_link,
            "role_title": role_title,
            "application_number": application_number,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent_emails.append(record)
        logger.info(
            "SimulatedEmailProvider: Activation email sent to '%s' (%s) for application '%s'.",
            _mask_email(to_email),
            role_title,
            application_number,
        )
        return True

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        if self.fail_next:
            self.fail_next = False
            logger.warning("SimulatedEmailProvider: Simulating delivery failure to '%s'.", _mask_email(to_email))
            raise EmailDeliveryError(f"Simulated email delivery network failure to {_mask_email(to_email)}.")

        record = {
            "to_email": to_email,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        self.sent_emails.append(record)
        logger.info("SimulatedEmailProvider: Email '%s' sent to '%s'.", subject, _mask_email(to_email))
        return True

    def get_last_email(self, to_email: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve most recent sent email, optionally filtered by recipient."""
        if not self.sent_emails:
            return None
        if to_email:
            for em in reversed(self.sent_emails):
                if em["to_email"].lower() == to_email.lower():
                    return em
            return None
        return self.sent_emails[-1]

    def clear(self):
        self.sent_emails.clear()
        self.fail_next = False


def _mask_email(email: str) -> str:
    """Mask email address for secure logging."""
    if not email or "@" not in email:
        return "***"
    parts = email.split("@", 1)
    name = parts[0]
    domain = parts[1]
    masked_name = name[0] + "***" if len(name) > 1 else "*"
    return f"{masked_name}@{domain}"


class SMTPEmailProvider(BaseEmailProvider):
    """
    Production SMTP email provider.
    Configured via environment variables:
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SMTP_FROM_EMAIL, SMTP_USE_TLS, SMTP_TIMEOUT.
    """

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_email: Optional[str] = None,
        use_tls: Optional[bool] = None,
        timeout: Optional[int] = None,
    ):
        self.host = (
            smtp_host
            or os.getenv("SMTP_HOST")
            or os.getenv("SIH_SMTP_HOST")
            or ""
        ).strip()

        port_str = (
            smtp_port
            or os.getenv("SMTP_PORT")
            or os.getenv("SIH_SMTP_PORT")
            or "587"
        )
        self.port = int(port_str)

        self.user = (
            smtp_user
            or os.getenv("SMTP_USERNAME")
            or os.getenv("SMTP_USER")
            or os.getenv("SIH_SMTP_USER")
            or ""
        ).strip()

        self.password = (
            smtp_password
            or os.getenv("SMTP_PASSWORD")
            or os.getenv("SIH_SMTP_PASSWORD")
            or ""
        )

        self.sender = (
            sender_email
            or os.getenv("SMTP_FROM_EMAIL")
            or os.getenv("SMTP_FROM")
            or os.getenv("SIH_SMTP_FROM")
            or "pawanbussiness108@gmail.com"
        ).strip()

        self.sender_name = (
            os.getenv("SMTP_SENDER_NAME")
            or "SWASTHYA SAMANVAY"
        ).strip()

        if use_tls is not None:
            self.use_tls = use_tls
        else:
            tls_env = os.getenv("SMTP_USE_TLS", os.getenv("SIH_SMTP_USE_TLS", "true")).lower().strip()
            self.use_tls = tls_env in ("1", "true", "yes")

        timeout_val = timeout or os.getenv("SMTP_TIMEOUT", os.getenv("SIH_SMTP_TIMEOUT", "10"))
        self.timeout = int(timeout_val)

    def _send_mime(self, to_email: str, msg: MIMEMultipart, log_description: str) -> bool:
        if not self.host:
            raise EmailDeliveryError("SMTP host is not configured.")

        masked_to = _mask_email(to_email)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout) as server:
                if self.use_tls:
                    try:
                        import certifi
                        tls_context = ssl.create_default_context(cafile=certifi.where())
                    except ImportError:
                        tls_context = ssl.create_default_context()
                    server.starttls(context=tls_context)
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
                logger.info("SMTPEmailProvider: Sent %s to %s.", log_description, masked_to)
                return True
        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error("SMTPEmailProvider: Authentication failed for user '%s'.", self.user)
            raise EmailDeliveryError(f"SMTP authentication failed for user '{self.user}'.") from auth_err
        except (smtplib.SMTPConnectError, TimeoutError, smtplib.SMTPServerDisconnected) as conn_err:
            logger.error("SMTPEmailProvider: Connection error contacting %s:%s.", self.host, self.port)
            raise EmailDeliveryError(f"SMTP connection to {self.host}:{self.port} failed: {conn_err}") from conn_err
        except Exception as exc:
            logger.error("SMTPEmailProvider: Failed delivering to %s: %s", masked_to, exc)
            raise EmailDeliveryError(f"SMTP delivery failed: {type(exc).__name__}: {exc}") from exc

    def _format_from(self) -> str:
        if self.sender_name:
            return f"{self.sender_name} <{self.sender}>"
        return self.sender

    def send_activation_email(
        self,
        to_email: str,
        recipient_name: str,
        activation_link: str,
        role_title: str,
        application_number: str,
    ) -> bool:
        subject = f"Official Portal Account Activation: {role_title} ({application_number}) - SWASTHYA SAMANVAY"
        
        body_text = f"""Dear {recipient_name},

Your registration application ({application_number}) has received final administrative approval.

An official operational account ({role_title}) has been provisioned for you.

To activate your account and establish your secure password, please visit the link below:
{activation_link}

This activation link is one-time use and will expire in 72 hours.
For security reasons, do not share this link with anyone.

Regards,
SWASTHYA SAMANVAY - Hospital Coordination & Referral Platform
Support: pawanbussiness108@gmail.com
"""

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._format_from()
        msg["To"] = to_email
        msg.attach(MIMEText(body_text, "plain"))

        return self._send_mime(to_email, msg, f"activation email for application '{application_number}'")

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
    ) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self._format_from()
        msg["To"] = to_email
        msg.attach(MIMEText(body_text, "plain"))
        if body_html:
            msg.attach(MIMEText(body_html, "html"))

        return self._send_mime(to_email, msg, f"email '{subject}'")


_ACTIVE_EMAIL_PROVIDER: Optional[BaseEmailProvider] = None

def get_email_provider() -> BaseEmailProvider:
    """
    Retrieve active email provider singleton.
    In production (SIH_ENV=production or ENVIRONMENT=production), fails closed
    if SMTP is missing or misconfigured.
    """
    global _ACTIVE_EMAIL_PROVIDER
    if _ACTIVE_EMAIL_PROVIDER is not None:
        return _ACTIVE_EMAIL_PROVIDER

    env = os.getenv("ENVIRONMENT", os.getenv("SIH_ENV", "development")).lower().strip()
    is_prod = env in ("production", "prod")

    backend = os.getenv("SIH_EMAIL_BACKEND", os.getenv("EMAIL_BACKEND", "")).strip().lower()

    if is_prod:
        host = os.getenv("SMTP_HOST", os.getenv("SIH_SMTP_HOST", "")).strip()
        if backend and backend != "smtp":
            raise RuntimeError(
                f"CRITICAL SECURITY ERROR: Production environment forbids email backend '{backend}'. "
                f"Only 'smtp' is permitted."
            )
        if not host:
            raise RuntimeError(
                "CRITICAL SECURITY ERROR: Production environment requires a valid SMTP configuration (SMTP_HOST is not set)."
            )
        _ACTIVE_EMAIL_PROVIDER = SMTPEmailProvider()
    else:
        if backend == "smtp":
            _ACTIVE_EMAIL_PROVIDER = SMTPEmailProvider()
        else:
            _ACTIVE_EMAIL_PROVIDER = SimulatedEmailProvider()

    return _ACTIVE_EMAIL_PROVIDER


def set_email_provider(provider: BaseEmailProvider) -> None:
    """Override active email provider (used in tests)."""
    global _ACTIVE_EMAIL_PROVIDER
    _ACTIVE_EMAIL_PROVIDER = provider
