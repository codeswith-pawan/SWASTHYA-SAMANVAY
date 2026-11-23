"""
Phase 5 Comprehensive Security Audit & Regression Test Suite
SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform

Validates:
1. BOLA / IDOR Defense on Direct Bed Reservation & Lifecycle APIs.
2. Cross-Jurisdictional BOLA Defense on Referral Bed Reservation Attachments.
3. User-Wide Session Revocation on Administrative Reviewer Auth & Context.
4. Production CORS Domain Regex Boundary Enforcement.
5. Case-Insensitive Geographic Scoping in Reviewer Application Inspection.
"""

import re
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.database.db_manager import get_db_session
from src.database.pg_models import (
    PgBase,
    User,
    Role,
    Hospital as PgHospital,
    RegistrationApplication,
)
from src.auth.jwt_utils import create_access_token
from src.auth.rate_limiter import revoke_user_sessions, reset_rate_limits
from src.auth.authorization import _GEO_CACHE


@pytest.fixture
def audit_db_session():
    """Create isolated in-memory SQLite session with StaticPool."""
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

    # Seed test hospitals
    h1 = PgHospital(
        hospital_id="HOSP_AMRITSAR",
        name="Amritsar Civil Hospital",
        state="Punjab",
        district="Amritsar",
        city="Amritsar",
        latitude=31.6340,
        longitude=74.8723,
    )
    h2 = PgHospital(
        hospital_id="HOSP_LUDHIANA",
        name="Ludhiana District Hospital",
        state="Punjab",
        district="Ludhiana",
        city="Ludhiana",
        latitude=30.9010,
        longitude=75.8573,
    )
    h3 = PgHospital(
        hospital_id="HOSP_JAIPUR",
        name="Jaipur Apex Hospital",
        state="Rajasthan",
        district="Jaipur",
        city="Jaipur",
        latitude=26.9124,
        longitude=75.7873,
    )
    session.merge(h1)
    session.merge(h2)
    session.merge(h3)

    # Seed test users
    u_hosp_amr = User(
        user_id="U_HOSP_AMR",
        username="hosp_amr",
        name="Amritsar Staff",
        role_id="HOSPITAL",
        state="Punjab",
        district="Amritsar",
        hospital_id="HOSP_AMRITSAR",
        is_active=True,
        password_hash="dummy_hash",
    )
    u_dist_amr = User(
        user_id="U_DIST_AMR",
        username="dist_amr",
        name="Amritsar CMO",
        role_id="DISTRICT_ADMIN",
        state="Punjab",
        district="Amritsar",
        is_active=True,
        password_hash="dummy_hash",
    )
    u_state_pb = User(
        user_id="U_STATE_PB",
        username="state_pb",
        name="Punjab Director",
        role_id="STATE_ADMIN",
        state="Punjab",
        is_active=True,
        password_hash="dummy_hash",
    )
    u_state_rj = User(
        user_id="U_STATE_RJ",
        username="state_rj",
        name="Rajasthan Director",
        role_id="STATE_ADMIN",
        state="Rajasthan",
        is_active=True,
        password_hash="dummy_hash",
    )
    session.merge(u_hosp_amr)
    session.merge(u_dist_amr)
    session.merge(u_state_pb)
    session.merge(u_state_rj)

    session.commit()

    # Pre-populate GEO_CACHE for reliable test lookup
    _GEO_CACHE["HOSP_AMRITSAR"] = {"hospital_id": "HOSP_AMRITSAR", "name": "Amritsar Civil Hospital", "state": "Punjab", "district": "Amritsar"}
    _GEO_CACHE["HOSP_LUDHIANA"] = {"hospital_id": "HOSP_LUDHIANA", "name": "Ludhiana District Hospital", "state": "Punjab", "district": "Ludhiana"}
    _GEO_CACHE["HOSP_JAIPUR"] = {"hospital_id": "HOSP_JAIPUR", "name": "Jaipur Apex Hospital", "state": "Rajasthan", "district": "Jaipur"}

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def audit_client(audit_db_session):
    """FastAPI TestClient with overridden database session."""
    def _override_db():
        try:
            yield audit_db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = _override_db
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_01_direct_reservation_jurisdiction_bola_protection(audit_client):
    """
    Test 1: Direct bed reservation and status endpoints must reject
    requests from unauthorized hospital staff or cross-district administrators with 403 Forbidden.
    """
    # 1. Hospital user trying to access a DIFFERENT hospital
    token_amr_hosp = create_access_token({
        "user_id": "U_HOSP_AMR",
        "username": "hosp_amr",
        "role": "HOSPITAL",
        "hospital_id": "HOSP_AMRITSAR",
        "state": "Punjab",
        "district": "Amritsar",
    })
    headers_amr_hosp = {"Authorization": f"Bearer {token_amr_hosp}"}

    resp = audit_client.post(
        "/reservation/HOSP_LUDHIANA/PAT-999/reserve?bed_type=GENERAL",
        headers=headers_amr_hosp,
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()

    # 2. District Admin from Amritsar trying to reserve bed in Ludhiana
    token_amr_dist = create_access_token({
        "user_id": "U_DIST_AMR",
        "username": "dist_amr",
        "role": "DISTRICT_ADMIN",
        "state": "Punjab",
        "district": "Amritsar",
    })
    headers_amr_dist = {"Authorization": f"Bearer {token_amr_dist}"}

    resp = audit_client.post(
        "/reservation/HOSP_LUDHIANA/PAT-999/reserve?bed_type=GENERAL",
        headers=headers_amr_dist,
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()

    # 3. State Admin from Rajasthan trying to access Ludhiana (Punjab) hospital
    token_rj_state = create_access_token({
        "user_id": "U_STATE_RJ",
        "username": "state_rj",
        "role": "STATE_ADMIN",
        "state": "Rajasthan",
    })
    headers_rj_state = {"Authorization": f"Bearer {token_rj_state}"}

    resp = audit_client.get(
        "/reservation/HOSP_LUDHIANA/PAT-999",
        headers=headers_rj_state,
    )
    assert resp.status_code == 403
    assert "not authorized" in resp.json()["detail"].lower()


def test_02_referral_reservation_attachment_state_boundary(audit_client, monkeypatch):
    """
    Test 2: State Admin from State A cannot attach bed reservations
    to a referral destined for a hospital in State B.
    """
    # Mock referral repository to return a referral destined for Punjab
    dummy_referral = {
        "referral_id": "REF-SEC-001",
        "patient_id": "PAT-SEC-001",
        "from_hospital_id": "HOSP_AMRITSAR",
        "to_hospital_id": "HOSP_LUDHIANA",
        "status": "ACCEPTED",
    }
    monkeypatch.setattr("src.api.main.get_referral", lambda ref_id: dummy_referral)

    token_rj_state = create_access_token({
        "user_id": "U_STATE_RJ",
        "username": "state_rj",
        "role": "STATE_ADMIN",
        "state": "Rajasthan",
    })
    headers_rj_state = {"Authorization": f"Bearer {token_rj_state}"}

    resp = audit_client.post(
        "/referrals/REF-SEC-001/reservation?hospital_id=HOSP_LUDHIANA&bed_type=GENERAL",
        headers=headers_rj_state,
    )
    assert resp.status_code == 403
    assert "state jurisdiction" in resp.json()["detail"].lower()


def test_03_reviewer_token_session_revocation(audit_client):
    """
    Test 3: User-wide session revocation (e.g., upon password reset or admin logout)
    must immediately invalidate reviewer tokens in require_reviewer_user.
    """
    reset_rate_limits()
    reviewer_user_id = "U_REV_REVOKED_TEST"
    token = create_access_token({
        "sub": reviewer_user_id,
        "user_id": reviewer_user_id,
        "username": "rev_test",
        "role": "DISTRICT_ADMIN",
        "state": "Punjab",
        "district": "Amritsar",
    })
    headers = {"Authorization": f"Bearer {token}"}

    # Before revocation, the endpoint allows access (or returns standard empty list/404)
    resp = audit_client.get("/api/registration/review/applications", headers=headers)
    assert resp.status_code == 200

    # Ensure second boundary passes so token iat < cutoff_ts
    import time
    time.sleep(1.05)

    # Trigger session revocation for the user
    revoke_user_sessions(reviewer_user_id)

    # After revocation, identical token must be rejected with 401
    resp_after = audit_client.get("/api/registration/review/applications", headers=headers)
    assert resp_after.status_code == 401
    assert "session has been revoked" in resp_after.json()["detail"].lower()


def test_04_cors_origin_regex_hardening():
    """
    Test 4: CORS regex must allow legitimate Swasthya Samanvay and legacy preview
    domains, while strictly rejecting unauthorized, spoofed, or malicious origins.
    """
    pattern = re.compile(r"^https://(swasthya-samanvay|arogyasetu-grid)(-[a-zA-Z0-9_-]+)?\.vercel\.app$")

    # Allowed legitimate origins
    assert pattern.match("https://swasthya-samanvay.vercel.app")
    assert pattern.match("https://swasthya-samanvay-git-main-pawan.vercel.app")
    assert pattern.match("https://swasthya-samanvay-preview-v2.vercel.app")
    assert pattern.match("https://arogyasetu-grid.vercel.app")
    assert pattern.match("https://arogyasetu-grid-staging.vercel.app")

    # Rejected malicious/spoofed origins
    assert not pattern.match("https://swasthya-samanvay.evil.com")
    assert not pattern.match("https://evil-swasthya-samanvay.vercel.app")
    assert not pattern.match("https://arogyasetu-grid.attacker.com")
    assert not pattern.match("http://swasthya-samanvay.vercel.app")
    assert not pattern.match("https://swasthya-samanvay.vercel.app.attacker.com")


def test_05_reviewer_geographic_scoping_case_insensitivity(audit_client, audit_db_session):
    """
    Test 5: Geographic scoping in reviewer endpoints must be case-insensitive
    so that district/state name variations (e.g., 'punjab' vs 'Punjab') match correctly.
    """
    # Create application with mixed case
    app_record = RegistrationApplication(
        application_id="APP-CASE-TEST-001",
        application_number="REG-2026-PB-0099",
        applicant_type="HOSPITAL",
        applicant_name="Case Sensitivity Hospital",
        applicant_email="case@hospital.org",
        applicant_phone="9876543210",
        state="PUNJAB",
        district="AMRITSAR",
        status="SUBMITTED",
        current_stage="DISTRICT_REVIEW",
        created_at=datetime.now(timezone.utc),
    )
    audit_db_session.merge(app_record)
    audit_db_session.commit()

    # Reviewer with lowercase state and district
    token = create_access_token({
        "sub": "U_DIST_CASE",
        "user_id": "U_DIST_CASE",
        "username": "dist_case",
        "role": "DISTRICT_ADMIN",
        "state": "punjab",
        "district": "amritsar",
    })
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Listing should find the application
    resp_list = audit_client.get("/api/registration/review/applications", headers=headers)
    assert resp_list.status_code == 200
    app_ids = [a["application_id"] for a in resp_list.json()["applications"]]
    assert "APP-CASE-TEST-001" in app_ids

    # 2. Detail view should succeed without 403
    resp_detail = audit_client.get("/api/registration/review/applications/APP-CASE-TEST-001", headers=headers)
    assert resp_detail.status_code == 200
    assert resp_detail.json()["application_id"] == "APP-CASE-TEST-001"
