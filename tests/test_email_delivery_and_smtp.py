"""
Email Delivery, SMTP Integration & Outbox Worker Verification Suite
AI Powered Smart Hospital Referral System - Phase 2 Task 2B
"""

import os
import smtplib
import logging
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy.orm import Session

from src.services.email_service import (
    SMTPEmailProvider,
    SimulatedEmailProvider,
    EmailDeliveryError,
    get_email_provider,
    set_email_provider,
    _mask_email,
)
from src.services.email_outbox_service import EmailOutboxService
from src.services.account_provisioning_service import AccountProvisioningService
from src.services.otp_service import OTPService, ConfigurableOTPProvider, SimulatedOTPProvider
from src.services.registration_service import RegistrationService
from src.database.pg_models import (
    RegistrationApplication,
    AccountActivationToken,
    RegistrationEmailOutbox,
    User,
    Hospital,
    VerificationToken,
)
from src.workers.outbox_worker import OutboxWorker


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.pg_models import PgBase, Role

# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def test_db_session():
    """Create in-memory SQLite session with StaticPool for thread safety."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    PgBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    roles = [
        Role(id="HOSPITAL", description="Hospital Staff"),
        Role(id="DISTRICT_ADMIN", description="District Admin"),
        Role(id="STATE_ADMIN", description="State Admin"),
        Role(id="CENTRAL_ADMIN", description="Central Admin"),
    ]
    for r in roles:
        session.merge(r)

    users = [
        User(user_id="U_DIST_MOH", username="dist_moh", name="Mohali CMO", role_id="DISTRICT_ADMIN", state="Punjab", district="Mohali", password_hash="hash"),
        User(user_id="U_STATE_PB", username="state_pb", name="Punjab Director", role_id="STATE_ADMIN", state="Punjab", password_hash="hash"),
        User(user_id="U_CENTRAL", username="central_admin", name="National Registrar", role_id="CENTRAL_ADMIN", password_hash="hash"),
    ]
    for u in users:
        session.merge(u)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()

@pytest.fixture
def sim_email():
    """Provides a fresh SimulatedEmailProvider."""
    provider = SimulatedEmailProvider()
    set_email_provider(provider)
    yield provider
    provider.clear()
    set_email_provider(None)


@pytest.fixture
def smtp_env(monkeypatch):
    """Sets standard mock SMTP environment variables."""
    monkeypatch.setenv("SMTP_HOST", "smtp.test-server.local")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "test_smtp_user")
    monkeypatch.setenv("SMTP_PASSWORD", "SuperSecretSmtpPass123!")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "no-reply@test.sih.gov.in")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_TIMEOUT", "5")
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "smtp")
    monkeypatch.setenv("ENVIRONMENT", "development")


# ============================================================
# 1. SMTP PROVIDER UNIT TESTS
# ============================================================

def test_smtp_successful_delivery_mock(smtp_env):
    """SMTP provider successfully delivers activation and notification emails via smtplib.SMTP."""
    provider = SMTPEmailProvider()

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server

        # Test activation email
        success = provider.send_activation_email(
            to_email="admin@hospital.punjab.gov.in",
            recipient_name="Dr. Harpreet Singh",
            activation_link="https://hospital.sih.gov.in/activate?token=ABC123SECURETOKEN",
            role_title="Hospital Operational Administrator",
            application_number="APP-HOSP-2026-001",
        )
        assert success is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test_smtp_user", "SuperSecretSmtpPass123!")
        assert mock_server.send_message.call_count == 1

        sent_msg = mock_server.send_message.call_args[0][0]
        assert sent_msg["To"] == "admin@hospital.punjab.gov.in"
        assert sent_msg["From"] == "no-reply@test.sih.gov.in"
        assert "Official Portal Account Activation" in sent_msg["Subject"]
        assert "ABC123SECURETOKEN" in sent_msg.get_payload()[0].get_payload()

        # Test general email
        mock_server.reset_mock()
        success_gen = provider.send_email(
            to_email="officer@mohali.gov.in",
            subject="Test Notification",
            body_text="Hello Officer",
        )
        assert success_gen is True
        assert mock_server.send_message.call_count == 1


def test_smtp_authentication_failure(smtp_env, caplog):
    """SMTP authentication failure raises EmailDeliveryError without leaking SMTP password in error or logs."""
    provider = SMTPEmailProvider()

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication credentials invalid")

        with caplog.at_level(logging.DEBUG):
            with pytest.raises(EmailDeliveryError) as exc_info:
                provider.send_email("recipient@punjab.gov.in", "Subject", "Body text")

        err_msg = str(exc_info.value)
        assert "SMTP authentication failed for user 'test_smtp_user'" in err_msg
        assert "SuperSecretSmtpPass123!" not in err_msg

        # Verify password is not in logs
        for record in caplog.records:
            assert "SuperSecretSmtpPass123!" not in record.message


def test_smtp_timeout_handling(smtp_env):
    """SMTP network timeout raises EmailDeliveryError with clean error message."""
    provider = SMTPEmailProvider()

    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        mock_server.starttls.side_effect = TimeoutError("Network connection timed out after 5s")

        with pytest.raises(EmailDeliveryError) as exc_info:
            provider.send_email("recipient@punjab.gov.in", "Subject", "Body text")

        err_msg = str(exc_info.value)
        assert "SMTP connection to smtp.test-server.local:587 failed" in err_msg
        assert "Network connection timed out" in err_msg


def test_missing_smtp_host_configuration(monkeypatch):
    """If SMTP host is empty, SMTPEmailProvider immediately raises EmailDeliveryError."""
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SIH_SMTP_HOST", raising=False)

    provider = SMTPEmailProvider(smtp_host="")
    with pytest.raises(EmailDeliveryError, match="SMTP host is not configured"):
        provider.send_email("test@example.com", "Test", "Body")


def test_missing_production_smtp_configuration_fails_closed(monkeypatch):
    """In production environment, missing or non-smtp email configuration raises RuntimeError."""
    set_email_provider(None)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SIH_SMTP_HOST", raising=False)
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "simulated")

    with pytest.raises(RuntimeError, match="CRITICAL SECURITY ERROR: Production environment forbids email backend 'simulated'"):
        get_email_provider()

    monkeypatch.setenv("SIH_EMAIL_BACKEND", "smtp")
    with pytest.raises(RuntimeError, match="CRITICAL SECURITY ERROR: Production environment requires a valid SMTP configuration"):
        get_email_provider()


# ============================================================
# 2. OTP EMAIL DELIVERY TESTS
# ============================================================

def test_otp_email_delivery_via_configured_email_provider(test_db_session, monkeypatch, sim_email):
    """OTPService routes email OTPs through the active email provider with formatted purpose and code."""
    monkeypatch.setenv("SIH_OTP_PROVIDER", "EMAIL")

    otp_provider = ConfigurableOTPProvider()
    otp_svc = OTPService(test_db_session, provider=otp_provider)

    target_email = "applicant_otp@punjab.gov.in"
    res = otp_svc.request_otp(
        contact_target=target_email,
        channel="EMAIL",
        purpose="REGISTRATION_OTP",
    )
    assert res["contact_target"] == target_email
    assert res["token_id"].startswith("VTOK_")

    # Verify email was captured by active provider
    last_email = sim_email.get_last_email(target_email)
    assert last_email is not None
    assert "Your Verification Code (Portal Registration)" in last_email["subject"]
    assert "Your single-use 6-digit verification code is:" in last_email["body_text"]

    # Extract 6-digit OTP from body text
    import re
    match = re.search(r"code is:\s*([0-9]{6})", last_email["body_text"])
    assert match is not None
    extracted_otp = match.group(1)

    # Verify OTP against OTPService
    verified_target = otp_svc.verify_otp(
        token_id=res["token_id"],
        otp=extracted_otp,
        purpose="REGISTRATION_OTP",
    )
    assert verified_target == target_email


def test_otp_delivery_failure_fails_closed(test_db_session, monkeypatch, sim_email):
    """If the email provider fails to deliver the OTP, request_otp raises an error and does not orphan active token."""
    monkeypatch.setenv("SIH_OTP_PROVIDER", "EMAIL")
    sim_email.fail_next = True

    otp_provider = ConfigurableOTPProvider()
    otp_svc = OTPService(test_db_session, provider=otp_provider)

    with pytest.raises(Exception, match="Failed to deliver"):
        otp_svc.request_otp(
            contact_target="fail_otp@punjab.gov.in",
            channel="EMAIL",
            purpose="PORTAL_ACCESS_OTP",
        )


# ============================================================
# 3. SINGLE-SOURCE OUTBOX & EXACTLY-ONCE ACTIVATION DISPATCH
# ============================================================

def test_activation_email_single_delivery_and_outbox_state(test_db_session, sim_email):
    """
    Activation email dispatch uses the outbox as single source of truth:
    - Post-commit dispatch delivers email and marks outbox record SENT.
    - Subsequent outbox worker run processes 0 items, preventing duplicate emails.
    """
    reg_svc = RegistrationService(test_db_session)
    app = reg_svc.create_application({
        "applicant_type": "STATE",
        "applicant_name": "Department of Health",
        "applicant_email": "health_head@punjab.gov.in",
        "applicant_phone": "9876543200",
        "state": "Punjab",
    })
    app.status = "APPROVED"
    test_db_session.commit()

    prov_svc = AccountProvisioningService(test_db_session)
    reviewer = {"user_id": "U_CENTRAL", "username": "central_admin", "role": "CENTRAL_ADMIN"}
    prov_result = prov_svc.provision_account(app.application_id, reviewer)
    test_db_session.commit()

    outbox_id = prov_result["outbox_id"]
    assert outbox_id is not None

    # Check outbox record is initially PENDING
    outbox_rec = test_db_session.query(RegistrationEmailOutbox).filter_by(outbox_id=outbox_id).first()
    assert outbox_rec.status == "PENDING"
    assert outbox_rec.retry_count == 0

    # 1. Post-commit immediate dispatch
    dispatched = prov_svc.dispatch_activation_email(prov_result)
    assert dispatched is True

    # Outbox status must be updated to SENT in the database
    test_db_session.refresh(outbox_rec)
    assert outbox_rec.status == "SENT"
    assert outbox_rec.sent_at is not None

    # Exactly 1 email delivered
    assert len(sim_email.sent_emails) == 1
    assert sim_email.sent_emails[0]["to_email"] == "health_head@punjab.gov.in"

    # 2. Subsequent outbox worker run must NOT send duplicate email
    outbox_svc = EmailOutboxService(test_db_session, sim_email)
    worker_res = outbox_svc.process_outbox(batch_size=10, worker_id="worker_test")
    assert worker_res["processed"] == 0
    assert len(sim_email.sent_emails) == 1  # Still exactly 1 email


def test_activation_dispatch_failure_retained_in_outbox_for_retry(test_db_session, sim_email):
    """If immediate dispatch fails, outbox record transitions to FAILED with backoff, retryable by worker."""
    reg_svc = RegistrationService(test_db_session)
    app = reg_svc.create_application({
        "applicant_type": "STATE",
        "applicant_name": "Health Office",
        "applicant_email": "retry_test@punjab.gov.in",
        "applicant_phone": "9876543201",
        "state": "Punjab",
    })
    app.status = "APPROVED"
    test_db_session.commit()

    prov_svc = AccountProvisioningService(test_db_session)
    prov_result = prov_svc.provision_account(app.application_id, {"user_id": "U_CENTRAL", "role": "CENTRAL_ADMIN"})
    test_db_session.commit()

    # Simulate network failure during immediate dispatch
    sim_email.fail_next = True
    dispatched = prov_svc.dispatch_activation_email(prov_result)
    assert dispatched is False

    outbox_rec = test_db_session.query(RegistrationEmailOutbox).filter_by(outbox_id=prov_result["outbox_id"]).first()
    assert outbox_rec.status == "FAILED"
    assert outbox_rec.retry_count == 1
    assert "Simulated email delivery network failure" in outbox_rec.last_error

    # Fast-forward retry timestamp to simulate retry window elapsed
    outbox_rec.next_retry_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    test_db_session.commit()

    # Background worker successfully delivers on retry without generating new tokens
    outbox_svc = EmailOutboxService(test_db_session, sim_email)
    worker_res = outbox_svc.process_outbox(batch_size=10, worker_id="worker_bg")
    assert worker_res["succeeded"] == 1

    test_db_session.refresh(outbox_rec)
    assert outbox_rec.status == "SENT"
    assert len(sim_email.sent_emails) == 1

    # Verify only 1 activation token was generated for this user
    user = test_db_session.query(User).filter_by(application_id=app.application_id).first()
    tokens = test_db_session.query(AccountActivationToken).filter_by(user_id=user.user_id).all()
    assert len(tokens) == 1


# ============================================================
# 4. PRIVACY & SENSITIVE TOKEN LOGGING AUDIT
# ============================================================

def test_no_sensitive_tokens_or_passwords_in_logs(test_db_session, caplog, sim_email):
    """Verifies that raw OTPs, activation tokens, and passwords never appear in log records."""
    caplog.set_level(logging.DEBUG)

    raw_token_secret = "SECRET_ACTIVATION_TOKEN_999888777"
    raw_otp_code = "849201"

    outbox_svc = EmailOutboxService(test_db_session, sim_email)
    outbox_rec = outbox_svc.enqueue_email(
        event_type="ACCOUNT_ACTIVATION",
        recipient_email="privacy_check@punjab.gov.in",
        recipient_name="Privacy Officer",
        subject="Activation Link",
        payload={
            "activation_link": f"https://hospital.sih.gov.in/activate?token={raw_token_secret}",
            "role_title": "State Administrator",
            "application_number": "APP-PRIV-001",
        },
    )
    test_db_session.commit()

    outbox_svc.process_event(outbox_rec.outbox_id)

    # Inspect all captured logs
    for record in caplog.records:
        msg = record.message
        assert raw_token_secret not in msg, f"Leak detected: raw token found in log: {msg}"
        assert raw_otp_code not in msg, f"Leak detected: raw OTP found in log: {msg}"
        # Recipient email should be masked e.g. p***@punjab.gov.in
        if "privacy_check@punjab.gov.in" in msg:
            pytest.fail(f"Full unmasked email leaked in log message: {msg}")


# ============================================================
# 5. STANDALONE OUTBOX WORKER TESTS
# ============================================================

def test_outbox_worker_run_once(test_db_session, sim_email):
    """OutboxWorker.run_once() processes pending events and returns structured summary."""
    outbox_svc = EmailOutboxService(test_db_session, sim_email)
    outbox_svc.enqueue_email(
        event_type="GENERIC_NOTIFICATION",
        recipient_email="worker_test@punjab.gov.in",
        subject="Welcome",
        payload={"body_text": "Welcome to the portal."},
    )
    test_db_session.commit()

    worker = OutboxWorker(
        session_factory=lambda: test_db_session,
        email_provider=sim_email,
        worker_id="unit_test_worker",
        batch_size=5,
    )

    summary = worker.run_once()
    assert summary["processed"] == 1
    assert summary["succeeded"] == 1
    assert summary["failed"] == 0
    assert summary["worker_id"] == "unit_test_worker"
    assert len(sim_email.sent_emails) == 1


def test_outbox_worker_prevents_duplicate_concurrent_loops(test_db_session, sim_email):
    """OutboxWorker raises RuntimeError if run_forever is called while already running."""
    worker = OutboxWorker(
        session_factory=lambda: test_db_session,
        email_provider=sim_email,
        poll_interval=0.1,
    )
    worker._is_running = True

    with pytest.raises(RuntimeError, match="is already running a loop"):
        worker.run_forever()


# ============================================================
# 6. BREVO SMTP CONFIGURATION & OTP SERVICE INTEGRATION TESTS
# ============================================================

def test_brevo_smtp_configuration_parameters(monkeypatch):
    """Verify SMTPEmailProvider correctly parses standard Brevo SMTP parameters."""
    monkeypatch.setenv("SMTP_HOST", "smtp-relay.brevo.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "7c48b1001@smtp-brevo.com")
    monkeypatch.setenv("SMTP_PASSWORD", "xsmtpsib-secret-key-test")
    monkeypatch.setenv("SMTP_FROM_EMAIL", "verified_sender@hospital.sih.gov.in")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_TIMEOUT", "10")
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "smtp")

    provider = SMTPEmailProvider()
    assert provider.host == "smtp-relay.brevo.com"
    assert provider.port == 587
    assert provider.user == "7c48b1001@smtp-brevo.com"
    assert provider.password == "xsmtpsib-secret-key-test"
    assert provider.sender == "verified_sender@hospital.sih.gov.in"
    assert provider.use_tls is True
    assert provider.timeout == 10


def test_get_otp_provider_dynamic_resolution_and_default_routing(test_db_session, monkeypatch, sim_email):
    """Verify get_otp_provider() resolves ConfigurableOTPProvider when SIH_OTP_PROVIDER=EMAIL."""
    from src.services.otp_service import get_otp_provider, set_otp_provider

    # 1. Default without SIH_OTP_PROVIDER -> SimulatedOTPProvider
    monkeypatch.delenv("SIH_OTP_PROVIDER", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    set_otp_provider(None)
    dev_provider = get_otp_provider()
    assert isinstance(dev_provider, SimulatedOTPProvider)

    # 2. With SIH_OTP_PROVIDER=EMAIL -> ConfigurableOTPProvider
    monkeypatch.setenv("SIH_OTP_PROVIDER", "EMAIL")
    set_otp_provider(None)
    prod_provider = get_otp_provider()
    assert isinstance(prod_provider, ConfigurableOTPProvider)

    # 3. OTPService instantiated without provider argument uses active email provider
    otp_svc = OTPService(test_db_session)  # provider=None defaults to get_otp_provider()
    assert isinstance(otp_svc.provider, ConfigurableOTPProvider)

    target_email = "dynamic_route@punjab.gov.in"
    res = otp_svc.request_otp(
        contact_target=target_email,
        channel="EMAIL",
        purpose="REGISTRATION_OTP",
    )
    assert res["token_id"].startswith("VTOK_")

    # Email provider captured the OTP email
    last_email = sim_email.get_last_email(target_email)
    assert last_email is not None
    assert "Your Verification Code (Portal Registration)" in last_email["subject"]

    # Reset provider
    set_otp_provider(None)


def test_portal_base_url_settings_and_environment_overrides(monkeypatch):
    """Verify portal_base_url is configurable via environment variables and strips trailing slashes."""
    from src.config import load_settings, get_settings, reset_settings, get_sanitized_config

    # 1. Default fallback when no env var set
    monkeypatch.delenv("PORTAL_BASE_URL", raising=False)
    monkeypatch.delenv("SIH_PORTAL_BASE_URL", raising=False)
    reset_settings()
    settings = load_settings()
    assert settings.portal_base_url == "http://localhost:3000"
    sanitized = get_sanitized_config()
    assert sanitized["portal_base_url"] == "http://localhost:3000"

    # 2. Configured via PORTAL_BASE_URL with trailing slash
    monkeypatch.setenv("PORTAL_BASE_URL", "https://hospital.example.org///")
    reset_settings()
    settings = get_settings()
    assert settings.portal_base_url == "https://hospital.example.org"

    # 3. Fallback to SIH_PORTAL_BASE_URL
    monkeypatch.delenv("PORTAL_BASE_URL", raising=False)
    monkeypatch.setenv("SIH_PORTAL_BASE_URL", "https://staging-referral.mohfw.gov.in/")
    reset_settings()
    settings = get_settings()
    assert settings.portal_base_url == "https://staging-referral.mohfw.gov.in"

    # 4. Default SMTP from email fallback
    monkeypatch.delenv("SMTP_FROM_EMAIL", raising=False)
    monkeypatch.delenv("SMTP_FROM", raising=False)
    monkeypatch.delenv("SIH_SMTP_FROM", raising=False)
    reset_settings()
    settings = get_settings()
    assert settings.smtp_from_email == "pawanbussiness108@gmail.com"


def test_portal_base_url_workflow_notification_and_provisioning(monkeypatch, test_db_session):
    """Verify get_portal_base_url and AccountProvisioningService dynamically honor PORTAL_BASE_URL."""
    from src.config import reset_settings
    from src.services.workflow_notification_service import get_portal_base_url, DEFAULT_PORTAL_BASE_URL
    from src.services.account_provisioning_service import AccountProvisioningService

    assert DEFAULT_PORTAL_BASE_URL == "http://localhost:3000"

    # Test default resolution
    monkeypatch.delenv("PORTAL_BASE_URL", raising=False)
    monkeypatch.delenv("SIH_PORTAL_BASE_URL", raising=False)
    reset_settings()
    assert get_portal_base_url() == "http://localhost:3000"

    prov_svc = AccountProvisioningService(test_db_session)
    assert prov_svc._get_base_activation_url() == "http://localhost:3000/activate"
    assert prov_svc._get_base_reset_url() == "http://localhost:3000/reset-password"

    # Explicit override takes precedence
    assert prov_svc._get_base_activation_url("https://custom.portal/activate/") == "https://custom.portal/activate"
    assert prov_svc._get_base_reset_url("https://custom.portal/reset-password/") == "https://custom.portal/reset-password"

    # Custom environment configuration
    monkeypatch.setenv("PORTAL_BASE_URL", "https://prod-referral.mohfw.gov.in")
    reset_settings()
    assert get_portal_base_url() == "https://prod-referral.mohfw.gov.in"
    assert prov_svc._get_base_activation_url() == "https://prod-referral.mohfw.gov.in/activate"
    assert prov_svc._get_base_reset_url() == "https://prod-referral.mohfw.gov.in/reset-password"


