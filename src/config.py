"""
Unified Production Configuration & Startup Invariant Validator
AI Powered Smart Hospital Referral System - Phase 3

Provides:
- Centralized configuration parsing with consistent environment variable naming
- Strict production validation (fails fast on missing/insecure production settings)
- Explicit separation between Development, Testing, and Production modes
- Sanitized configuration export (never logs or reveals secrets)
"""

import os
import re
import socket
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("sih.config")

INSECURE_DEV_JWT_SECRET = "sih-hospital-ai-demo-secret-change-later"


def _clean_str(val: Optional[str], default: str = "") -> str:
    return (val or default).strip()


def _to_bool(val: Any, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    return s in ("1", "true", "yes", "on")


class SystemSettings(BaseModel):
    """Immutable validated system configuration settings."""

    # Environment
    environment: str = Field(default="development")
    is_production: bool = Field(default=False)
    is_testing: bool = Field(default=False)

    # Server & Networking
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: List[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])

    # Database (PostgreSQL)
    database_url: str = Field(default="")
    is_postgres: bool = Field(default=False)
    db_pool_size: int = Field(default=10)
    db_max_overflow: int = Field(default=5)
    db_pool_timeout: int = Field(default=30)
    db_pool_recycle: int = Field(default=1800)

    # Redis
    redis_url: str = Field(default="")
    redis_required: bool = Field(default=False)

    # Authentication & Security
    jwt_secret_key: str = Field(default=INSECURE_DEV_JWT_SECRET)
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    applicant_token_expire_minutes: int = Field(default=1440)

    # Email & SMTP (Brevo)
    email_backend: str = Field(default="simulated")
    otp_provider: str = Field(default="SIMULATED")
    smtp_host: str = Field(default="")
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_email: str = Field(default="pawanbussiness108@gmail.com")
    smtp_use_tls: bool = Field(default=True)
    smtp_timeout: int = Field(default=10)

    # Portal Frontend URL
    portal_base_url: str = Field(default="http://localhost:3000")

    # Outbox Worker
    outbox_poll_interval: float = Field(default=5.0)
    outbox_batch_size: int = Field(default=10)
    outbox_lease_timeout_seconds: int = Field(default=300)
    outbox_max_retries: int = Field(default=5)

    # Storage
    storage_base_dir: str = Field(default="/tmp/sih_hospital_documents")
    max_document_size_mb: int = Field(default=10)
    enable_malware_scan: bool = Field(default=True)


_SETTINGS_INSTANCE: Optional[SystemSettings] = None


def load_settings() -> SystemSettings:
    """Read environment variables and construct SystemSettings."""
    env = _clean_str(os.getenv("ENVIRONMENT") or os.getenv("SIH_ENV") or "development").lower()
    is_prod = env in ("production", "prod")
    is_test = env in ("testing", "test")

    portal_base_url = (
        _clean_str(os.getenv("PORTAL_BASE_URL") or os.getenv("SIH_PORTAL_BASE_URL"))
        or "http://localhost:3000"
    ).rstrip("/")

    # CORS origins (combines explicit CORS_ORIGINS with PORTAL_BASE_URL and standard Vercel/local origins)
    default_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8050",
        "http://127.0.0.1:8050",
        "https://swasthya-samanvay.vercel.app",
        "https://arogyasetu-grid.vercel.app",
    ]
    if portal_base_url and portal_base_url not in default_origins:
        default_origins.append(portal_base_url)

    cors_raw = os.getenv("CORS_ORIGINS", "")
    if cors_raw:
        cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
        for origin in default_origins:
            if origin not in cors_origins:
                cors_origins.append(origin)
    else:
        cors_origins = default_origins

    # Database
    db_url = _clean_str(os.getenv("DATABASE_URL") or os.getenv("SIH_DATABASE_URL"))
    if not db_url:
        db_url = "sqlite:///data/hospital_app.db"
    is_pg = db_url.startswith("postgresql://") or db_url.startswith("postgres://") or db_url.startswith("postgresql+psycopg2://")

    # JWT secret
    jwt_secret = _clean_str(os.getenv("JWT_SECRET_KEY") or os.getenv("SIH_JWT_SECRET"))
    if not jwt_secret:
        jwt_secret = INSECURE_DEV_JWT_SECRET

    # Email backend and SMTP
    email_backend = _clean_str(os.getenv("SIH_EMAIL_BACKEND") or os.getenv("EMAIL_BACKEND") or "simulated").lower()
    otp_provider = _clean_str(os.getenv("SIH_OTP_PROVIDER") or "SIMULATED").upper()

    smtp_host = _clean_str(os.getenv("SMTP_HOST") or os.getenv("SIH_SMTP_HOST"))
    smtp_port = int(os.getenv("SMTP_PORT") or os.getenv("SIH_SMTP_PORT") or "587")
    smtp_user = _clean_str(os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or os.getenv("SIH_SMTP_USER"))
    smtp_pass = os.getenv("SMTP_PASSWORD") or os.getenv("SIH_SMTP_PASSWORD") or ""
    smtp_from = _clean_str(os.getenv("SMTP_FROM_EMAIL") or os.getenv("SMTP_FROM") or os.getenv("SIH_SMTP_FROM") or "pawanbussiness108@gmail.com")
    smtp_tls = _to_bool(os.getenv("SMTP_USE_TLS") or os.getenv("SIH_SMTP_USE_TLS"), default=True)
    smtp_timeout = int(os.getenv("SMTP_TIMEOUT") or os.getenv("SIH_SMTP_TIMEOUT") or "10")

    portal_base_url = (
        _clean_str(os.getenv("PORTAL_BASE_URL") or os.getenv("SIH_PORTAL_BASE_URL"))
        or "http://localhost:3000"
    ).rstrip("/")

    return SystemSettings(
        environment=env,
        is_production=is_prod,
        is_testing=is_test,
        host=_clean_str(os.getenv("HOST"), "0.0.0.0"),
        port=int(os.getenv("PORT") or "8000"),
        cors_origins=cors_origins,
        portal_base_url=portal_base_url,
        database_url=db_url,
        is_postgres=is_pg,
        db_pool_size=int(os.getenv("DB_POOL_SIZE") or os.getenv("SIH_DB_POOL_SIZE") or "10"),
        db_max_overflow=int(os.getenv("DB_MAX_OVERFLOW") or os.getenv("SIH_DB_MAX_OVERFLOW") or "5"),
        db_pool_timeout=int(os.getenv("DB_POOL_TIMEOUT") or os.getenv("SIH_DB_POOL_TIMEOUT") or "30"),
        db_pool_recycle=int(os.getenv("DB_POOL_RECYCLE") or os.getenv("SIH_DB_POOL_RECYCLE") or "1800"),
        redis_url=_clean_str(os.getenv("REDIS_URL") or os.getenv("SIH_REDIS_URL")),
        redis_required=_to_bool(os.getenv("REDIS_REQUIRED") or os.getenv("SIH_REQUIRE_REDIS"), default=False),
        jwt_secret_key=jwt_secret,
        jwt_algorithm=_clean_str(os.getenv("JWT_ALGORITHM"), "HS256"),
        access_token_expire_minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES") or "60"),
        applicant_token_expire_minutes=int(os.getenv("APPLICANT_JWT_EXPIRE_MINUTES") or "1440"),
        email_backend=email_backend,
        otp_provider=otp_provider,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_username=smtp_user,
        smtp_password=smtp_pass,
        smtp_from_email=smtp_from,
        smtp_use_tls=smtp_tls,
        smtp_timeout=smtp_timeout,
        outbox_poll_interval=float(os.getenv("OUTBOX_POLL_INTERVAL") or "5.0"),
        outbox_batch_size=int(os.getenv("OUTBOX_BATCH_SIZE") or "10"),
        outbox_lease_timeout_seconds=int(os.getenv("OUTBOX_LEASE_TIMEOUT_SECONDS") or "300"),
        outbox_max_retries=int(os.getenv("OUTBOX_MAX_RETRIES") or "5"),
        storage_base_dir=_clean_str(os.getenv("STORAGE_BASE_DIR") or "/tmp/sih_hospital_documents"),
        max_document_size_mb=int(os.getenv("MAX_DOCUMENT_SIZE_MB") or "10"),
        enable_malware_scan=_to_bool(os.getenv("ENABLE_MALWARE_SCAN"), default=True),
    )


def get_settings() -> SystemSettings:
    """Retrieve global system settings singleton."""
    global _SETTINGS_INSTANCE
    if _SETTINGS_INSTANCE is None:
        _SETTINGS_INSTANCE = load_settings()
    return _SETTINGS_INSTANCE


def reset_settings() -> None:
    """Reset cached settings instance (for tests)."""
    global _SETTINGS_INSTANCE
    _SETTINGS_INSTANCE = None


def mask_secret(val: str, reveal_len: int = 3) -> str:
    """Safely mask sensitive strings for logging."""
    if not val:
        return "<not set>"
    if len(val) <= reveal_len * 2:
        return "***"
    return f"{val[:reveal_len]}***{val[-reveal_len:]}"


def mask_email(email: str) -> str:
    """Safely mask email addresses for logging."""
    if not email or "@" not in email:
        return "***"
    user, domain = email.split("@", 1)
    masked_user = user[0] + "***" if len(user) > 1 else "*"
    return f"{masked_user}@{domain}"


def get_sanitized_config() -> Dict[str, Any]:
    """Return a dictionary of all active configurations with all credentials masked."""
    s = get_settings()
    parsed_db = urlparse(s.database_url)
    sanitized_db = f"{parsed_db.scheme}://{parsed_db.hostname or 'local'}:{parsed_db.port or 'default'}/{parsed_db.path.lstrip('/')}"

    return {
        "environment": s.environment,
        "is_production": s.is_production,
        "host": s.host,
        "port": s.port,
        "cors_origins": s.cors_origins,
        "portal_base_url": s.portal_base_url,
        "database": {
            "sanitized_url": sanitized_db,
            "is_postgres": s.is_postgres,
            "pool_size": s.db_pool_size,
            "max_overflow": s.db_max_overflow,
            "pool_timeout": s.db_pool_timeout,
            "pool_recycle": s.db_pool_recycle,
        },
        "redis": {
            "configured": bool(s.redis_url),
            "required": s.redis_required,
        },
        "security": {
            "jwt_secret_configured": bool(s.jwt_secret_key and s.jwt_secret_key != INSECURE_DEV_JWT_SECRET),
            "jwt_algorithm": s.jwt_algorithm,
            "access_token_expire_minutes": s.access_token_expire_minutes,
        },
        "email_and_smtp": {
            "email_backend": s.email_backend,
            "otp_provider": s.otp_provider,
            "smtp_host": s.smtp_host or "<not set>",
            "smtp_port": s.smtp_port,
            "smtp_username": mask_secret(s.smtp_username),
            "smtp_password_set": bool(s.smtp_password),
            "smtp_from_email": mask_email(s.smtp_from_email),
            "smtp_use_tls": s.smtp_use_tls,
            "mailjet_configured": bool(os.getenv("MAILJET_API_KEY") and os.getenv("MAILJET_SECRET_KEY")),
        },
        "outbox_worker": {
            "poll_interval": s.outbox_poll_interval,
            "batch_size": s.outbox_batch_size,
            "lease_timeout": s.outbox_lease_timeout_seconds,
            "max_retries": s.outbox_max_retries,
        },
        "storage": {
            "base_dir": s.storage_base_dir,
            "max_size_mb": s.max_document_size_mb,
            "malware_scan": s.enable_malware_scan,
        },
    }


def validate_production_configuration() -> None:
    """
    Startup invariant check: validates all requirements when running in production.
    Fails fast (raises RuntimeError) if ANY production invariant is violated.
    Does NOT silently fall back to insecure or simulated implementations.
    """
    s = get_settings()
    if not s.is_production:
        return

    logger.info("Executing comprehensive production startup configuration audit...")
    violations: List[str] = []

    # 1. Database validation: Must be PostgreSQL and reachable
    if not s.is_postgres:
        violations.append("Production requires PostgreSQL. SQLite or JSON database fallback is strictly prohibited.")
    else:
        try:
            from src.database.db_manager import check_db_health
            db_health = check_db_health()
            if db_health.get("status") != "HEALTHY":
                violations.append(f"Production PostgreSQL connectivity check failed: {db_health.get('error')}")
        except Exception as exc:
            violations.append(f"Production PostgreSQL check threw exception: {exc}")

    # 2. Security validation: JWT secret must be strong and non-default
    if not s.jwt_secret_key or s.jwt_secret_key == INSECURE_DEV_JWT_SECRET or len(s.jwt_secret_key) < 32:
        violations.append(
            "Production requires a strong JWT secret (SIH_JWT_SECRET / JWT_SECRET_KEY) "
            "of at least 32 characters. Insecure demo fallback secret is forbidden."
        )

    # 3. CORS validation: Wildcard forbidden when allow_credentials=True
    if "*" in s.cors_origins:
        violations.append("Production CORS policy forbids wildcard '*' when credentials are permitted.")

    # 4. Email validation: Must be SMTP or Mailjet, credentials must be configured, no simulated fallback
    if s.email_backend not in ("smtp", "mailjet"):
        violations.append(
            f"Production forbids email backend '{s.email_backend}'. "
            "SIH_EMAIL_BACKEND must be set to 'mailjet' or 'smtp' for live delivery."
        )
    if s.email_backend == "smtp" and not s.smtp_host:
        violations.append("Production requires SMTP_HOST (e.g. smtp-relay.brevo.com).")
    if s.email_backend == "mailjet":
        mailjet_key = (os.getenv("MAILJET_API_KEY") or os.getenv("SIH_MAILJET_API_KEY") or "").strip()
        mailjet_secret = (os.getenv("MAILJET_SECRET_KEY") or os.getenv("SIH_MAILJET_SECRET_KEY") or "").strip()
        if not mailjet_key or not mailjet_secret:
            violations.append("Production Mailjet email backend requires MAILJET_API_KEY and MAILJET_SECRET_KEY.")
    if not s.smtp_from_email or "@" not in s.smtp_from_email:
        violations.append("Production requires a valid SMTP_FROM_EMAIL sender address.")
    if s.otp_provider == "SIMULATED" or s.otp_provider == "CONSOLE":
        violations.append(f"Production forbids SIH_OTP_PROVIDER='{s.otp_provider}'. Must be set to 'EMAIL'.")

    # 5. Redis validation (if required or in multi-instance production)
    if s.redis_required:
        if not s.redis_url:
            violations.append("REDIS_REQUIRED is enabled but REDIS_URL is not set.")
        else:
            try:
                import redis
                client = redis.Redis.from_url(s.redis_url, socket_timeout=3.0)
                client.ping()
            except Exception as r_err:
                violations.append(f"Production Redis connectivity check failed: {r_err}")

    # 6. Storage directory validation: Must exist or be writable
    if not os.path.exists(s.storage_base_dir):
        try:
            os.makedirs(s.storage_base_dir, exist_ok=True)
        except Exception as st_err:
            violations.append(f"Cannot initialize production storage directory '{s.storage_base_dir}': {st_err}")

    if violations:
        error_msg = (
            "CRITICAL PRODUCTION CONFIGURATION INVARIANT VIOLATION:\n  - "
            + "\n  - ".join(violations)
            + "\nStartup aborted. Fix configuration in environment or .env before starting production."
        )
        logger.critical(error_msg)
        raise RuntimeError(error_msg)

    logger.info("Production configuration audit PASSED. All invariants verified.")
