import os
import pytest

@pytest.fixture(autouse=True)
def default_test_env(monkeypatch):
    """Ensure automated tests run in safe SIMULATED mode by default."""
    monkeypatch.setenv("SIH_OTP_PROVIDER", "SIMULATED")
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "simulated")
    monkeypatch.setenv("ENVIRONMENT", "development")
    from src.services.otp_service import set_otp_provider
    set_otp_provider(None)
    from src.services.email_service import set_email_provider
    set_email_provider(None)
