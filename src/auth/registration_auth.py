"""
Applicant & Registration Reviewer Authentication and Authorization Dependencies
AI Powered Smart Hospital Referral System - Phase 1 Task 1D

Provides separate restricted APPLICANT authentication contexts, session token
issuance, verification against token revocation blocklists, and role-based reviewer
guardrails ensuring operational hospital users and applicants cannot cross security boundaries.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
import jwt
from fastapi import Header, HTTPException

from src.auth.jwt_utils import get_jwt_secret, ALGORITHM
from src.auth.rate_limiter import is_token_revoked, is_user_session_revoked

logger = logging.getLogger("registration_auth")

APPLICANT_TOKEN_EXPIRE_HOURS = 2
REVIEWER_ROLES = {"DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"}


def create_applicant_token(data: Dict[str, Any]) -> str:
    """
    Issue a signed JWT access token specifically scoped to the APPLICANT context.
    Applicants are strictly isolated from operational hospital staff and system administrators.
    """
    now = datetime.now(timezone.utc)
    secret_key = get_jwt_secret()

    payload = {
        "sub": f"APPLICANT:{data['application_number']}",
        "role": "APPLICANT",
        "application_number": data["application_number"],
        "application_id": data["application_id"],
        "applicant_type": data.get("applicant_type"),
        "applicant_email": data.get("applicant_email"),
        "state": data.get("state"),
        "district": data.get("district"),
        "iat": now,
        "exp": now + timedelta(hours=APPLICANT_TOKEN_EXPIRE_HOURS),
    }

    return jwt.encode(payload, secret_key, algorithm=ALGORITHM)


def decode_applicant_token(token: str, check_revocation: bool = True) -> Optional[Dict[str, Any]]:
    """
    Verify and decode an APPLICANT JWT access token.
    Validates signature, expiration, role='APPLICANT', and checks distributed revocation.
    """
    if not token or not isinstance(token, str):
        return None

    if check_revocation and is_token_revoked(token):
        logger.warning("Rejected attempt to use revoked applicant JWT.")
        return None

    try:
        secret_key = get_jwt_secret()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        if payload.get("role") != "APPLICANT":
            logger.warning("Decoded token role mismatch: expected APPLICANT, got %s", payload.get("role"))
            return None
        if check_revocation:
            sub = payload.get("sub")
            iat = payload.get("iat")
            if sub and is_user_session_revoked(sub, iat):
                logger.warning("Rejected attempt to use applicant JWT issued prior to session revocation for %s.", sub)
                return None
        return payload
    except (jwt.PyJWTError, Exception) as exc:
        logger.debug("Applicant JWT validation failed: %s", exc)
        return None


def require_applicant_user(
    authorization: str | None = Header(default=None)
) -> Dict[str, Any]:
    """
    FastAPI dependency validating Bearer APPLICANT JWT token.
    Enforces authorization header format, signature, revocation, and APPLICANT role.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token required."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    if is_token_revoked(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked or logged out."
        )

    applicant = decode_applicant_token(token)
    if applicant is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid, expired, or non-applicant access token."
        )

    return applicant


def require_reviewer_user(
    authorization: str | None = Header(default=None)
) -> Dict[str, Any]:
    """
    FastAPI dependency validating authorized registration reviewers:
    - Must possess a valid, non-revoked JWT access token.
    - Role must be in {DISTRICT_ADMIN, STATE_ADMIN, CENTRAL_ADMIN}.
    - Operational hospital users (HOSPITAL) and applicants (APPLICANT) are strictly forbidden.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token required."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    if is_token_revoked(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked."
        )

    try:
        secret_key = get_jwt_secret()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except (jwt.PyJWTError, Exception) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token."
        ) from exc

    sub = payload.get("sub")
    iat = payload.get("iat")
    if sub and is_user_session_revoked(sub, iat):
        raise HTTPException(
            status_code=401,
            detail="Session has been revoked. Please log in again."
        )

    role = payload.get("role")
    if role == "APPLICANT":
        raise HTTPException(
            status_code=403,
            detail="Applicant credentials cannot be used to access administrative reviewer endpoints."
        )
    if role == "HOSPITAL":
        raise HTTPException(
            status_code=403,
            detail="Hospital staff role is not permitted to review registration applications."
        )
    if role not in REVIEWER_ROLES:
        raise HTTPException(
            status_code=403,
            detail=f"User role '{role}' is unauthorized to review registration applications."
        )

    return payload


def get_caller_user_context(
    authorization: str | None = Header(default=None)
) -> Dict[str, Any]:
    """
    FastAPI dependency validating caller context for document download/inspection:
    Permits both authenticated APPLICANT and authenticated REVIEWER users.
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization token required."
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    if is_token_revoked(token):
        raise HTTPException(
            status_code=401,
            detail="Token has been revoked or logged out."
        )

    # 1. Try APPLICANT token
    app_payload = decode_applicant_token(token, check_revocation=False)
    if app_payload:
        return app_payload

    # 2. Try standard reviewer token
    try:
        secret_key = get_jwt_secret()
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        sub = payload.get("sub")
        iat = payload.get("iat")
        if sub and is_user_session_revoked(sub, iat):
            raise HTTPException(
                status_code=401,
                detail="Session has been revoked. Please log in again."
            )
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token."
        ) from exc
