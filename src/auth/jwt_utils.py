"""
JWT Utility Functions
AI Powered Smart Hospital Referral System - Phase 17
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt

from src.auth.rate_limiter import is_token_revoked, is_user_session_revoked

logger = logging.getLogger(__name__)

INSECURE_DEV_SECRET = "sih-hospital-ai-demo-secret-change-later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def get_jwt_secret() -> str:
    """
    Validate and return the JWT secret key.
    Enforces that production and staging environments MUST have a secure,
    non-default SIH_JWT_SECRET environment variable of at least 32 characters.
    In development mode, a clearly separated dev secret is allowed with a warning.
    """
    env = os.getenv("SIH_ENV", os.getenv("ENVIRONMENT", "development")).lower().strip()
    secret = os.getenv("SIH_JWT_SECRET", os.getenv("JWT_SECRET_KEY", "")).strip()

    is_production = env in ("production", "prod", "staging", "demo")

    if is_production:
        if not secret or secret == INSECURE_DEV_SECRET or len(secret) < 32:
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: SIH_JWT_SECRET must be set to a strong, "
                "unique key (minimum 32 characters) in production/staging environments. "
                "Using the insecure development fallback secret is strictly prohibited in production."
            )
        return secret

    # Development mode fallback
    if not secret:
        return INSECURE_DEV_SECRET
    return secret


def validate_production_security_config():
    """Startup check: fails application initialization if configuration is insecure in production."""
    get_jwt_secret()


def create_access_token(user: dict) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    secret_key = get_jwt_secret()

    payload = {
        "sub": user.get("user_id"),
        "user_id": user.get("user_id"),
        "username": user.get("username"),
        "role": user.get("role"),
        "hospital_id": user.get("hospital_id"),
        "state": user.get("state"),
        "district": user.get("district"),
        "email": user.get("email"),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str, check_revocation: bool = True) -> Optional[dict]:
    """
    Verify and decode a signed JWT access token.
    Enforces algorithm HS256, verifies signature, expiration, and checks distributed revocation blocklist.
    """
    if not token or not isinstance(token, str):
        return None

    # Check revocation blocklist first
    if check_revocation and is_token_revoked(token):
        logger.warning("Rejected attempt to use revoked JWT.")
        return None

    try:
        secret_key = get_jwt_secret()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        if check_revocation:
            user_id = payload.get("sub") or payload.get("user_id")
            username = payload.get("username")
            iat = payload.get("iat")
            if (user_id and is_user_session_revoked(user_id, iat)) or (username and is_user_session_revoked(username, iat)):
                logger.warning("Rejected attempt to use JWT issued prior to session revocation for user '%s'.", user_id)
                return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.debug("JWT validation failed: signature expired.")
        return None
    except jwt.InvalidTokenError as e:
        logger.debug("JWT validation failed: invalid token (%s).", e)
        return None
    except Exception as e:
        logger.warning("Unexpected error decoding JWT: %s", e)
        return None
