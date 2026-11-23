"""
Unit and Integration Tests for Mailjet HTTPS Send API v3.1 Email Backend
AI-Powered Smart Hospital Referral System — SWASTHYA SAMANVAY
"""

import os
import json
import base64
import urllib.request
import urllib.error
from unittest.mock import MagicMock, patch
import pytest

from src.services.email_service import (
    BaseEmailProvider,
    MailjetEmailProvider,
    SMTPEmailProvider,
    SimulatedEmailProvider,
    MockEmailProvider,
    EmailDeliveryError,
    get_email_provider,
    set_email_provider,
)
from src.services.otp_service import OTPService, ConfigurableOTPProvider


@pytest.fixture(autouse=True)
def reset_provider():
    """Reset active email provider before and after each test."""
    set_email_provider(None)
    yield
    set_email_provider(None)


def test_mailjet_provider_initialization_defaults():
    """Verify MailjetEmailProvider reads environment variables and defaults."""
    provider = MailjetEmailProvider(
        api_key="test_api_key",
        secret_key="test_secret_key",
        sender_email="sender@example.com",
        sender_name="SWASTHYA SAMANVAY",
    )
    assert provider.api_key == "test_api_key"
    assert provider.secret_key == "test_secret_key"
    assert provider.sender == "sender@example.com"
    assert provider.sender_name == "SWASTHYA SAMANVAY"
    assert provider.api_url == "https://api.mailjet.com/v3.1/send"
    assert provider.timeout == 10


def test_mailjet_missing_credentials_raises_error():
    """Verify that send_email fails fast if credentials are not configured."""
    provider = MailjetEmailProvider(api_key="", secret_key="")
    with pytest.raises(EmailDeliveryError) as exc_info:
        provider.send_email(
            to_email="patient@example.com",
            subject="Test",
            body_text="Hello",
        )
    assert "Mailjet API key or Secret key is not configured" in str(exc_info.value)


def test_mailjet_successful_send_email():
    """Verify that send_email constructs the exact Mailjet v3.1 payload and basic auth header."""
    provider = MailjetEmailProvider(
        api_key="mj_pub_12345",
        secret_key="mj_sec_67890",
        sender_email="support@swasthya.gov.in",
        sender_name="SWASTHYA SAMANVAY",
    )

    fake_response = MagicMock()
    fake_response.getcode.return_value = 200
    fake_response.read.return_value = json.dumps({
        "Messages": [
            {
                "Status": "success",
                "CustomID": "",
                "To": [{"Email": "recipient@hospital.org", "MessageUUID": "uuid-123", "MessageID": 12345}],
                "Cc": [],
                "Bcc": [],
            }
        ]
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    captured_request = []

    def mock_urlopen(req, timeout=None):
        captured_request.append((req, timeout))
        return fake_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        success = provider.send_email(
            to_email="recipient@hospital.org",
            subject="Bed Allocation Confirmation",
            body_text="Your ICU bed is confirmed.",
            body_html="<p>Your ICU bed is confirmed.</p>",
        )

    assert success is True
    assert len(captured_request) == 1
    req, timeout = captured_request[0]

    # Verify endpoint
    assert req.full_url == "https://api.mailjet.com/v3.1/send"
    assert req.method == "POST"

    # Verify Basic Auth Header
    auth_header = req.headers.get("Authorization")
    expected_b64 = base64.b64encode(b"mj_pub_12345:mj_sec_67890").decode("ascii")
    assert auth_header == f"Basic {expected_b64}"

    # Verify Content-Type
    assert req.headers.get("Content-type") == "application/json"

    # Verify JSON Payload structure matches Mailjet Send API v3.1 spec
    payload = json.loads(req.data.decode("utf-8"))
    assert "Messages" in payload
    assert len(payload["Messages"]) == 1
    msg = payload["Messages"][0]
    assert msg["From"]["Email"] == "support@swasthya.gov.in"
    assert msg["From"]["Name"] == "SWASTHYA SAMANVAY"
    assert msg["To"] == [{"Email": "recipient@hospital.org"}]
    assert msg["Subject"] == "Bed Allocation Confirmation"
    assert msg["TextPart"] == "Your ICU bed is confirmed."
    assert msg["HTMLPart"] == "<p>Your ICU bed is confirmed.</p>"


def test_mailjet_send_activation_email():
    """Verify that send_activation_email formats the activation link and headers correctly."""
    provider = MailjetEmailProvider(
        api_key="mj_pub_key",
        secret_key="mj_sec_key",
        sender_email="support@swasthya.gov.in",
    )

    fake_response = MagicMock()
    fake_response.getcode.return_value = 200
    fake_response.read.return_value = json.dumps({"Messages": [{"Status": "success"}]}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    captured_payload = []

    def mock_urlopen(req, timeout=None):
        captured_payload.append(json.loads(req.data.decode("utf-8")))
        return fake_response

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        success = provider.send_activation_email(
            to_email="cmo@patnahospital.org",
            recipient_name="Dr. R. K. Singh",
            activation_link="https://swasthya-samanvay.vercel.app/activate?token=act_9999",
            role_title="Hospital Administrator",
            application_number="APP-2026-BIH-001",
        )

    assert success is True
    assert len(captured_payload) == 1
    msg = captured_payload[0]["Messages"][0]
    assert "Dr. R. K. Singh" in msg["TextPart"]
    assert "https://swasthya-samanvay.vercel.app/activate?token=act_9999" in msg["TextPart"]
    assert "https://swasthya-samanvay.vercel.app/activate?token=act_9999" in msg["HTMLPart"]
    assert "APP-2026-BIH-001" in msg["Subject"]


def test_mailjet_http_error_handling():
    """Verify that HTTP errors (e.g. 401 Unauthorized) raise EmailDeliveryError."""
    provider = MailjetEmailProvider(api_key="bad_key", secret_key="bad_secret")

    http_error = urllib.error.HTTPError(
        url="https://api.mailjet.com/v3.1/send",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=MagicMock(read=lambda: b'{"ErrorMessage": "Unauthorized", "StatusCode": 401}'),
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        with pytest.raises(EmailDeliveryError) as exc_info:
            provider.send_email(
                to_email="test@hospital.org",
                subject="Test",
                body_text="Test message",
            )
    assert "Mailjet HTTP 401 error" in str(exc_info.value)


def test_mailjet_network_url_error_handling():
    """Verify that network failures raise EmailDeliveryError."""
    provider = MailjetEmailProvider(api_key="key", secret_key="secret")

    url_error = urllib.error.URLError("Connection refused")

    with patch("urllib.request.urlopen", side_effect=url_error):
        with pytest.raises(EmailDeliveryError) as exc_info:
            provider.send_email(
                to_email="test@hospital.org",
                subject="Test",
                body_text="Test message",
            )
    assert "Mailjet network failure" in str(exc_info.value)


def test_mailjet_message_level_error_handling():
    """Verify that Mailjet 200 OK responses with Status='error' raise EmailDeliveryError."""
    provider = MailjetEmailProvider(api_key="key", secret_key="secret")

    fake_response = MagicMock()
    fake_response.getcode.return_value = 200
    fake_response.read.return_value = json.dumps({
        "Messages": [
            {
                "Status": "error",
                "Errors": [{"ErrorIdentifier": "err-1", "ErrorMessage": "Invalid email address"}],
            }
        ]
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=fake_response):
        with pytest.raises(EmailDeliveryError) as exc_info:
            provider.send_email(
                to_email="invalid-email",
                subject="Test",
                body_text="Test",
            )
    assert "Mailjet message dispatch error" in str(exc_info.value)
    assert "Invalid email address" in str(exc_info.value)


def test_get_email_provider_mailjet_selection(monkeypatch):
    """Verify that get_email_provider selects MailjetEmailProvider when SIH_EMAIL_BACKEND=mailjet."""
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "mailjet")
    monkeypatch.setenv("MAILJET_API_KEY", "mj_key")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "mj_secret")

    provider = get_email_provider()
    assert isinstance(provider, MailjetEmailProvider)
    assert provider.api_key == "mj_key"
    assert provider.secret_key == "mj_secret"


def test_mock_email_provider_backward_compatibility():
    """Verify MockEmailProvider alias points to SimulatedEmailProvider."""
    assert MockEmailProvider is SimulatedEmailProvider
    mock_instance = MockEmailProvider()
    assert isinstance(mock_instance, BaseEmailProvider)
    assert hasattr(mock_instance, "sent_emails")


def test_otp_service_with_mailjet_provider(monkeypatch):
    """Verify that OTPService delivers verification code via Mailjet when configured."""
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "mailjet")
    monkeypatch.setenv("MAILJET_API_KEY", "mj_key")
    monkeypatch.setenv("MAILJET_SECRET_KEY", "mj_secret")
    monkeypatch.setenv("SIH_OTP_PROVIDER", "EMAIL")

    mailjet_provider = MailjetEmailProvider(api_key="mj_key", secret_key="mj_secret")
    set_email_provider(mailjet_provider)

    fake_response = MagicMock()
    fake_response.getcode.return_value = 200
    fake_response.read.return_value = json.dumps({"Messages": [{"Status": "success"}]}).encode("utf-8")
    fake_response.__enter__.return_value = fake_response
    fake_response.__exit__.return_value = None

    captured_payloads = []

    def mock_urlopen(req, timeout=None):
        captured_payloads.append(json.loads(req.data.decode("utf-8")))
        return fake_response

    otp_provider = ConfigurableOTPProvider()

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        dispatched = otp_provider.send_otp(
            contact_target="applicant@hospital.org",
            otp="543210",
            purpose="REGISTRATION_OTP",
            channel="EMAIL",
        )

    assert dispatched is True
    assert len(captured_payloads) == 1
    msg = captured_payloads[0]["Messages"][0]
    assert "543210" in msg["TextPart"]
    assert "Portal Registration" in msg["Subject"]
    assert msg["To"] == [{"Email": "applicant@hospital.org"}]
