"""
Phase 3 Observability, Security Headers & Startup Invariants Test Suite
AI Powered Smart Hospital Referral System
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.config import (
    load_settings,
    reset_settings,
    validate_production_configuration,
    get_sanitized_config,
    INSECURE_DEV_JWT_SECRET,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_health_endpoints(client):
    # 1. Base health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # 2. Liveness check
    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "UP"

    # 3. Readiness check
    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    data = ready_res.json()
    assert "ready" in data
    assert "database" in data
    assert "redis" in data

    # 4. Metrics check
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    m_data = metrics_res.json()
    assert "server" in m_data
    assert "email_outbox_queue" in m_data
    assert "background_worker" in m_data
    assert m_data["server"]["total_requests"] >= 1


def test_security_headers_and_request_id(client):
    custom_req_id = "test_req_abc123"
    response = client.get("/health", headers={"X-Request-ID": custom_req_id})

    assert response.status_code == 200
    headers = response.headers

    # Verify Correlation Request ID is preserved
    assert headers.get("X-Request-ID") == custom_req_id

    # Verify Security Headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "camera=()" in headers.get("Permissions-Policy", "")


def test_production_configuration_validation_fails_closed(monkeypatch):
    reset_settings()
    monkeypatch.setenv("ENVIRONMENT", "production")

    # In production with SQLite or default settings, validation must fail fast
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("JWT_SECRET_KEY", INSECURE_DEV_JWT_SECRET)
    monkeypatch.setenv("SIH_EMAIL_BACKEND", "simulated")

    with pytest.raises(RuntimeError) as exc_info:
        reset_settings()
        validate_production_configuration()

    err = str(exc_info.value)
    assert "Production requires PostgreSQL" in err
    assert "JWT secret" in err
    assert "SIH_EMAIL_BACKEND" in err

    reset_settings()


def test_sanitized_config_never_exposes_secrets(monkeypatch):
    monkeypatch.setenv("SMTP_PASSWORD", "secret_brevo_password_key_12345")
    monkeypatch.setenv("SMTP_USERNAME", "operator_admin@brevo.com")
    reset_settings()

    config = get_sanitized_config()
    assert "secret_brevo_password_key_12345" not in str(config)
    assert config["email_and_smtp"]["smtp_password_set"] is True
    assert config["email_and_smtp"]["smtp_username"] != "operator_admin@brevo.com"
    assert "***" in config["email_and_smtp"]["smtp_username"]

    reset_settings()


def test_metrics_endpoint_access_control(client, monkeypatch):
    from src.config import reset_settings
    # In production mode:
    monkeypatch.setenv("ENVIRONMENT", "production")
    reset_settings()

    # External untrusted IP receives 403 Forbidden
    res_forbidden = client.get("/metrics", headers={"X-Forwarded-For": "203.0.113.195"})
    assert res_forbidden.status_code == 403
    assert "restricted" in res_forbidden.json()["detail"].lower()

    # Localhost / loopback is permitted
    res_local = client.get("/metrics", headers={"X-Forwarded-For": "127.0.0.1"})
    assert res_local.status_code == 200

    # Request with valid METRICS_API_KEY is permitted
    monkeypatch.setenv("METRICS_API_KEY", "operator_secret_metrics_token_999")
    res_key = client.get("/metrics", headers={"X-Forwarded-For": "203.0.113.195", "X-Metrics-Key": "operator_secret_metrics_token_999"})
    assert res_key.status_code == 200

    reset_settings()
