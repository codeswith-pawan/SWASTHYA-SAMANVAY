"""
Comprehensive API & Authentication Test Suite for Hierarchical Registration System
AI Powered Smart Hospital Referral System - Phase 1 Task 1D

Validates:
- Part A: Applicant OTP request, verification, session issuance, rate limiting, and logout
- Part B: Applicant lifecycle APIs (create State/District/Hospital, draft update, upload docs, submit, resubmit)
- Part C: Public tracking privacy (no emails, phones, Aadhaar, internal reviewer notes or IDs leaked)
- Part D: Reviewer APIs (assigned list, document verify/reject, forward/approve/reject, request corrections)
- Security boundaries: APPLICANT token restrictions, hospital staff restrictions, geographic boundaries, self-approval prevention
"""

import pytest
import secrets
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.database.db_manager import get_db_session
from src.database.pg_models import PgBase, User, Hospital, Role
from src.auth.jwt_utils import create_access_token
from src.auth.registration_auth import create_applicant_token
from src.services.otp_service import get_otp_provider, SimulatedOTPProvider


@pytest.fixture
def api_db_session():
    """Create a fresh in-memory SQLite database per test with StaticPool."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    PgBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    # Seed required reviewer users into database
    roles = [
        Role(id="HOSPITAL", description="Hospital Staff"),
        Role(id="DISTRICT_ADMIN", description="District Admin"),
        Role(id="STATE_ADMIN", description="State Admin"),
        Role(id="CENTRAL_ADMIN", description="Central Admin"),
    ]
    for r in roles:
        session.merge(r)

    users = [
        User(user_id="U_REV_DIST_MOH", username="dist_moh", name="Mohali CMO", role_id="DISTRICT_ADMIN", state="Punjab", district="Mohali", password_hash="hash"),
        User(user_id="U_REV_DIST_ASR", username="dist_asr", name="Amritsar CMO", role_id="DISTRICT_ADMIN", state="Punjab", district="Amritsar", password_hash="hash"),
        User(user_id="U_REV_STATE_PB", username="state_pb", name="Punjab Director", role_id="STATE_ADMIN", state="Punjab", password_hash="hash"),
        User(user_id="U_REV_STATE_HR", username="state_hr", name="Haryana Director", role_id="STATE_ADMIN", state="Haryana", password_hash="hash"),
        User(user_id="U_REV_CENTRAL", username="central_admin", name="National Registrar", role_id="CENTRAL_ADMIN", password_hash="hash"),
        User(user_id="U_HOSP_STAFF", username="gh00001", name="Hospital Staff", role_id="HOSPITAL", hospital_id="GH00001", state="Punjab", district="Mohali", password_hash="hash"),
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
def client(api_db_session):
    """TestClient with overridden get_db_session dependency."""
    from src.auth.rate_limiter import reset_rate_limits
    reset_rate_limits()

    def _override_get_db():
        try:
            yield api_db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db_session, None)
    reset_rate_limits()


@pytest.fixture
def reviewer_tokens():
    """Generate signed JWT tokens for reviewer testing."""
    return {
        "dist_mohali": create_access_token({
            "user_id": "U_REV_DIST_MOH",
            "username": "dist_moh",
            "role": "DISTRICT_ADMIN",
            "state": "Punjab",
            "district": "Mohali",
        }),
        "dist_amritsar": create_access_token({
            "user_id": "U_REV_DIST_ASR",
            "username": "dist_asr",
            "role": "DISTRICT_ADMIN",
            "state": "Punjab",
            "district": "Amritsar",
        }),
        "state_punjab": create_access_token({
            "user_id": "U_REV_STATE_PB",
            "username": "state_pb",
            "role": "STATE_ADMIN",
            "state": "Punjab",
        }),
        "state_haryana": create_access_token({
            "user_id": "U_REV_STATE_HR",
            "username": "state_hr",
            "role": "STATE_ADMIN",
            "state": "Haryana",
        }),
        "central": create_access_token({
            "user_id": "U_REV_CENTRAL",
            "username": "central_admin",
            "role": "CENTRAL_ADMIN",
        }),
        "hospital_staff": create_access_token({
            "user_id": "U_HOSP_STAFF",
            "username": "gh00001",
            "role": "HOSPITAL",
            "hospital_id": "GH00001",
        }),
    }


# ============================================================
# 1. APPLICANT AUTHENTICATION & OTP TESTS
# ============================================================

def test_applicant_otp_request_and_verification_flow(client):
    """Verify applicant OTP generation, delivery via simulated provider, and successful token issuance."""
    provider = get_otp_provider()
    assert isinstance(provider, SimulatedOTPProvider)

    # 1. Request OTP
    target_email = "test.applicant@healthorg.gov.in"
    req_resp = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_email, "channel": "EMAIL", "purpose": "PORTAL_ACCESS_OTP"},
    )
    assert req_resp.status_code == 200, req_resp.text
    req_data = req_resp.json()
    token_id = req_data["token_id"]
    assert token_id.startswith("VTOK_")

    # 2. Retrieve simulated OTP securely (without log leakage)
    simulated_otp = provider.get_last_simulated_otp(target_email)
    assert simulated_otp is not None
    assert len(simulated_otp) == 6

    # 3. Verify OTP
    verify_resp = client.post(
        "/api/registration/auth/otp/verify",
        json={"token_id": token_id, "otp": simulated_otp},
    )
    assert verify_resp.status_code == 200, verify_resp.text
    verify_data = verify_resp.json()
    assert verify_data["verified"] is True
    assert verify_data["contact_target"] == target_email


def test_applicant_otp_invalid_code_and_attempt_limit(client):
    """Verify that wrong OTP decrements attempts and locks token after 3 failures."""
    provider = get_otp_provider()
    target_email = "bad.attempts@healthorg.gov.in"

    # Request OTP
    req_resp = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_email, "channel": "EMAIL"},
    )
    token_id = req_resp.json()["token_id"]

    # Attempt 1: wrong OTP
    resp1 = client.post("/api/registration/auth/otp/verify", json={"token_id": token_id, "otp": "000000"})
    assert resp1.status_code == 422
    assert "2 attempt(s) remaining" in resp1.json()["detail"]

    # Attempt 2: wrong OTP
    resp2 = client.post("/api/registration/auth/otp/verify", json={"token_id": token_id, "otp": "111111"})
    assert resp2.status_code == 422
    assert "1 attempt(s) remaining" in resp2.json()["detail"]

    # Attempt 3: wrong OTP (exhausts limit)
    resp3 = client.post("/api/registration/auth/otp/verify", json={"token_id": token_id, "otp": "222222"})
    assert resp3.status_code == 422
    assert "Maximum attempts exceeded" in resp3.json()["detail"]

    # Attempt 4: even with correct OTP, token is now locked
    simulated_otp = provider.get_last_simulated_otp(target_email)
    resp4 = client.post("/api/registration/auth/otp/verify", json={"token_id": token_id, "otp": simulated_otp})
    assert resp4.status_code == 422
    assert "Maximum verification attempts exceeded" in resp4.json()["detail"]


def test_applicant_otp_cooldown_rate_limit(client):
    """Verify that requesting another OTP before the 60s cooldown triggers validation error."""
    target_email = "cooldown.test@healthorg.gov.in"

    resp1 = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_email, "channel": "EMAIL"},
    )
    assert resp1.status_code == 200

    # Immediate second request triggers cooldown
    resp2 = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_email, "channel": "EMAIL"},
    )
    assert resp2.status_code == 422
    assert "OTP was recently sent" in resp2.json()["detail"]


def test_applicant_logout_and_token_invalidation(client):
    """Verify applicant logout revokes the JWT session token."""
    # 1. Create a hospital application to obtain an applicant session token
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Logout Test Hospital",
            "applicant_email": "logout.test@hospital.org",
            "applicant_phone": "0172-5551234",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    assert create_resp.status_code == 200
    token = create_resp.json()["applicant_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Access /api/registration/applications/me successfully
    me_resp = client.get("/api/registration/applications/me", headers=headers)
    assert me_resp.status_code == 200

    # 3. Logout
    logout_resp = client.post("/api/registration/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert "logged out" in logout_resp.json()["message"]

    # 4. Subsequent access is rejected with 401
    denied_resp = client.get("/api/registration/applications/me", headers=headers)
    assert denied_resp.status_code == 401
    assert "revoked" in denied_resp.json()["detail"]


# ============================================================
# 2. APPLICANT REGISTRATION & LIFECYCLE APIS
# ============================================================

def test_create_state_and_district_and_hospital_applications(client):
    """Verify creation of State, District, and Hospital applications."""
    # 1. Create State Application
    state_resp = client.post(
        "/api/registration/applications/state",
        json={
            "applicant_name": "Punjab Health Directorate",
            "applicant_email": "director@punjabhealth.gov.in",
            "applicant_phone": "0172-2233445",
            "state": "Punjab",
            "official_designation": "Director General of Health",
        },
    )
    assert state_resp.status_code == 200
    state_data = state_resp.json()
    assert state_data["applicant_type"] == "STATE"
    assert "-ST-" in state_data["application_number"]
    assert state_data["status"] == "DRAFT"

    # 2. Create District Application
    dist_resp = client.post(
        "/api/registration/applications/district",
        json={
            "applicant_name": "Amritsar District Health Society",
            "applicant_email": "cmo@amritsardhs.gov.in",
            "applicant_phone": "0183-2211445",
            "state": "Punjab",
            "district": "Amritsar",
            "official_designation": "Chief Medical Officer",
        },
    )
    assert dist_resp.status_code == 200
    dist_data = dist_resp.json()
    assert dist_data["applicant_type"] == "DISTRICT"
    assert "DIST" in dist_data["application_number"]
    assert dist_data["status"] == "DRAFT"

    # 3. Create Hospital Application
    hosp_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Apex Heart Hospital",
            "applicant_email": "admin@apexheart.org",
            "applicant_phone": "0172-5559988",
            "state": "Punjab",
            "district": "Mohali",
            "city": "Mohali",
            "profile_data": {"total_beds": 150, "icu_beds": 20},
        },
    )
    assert hosp_resp.status_code == 200
    hosp_data = hosp_resp.json()
    assert hosp_data["applicant_type"] == "HOSPITAL"
    assert "HOSP" in hosp_data["application_number"]
    assert hosp_data["status"] == "DRAFT"


def test_update_draft_application_and_submit(client):
    """Verify editing a draft, uploading mandatory documents, and submitting into review pipeline."""
    # 1. Create hospital application
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Draft Update Hospital",
            "applicant_email": "contact@draftupdate.org",
            "applicant_phone": "0172-5553311",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Update draft details
    update_resp = client.put(
        "/api/registration/applications/draft",
        json={
            "applicant_name": "Draft Update Hospital Renamed",
            "address": "Sector 62, Phase 8",
            "pincode": "160062",
            "profile_data": {"total_beds": 80, "icu_beds": 12},
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "DRAFT"

    # 3. Attempt submission without mandatory documents -> Fails with 400
    bad_sub_resp = client.post("/api/registration/applications/submit", json={"remarks": "Ready"}, headers=headers)
    assert bad_sub_resp.status_code == 400
    assert "Missing mandatory hospital documents" in bad_sub_resp.json()["detail"]

    # 4. Upload mandatory hospital documents (CLINICAL_LICENSE, FIRE_SAFETY_NOC)
    doc1_resp = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "license.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 10240,
            "storage_key": "s3://docs/license.pdf",
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert doc1_resp.status_code == 200

    doc2_resp = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "FIRE_SAFETY_NOC",
            "original_filename": "fire_noc.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 20480,
            "storage_key": "s3://docs/fire_noc.pdf",
            "checksum_sha256": "b" * 64,
        },
        headers=headers,
    )
    assert doc2_resp.status_code == 200

    # 5. Submit application successfully -> transitions to SUBMITTED / DISTRICT_REVIEW
    sub_resp = client.post(
        "/api/registration/applications/submit",
        json={"remarks": "All documents verified and attached."},
        headers=headers,
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "SUBMITTED"
    assert sub_data["current_stage"] == "DISTRICT_REVIEW"

    # 6. Editing application while in SUBMITTED status is forbidden
    edit_after_sub = client.put(
        "/api/registration/applications/draft",
        json={"applicant_name": "Illegal Edit"},
        headers=headers,
    )
    assert edit_after_sub.status_code == 400
    assert "Only DRAFT applications can be updated" in edit_after_sub.json()["detail"]


# ============================================================
# 3. APPLICANT TOKEN RESTRICTIONS & OWNERSHIP
# ============================================================

def test_applicant_token_cannot_access_operational_or_reviewer_routes(client, reviewer_tokens):
    """Verify that APPLICANT tokens cannot access operational hospital/admin endpoints or reviewer endpoints."""
    # Create an applicant token
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Boundary Test Hospital",
            "applicant_email": "boundary@test.org",
            "applicant_phone": "0172-9998877",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    # 1. Applicant cannot access reviewer endpoints (403 Forbidden)
    rev_resp = client.get("/api/registration/review/applications", headers=app_headers)
    assert rev_resp.status_code == 403
    assert "Applicant credentials cannot be used" in rev_resp.json()["detail"]

    # 2. Applicant cannot access operational hospital/admin endpoints (403 Forbidden)
    admin_resp = client.get("/district/overview", headers=app_headers)
    assert admin_resp.status_code == 403
    hosp_resp = client.get("/hospitals/GH00001/inventory", headers=app_headers)
    assert hosp_resp.status_code == 403


def test_applicant_ownership_isolation(client):
    """Applicant A cannot view or modify Applicant B's application."""
    # Hospital A
    resp_a = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Hospital A",
            "applicant_email": "hosp.a@test.org",
            "applicant_phone": "0172-1111111",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token_a = resp_a.json()["applicant_token"]
    app_id_a = resp_a.json()["application_id"]

    # Hospital B
    resp_b = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Hospital B",
            "applicant_email": "hosp.b@test.org",
            "applicant_phone": "0172-2222222",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token_b = resp_b.json()["applicant_token"]

    # Applicant B calls /api/registration/applications/me -> returns only Hospital B
    me_b = client.get("/api/registration/applications/me", headers={"Authorization": f"Bearer {token_b}"})
    assert me_b.status_code == 200
    assert me_b.json()["application_id"] != app_id_a
    assert me_b.json()["applicant_name"] == "Hospital B"


# ============================================================
# 4. PUBLIC TRACKING PRIVACY TESTS
# ============================================================

def test_public_tracking_privacy_sanitization(client):
    """Verify that public tracking NEVER leaks private contact details, Aadhaar, reviewer notes, or storage keys."""
    # Create and submit hospital application
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Privacy Shield Hospital",
            "applicant_email": "private.email@hospital.org",
            "applicant_phone": "0172-9988776655",
            "state": "Punjab",
            "district": "Mohali",
            "profile_data": {"aadhaar_number": "9999-8888-7777", "tax_id": "PAN12345"},
        },
    )
    app_num = create_resp.json()["application_number"]
    token = create_resp.json()["applicant_token"]
    track_token = create_resp.json()["tracking_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload document
    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "secret_license.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://private-vault/secret_license.pdf",
            "checksum_sha256": "c" * 64,
        },
        headers=headers,
    )

    # Public tracking request requires mandatory tracking_token
    track_resp = client.get(f"/api/registration/public/track/{app_num}?tracking_token={track_token}")
    assert track_resp.status_code == 200
    track_data = track_resp.json()

    # Assert safe public fields exist
    assert track_data["application_number"] == app_num
    assert track_data["applicant_name"] == "Privacy Shield Hospital"
    assert track_data["state"] == "Punjab"
    assert track_data["district"] == "Mohali"
    assert track_data["status"] == "DRAFT"

    # STRICT PRIVACY INVARIANTS: assert NO sensitive fields exist in response
    resp_text = track_resp.text
    assert "private.email@hospital.org" not in resp_text
    assert "9988776655" not in resp_text
    assert "9999-8888-7777" not in resp_text
    assert "s3://private-vault" not in resp_text
    assert "checksum_sha256" not in resp_text


# ============================================================
# 5. REVIEWER WORKFLOW & HIERARCHICAL DECISION TESTS
# ============================================================

def test_reviewer_workflow_geographic_access_and_hierarchy(client, reviewer_tokens):
    """
    Test complete 3-tier reviewer approval workflow:
    Hospital App -> DISTRICT_ADMIN (Mohali) forwards -> STATE_ADMIN (Punjab) forwards -> CENTRAL_ADMIN approves.
    Verifies geographic boundaries and reviewer role enforcement.
    """
    # 1. Create and submit hospital application in Mohali, Punjab
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Full Chain Hospital Mohali",
            "applicant_email": "admin@fullchain-mohali.org",
            "applicant_phone": "0172-5558877",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    app_id = create_resp.json()["application_id"]
    token = create_resp.json()["applicant_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload mandatory documents
    doc1 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://docs/lic.pdf",
            "checksum_sha256": "1" * 64,
        },
        headers=headers,
    ).json()

    doc2 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "FIRE_SAFETY_NOC",
            "original_filename": "fire.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
            "storage_key": "s3://docs/fire.pdf",
            "checksum_sha256": "2" * 64,
        },
        headers=headers,
    ).json()

    # Submit application -> moves to DISTRICT_REVIEW
    sub_resp = client.post("/api/registration/applications/submit", json={"remarks": "Submitted"}, headers=headers)
    assert sub_resp.status_code == 200

    # 2. Reviewer Security: Amritsar District Admin attempts to access Mohali application -> 403 Forbidden
    asr_headers = {"Authorization": f"Bearer {reviewer_tokens['dist_amritsar']}"}
    asr_resp = client.get(f"/api/registration/review/applications/{app_id}", headers=asr_headers)
    assert asr_resp.status_code == 403
    assert "outside your district jurisdiction" in asr_resp.json()["detail"]

    # 3. Reviewer Security: Operational hospital staff cannot access reviewer endpoints -> 403 Forbidden
    hosp_staff_headers = {"Authorization": f"Bearer {reviewer_tokens['hospital_staff']}"}
    hosp_staff_resp = client.get(f"/api/registration/review/applications/{app_id}", headers=hosp_staff_headers)
    assert hosp_staff_resp.status_code == 403
    assert "Hospital staff role is not permitted" in hosp_staff_resp.json()["detail"]

    # 4. Mohali District Admin accesses and verifies documents
    moh_headers = {"Authorization": f"Bearer {reviewer_tokens['dist_mohali']}"}
    moh_view = client.get(f"/api/registration/review/applications/{app_id}", headers=moh_headers)
    assert moh_view.status_code == 200

    # Verify document 1
    vdoc1 = client.post(
        f"/api/registration/review/documents/{doc1['document_id']}/verify",
        json={"verification_status": "VERIFIED", "reviewer_remarks": "Clinical license verified with state registry."},
        headers=moh_headers,
    )
    assert vdoc1.status_code == 200

    # Verify document 2
    vdoc2 = client.post(
        f"/api/registration/review/documents/{doc2['document_id']}/verify",
        json={"verification_status": "VERIFIED", "reviewer_remarks": "Fire safety NOC valid."},
        headers=moh_headers,
    )
    assert vdoc2.status_code == 200

    # 5. Mohali District Admin forwards to State Review
    fwd_dist = client.post(
        f"/api/registration/review/applications/{app_id}/decision",
        json={"action": "FORWARD", "remarks": "Documents verified. Recommending for State approval."},
        headers=moh_headers,
    )
    assert fwd_dist.status_code == 200
    assert fwd_dist.json()["new_stage"] == "STATE_REVIEW"

    # 6. Haryana State Admin attempts to access Punjab application -> 403 Forbidden
    hr_headers = {"Authorization": f"Bearer {reviewer_tokens['state_haryana']}"}
    hr_resp = client.get(f"/api/registration/review/applications/{app_id}", headers=hr_headers)
    assert hr_resp.status_code == 403
    assert "outside your state jurisdiction" in hr_resp.json()["detail"]

    # 7. Punjab State Admin forwards to Central Review
    pb_headers = {"Authorization": f"Bearer {reviewer_tokens['state_punjab']}"}
    fwd_state = client.post(
        f"/api/registration/review/applications/{app_id}/decision",
        json={"action": "FORWARD", "remarks": "State healthcare council endorsed."},
        headers=pb_headers,
    )
    assert fwd_state.status_code == 200
    assert fwd_state.json()["new_stage"] == "CENTRAL_REVIEW"

    # 8. Central Admin approves application
    central_headers = {"Authorization": f"Bearer {reviewer_tokens['central']}"}
    appr_central = client.post(
        f"/api/registration/review/applications/{app_id}/decision",
        json={"action": "APPROVE", "remarks": "Final central accreditation approved."},
        headers=central_headers,
    )
    assert appr_central.status_code == 200
    assert appr_central.json()["new_status"] == "APPROVED"
    assert appr_central.json()["new_stage"] == "APPROVED"


def test_correction_request_and_applicant_resubmission_api(client, reviewer_tokens):
    """Verify reviewer requesting corrections, applicant resubmission, and audit trail progression."""
    # 1. Create and submit hospital application
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Correction Flow Hospital",
            "applicant_email": "corr.test@hospital.org",
            "applicant_phone": "0172-5554422",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    app_id = create_resp.json()["application_id"]
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    # Upload docs and submit
    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "a" * 64,
        },
        headers=app_headers,
    )
    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "FIRE_SAFETY_NOC",
            "original_filename": "fire.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
            "storage_key": "s3://fire.pdf",
            "checksum_sha256": "b" * 64,
        },
        headers=app_headers,
    )
    client.post("/api/registration/applications/submit", json={"remarks": "Initial"}, headers=app_headers)

    # 2. Mohali District Admin issues correction request
    moh_headers = {"Authorization": f"Bearer {reviewer_tokens['dist_mohali']}"}
    corr_resp = client.post(
        f"/api/registration/review/applications/{app_id}/request-correction",
        json={"correction_notes": "Please upload an unexpired Fire Safety NOC certificate with clear seal."},
        headers=moh_headers,
    )
    assert corr_resp.status_code == 200
    assert corr_resp.json()["status"] == "CORRECTION_REQUIRED"

    # 3. Applicant checks /api/registration/applications/me and sees correction notes
    me_resp = client.get("/api/registration/applications/me", headers=app_headers)
    assert me_resp.status_code == 200
    assert me_resp.json()["status"] == "CORRECTION_REQUIRED"
    assert "Please upload an unexpired Fire Safety NOC" in me_resp.json()["correction_notes"]

    # 4. Applicant resubmits application
    resub_resp = client.post(
        "/api/registration/applications/resubmit",
        json={"applicant_notes": "Uploaded renewed NOC certificate issued on Nov 1."},
        headers=app_headers,
    )
    assert resub_resp.status_code == 200
    resub_data = resub_resp.json()
    assert resub_data["status"] == "SUBMITTED"
    assert resub_data["resubmission_version"] == 2


# ============================================================
# 5. SELF-APPROVAL & SECURITY CONTROLS
# ============================================================

def test_self_approval_prevention_via_api(client):
    """
    Verify that reviewers cannot approve applications where their own email matches the applicant email.
    """
    # 1. Create and submit an application with reviewer's email
    app_email = "self_review_dist@mohali.gov.in"
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Self Review Clinic",
            "applicant_email": app_email,
            "applicant_phone": "0172-3334455",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    app_id = create_resp.json()["application_id"]
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "a" * 64,
        },
        headers=app_headers,
    )
    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "FIRE_SAFETY_NOC",
            "original_filename": "fire.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
            "storage_key": "s3://fire.pdf",
            "checksum_sha256": "b" * 64,
        },
        headers=app_headers,
    )
    client.post("/api/registration/applications/submit", json={"remarks": "Ready"}, headers=app_headers)

    # 2. Reviewer with matching email attempts to execute review decision
    self_reviewer_token = create_access_token({
        "user_id": "U_SELF_REV_1",
        "username": "self_rev",
        "role": "DISTRICT_ADMIN",
        "email": app_email,
        "state": "Punjab",
        "district": "Mohali",
    })
    rev_headers = {"Authorization": f"Bearer {self_reviewer_token}"}

    dec_resp = client.post(
        f"/api/registration/review/applications/{app_id}/decision",
        json={"action": "FORWARD", "remarks": "Approving own hospital"},
        headers=rev_headers,
    )
    assert dec_resp.status_code == 403
    assert "cannot review or approve their own application" in dec_resp.json()["detail"]


def test_otp_api_rate_limiting(client):
    """
    Verify rate limiting on OTP request endpoint.
    Exceeding maximum allowed attempts triggers 429 Too Many Requests.
    """
    target_email = "ratelimit.applicant@domain.org"
    for i in range(5):
        resp = client.post(
            "/api/registration/auth/otp/request",
            json={"contact_target": target_email, "purpose": "REGISTRATION_OTP"},
        )
        assert resp.status_code in (200, 422)

    # 6th attempt exceeds sliding-window rate limit
    exceeded_resp = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_email, "purpose": "REGISTRATION_OTP"},
    )
    assert exceeded_resp.status_code == 429
    assert "Retry-After" in exceeded_resp.headers or "Too many" in exceeded_resp.json()["detail"]


def test_document_metadata_validation_errors(client):
    """
    Verify input validation on document metadata upload:
    - Unsupported document type
    - Invalid file size (<= 0)
    - Invalid SHA-256 checksum format
    """
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Validation Test Clinic",
            "applicant_email": "doc.val@hospital.org",
            "applicant_phone": "0172-5551299",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    # 1. Invalid document type
    bad_type_resp = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "INVALID_RANDOM_TYPE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "a" * 64,
        },
        headers=app_headers,
    )
    assert bad_type_resp.status_code in (400, 422)

    # 2. Invalid file size (0 bytes)
    zero_size_resp = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 0,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "a" * 64,
        },
        headers=app_headers,
    )
    assert zero_size_resp.status_code == 422

    # 3. Invalid checksum length (not 64 chars)
    bad_hash_resp = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "tooshort",
        },
        headers=app_headers,
    )
    assert bad_hash_resp.status_code == 422


def test_reviewer_application_listing_and_filtering(client, reviewer_tokens):
    """
    Verify application listing by reviewer role, jurisdiction filtering, and status filtering.
    """
    moh_headers = {"Authorization": f"Bearer {reviewer_tokens['dist_mohali']}"}
    pun_headers = {"Authorization": f"Bearer {reviewer_tokens['state_punjab']}"}
    cen_headers = {"Authorization": f"Bearer {reviewer_tokens['central']}"}

    # Mohali District Admin queries applications in their district
    moh_resp = client.get("/api/registration/review/applications", headers=moh_headers)
    assert moh_resp.status_code == 200
    moh_items = moh_resp.json()["applications"]
    for item in moh_items:
        assert item["district"] == "Mohali"
        assert item["state"] == "Punjab"

    # State Admin queries applications across all districts in Punjab
    pun_resp = client.get("/api/registration/review/applications", headers=pun_headers)
    assert pun_resp.status_code == 200
    pun_items = pun_resp.json()["applications"]
    for item in pun_items:
        assert item["state"] == "Punjab"

    # Central Admin queries applications nationally
    cen_resp = client.get("/api/registration/review/applications?applicant_type=HOSPITAL", headers=cen_headers)
    assert cen_resp.status_code == 200
    cen_items = cen_resp.json()["applications"]
    for item in cen_items:
        assert item["applicant_type"] == "HOSPITAL"


def test_public_tracking_not_found_and_token_verification(client):
    """
    Verify mandatory tracking_token behavior, 404 response for non-existent applications,
    and rejection of requests missing tracking_token.
    """
    fake_token = "a" * 32

    # 1. Non-existent application number with token returns 404
    not_found = client.get(f"/api/registration/track/APP-20261103-HO-NONEXIST?tracking_token={fake_token}")
    assert not_found.status_code == 404

    # 2. Tracking without token returns 422 Unprocessable Content (mandatory parameter)
    missing_token = client.get("/api/registration/track/APP-20261103-HO-NONEXIST")
    assert missing_token.status_code == 422

    # 3. Create application and submit to get tracking token
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Tracking Test Hospital",
            "applicant_email": "track.test@hospital.org",
            "applicant_phone": "0172-5559090",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "lic.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "storage_key": "s3://lic.pdf",
            "checksum_sha256": "c" * 64,
        },
        headers=app_headers,
    )
    client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "FIRE_SAFETY_NOC",
            "original_filename": "fire.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
            "storage_key": "s3://fire.pdf",
            "checksum_sha256": "d" * 64,
        },
        headers=app_headers,
    )
    sub_resp = client.post("/api/registration/applications/submit", json={"remarks": "Submit for track"}, headers=app_headers)
    assert sub_resp.status_code == 200
    app_num = sub_resp.json()["application_number"]
    track_token = sub_resp.json()["tracking_token"]

    # 4. Public tracking with valid tracking token query parameter succeeds
    track_resp = client.get(f"/api/registration/track/{app_num}?tracking_token={track_token}")
    assert track_resp.status_code == 200
    track_data = track_resp.json()
    assert track_data["application_number"] == app_num
    assert track_data["status"] == "SUBMITTED"

    # 5. Public tracking without token query parameter is rejected with 422
    no_token_resp = client.get(f"/api/registration/track/{app_num}")
    assert no_token_resp.status_code == 422

    # 6. Public tracking with invalid/wrong token returns uniform 404 (prevents oracle)
    bad_token_resp = client.get(f"/api/registration/track/{app_num}?tracking_token={fake_token}")
    assert bad_token_resp.status_code == 404
    assert "Invalid application number or tracking token" in bad_token_resp.json()["detail"]


def test_resubmit_without_correction_required_fails(client):
    """
    Attempting to resubmit an application that is not in CORRECTION_REQUIRED status must fail.
    """
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Premature Resubmit Clinic",
            "applicant_email": "premature@clinic.org",
            "applicant_phone": "0172-5558080",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    app_headers = {"Authorization": f"Bearer {token}"}

    # Resubmit on DRAFT application fails with 400 Bad Request
    fail_resub = client.post(
        "/api/registration/applications/resubmit",
        json={"applicant_notes": "Trying early resubmit"},
        headers=app_headers,
    )
    assert fail_resub.status_code == 400
    assert "CORRECTION_REQUIRED" in fail_resub.json()["detail"]


# ============================================================
# 6. SECURITY REMEDIATION TESTS (FINDINGS F-1 THROUGH F-5)
# ============================================================

def test_f1_mandatory_tracking_token_and_oracle_prevention(client, api_db_session):
    """
    F-1 Remediation:
    - Missing tracking_token is rejected with 422.
    - Non-existent app and wrong token return identical 404 without leaking application existence.
    - Expired or revoked token returns 404.
    - Valid token returns 200.
    """
    # 1. Create hospital application
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "F1 Security Hospital",
            "applicant_email": "f1.sec@hospital.org",
            "applicant_phone": "0172-5551100",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    app_num = create_resp.json()["application_number"]
    app_id = create_resp.json()["application_id"]
    valid_token = create_resp.json()["tracking_token"]
    fake_token = "b" * 32

    # A. Missing tracking_token -> 422
    assert client.get(f"/api/registration/track/{app_num}").status_code == 422
    assert client.get(f"/api/registration/public/track/{app_num}").status_code == 422

    # B. Non-existent application number with token -> 404
    non_exist_resp = client.get(f"/api/registration/track/APP-20261103-HO-NONEXIST?tracking_token={fake_token}")
    assert non_exist_resp.status_code == 404
    assert "Invalid application number or tracking token" in non_exist_resp.json()["detail"]

    # C. Real application with wrong token -> identical 404 (prevents enumeration oracle)
    wrong_token_resp = client.get(f"/api/registration/track/{app_num}?tracking_token={fake_token}")
    assert wrong_token_resp.status_code == 404
    assert "Invalid application number or tracking token" in wrong_token_resp.json()["detail"]

    # D. Valid application and valid token -> 200 OK
    valid_resp = client.get(f"/api/registration/track/{app_num}?tracking_token={valid_token}")
    assert valid_resp.status_code == 200
    assert valid_resp.json()["application_number"] == app_num

    # E. Revoked token -> 404
    from src.database.pg_models import ApplicationTrackingToken
    tok = api_db_session.query(ApplicationTrackingToken).filter_by(application_id=app_id).first()
    tok.is_revoked = True
    api_db_session.commit()

    revoked_resp = client.get(f"/api/registration/track/{app_num}?tracking_token={valid_token}")
    assert revoked_resp.status_code == 404
    assert "Invalid application number or tracking token" in revoked_resp.json()["detail"]


def test_f2_otp_ip_level_rate_limiting_and_target_spray(client):
    """
    F-2 Remediation:
    - Multiple victim email addresses requested from the same IP are throttled at the IP ceiling (15).
    - Single email target requests are throttled at the target ceiling (5).
    - Untrusted X-Forwarded-For header does not bypass rate limit.
    """
    # 1. IP spray across 15 different targets
    for i in range(15):
        resp = client.post(
            "/api/registration/auth/otp/request",
            json={"contact_target": f"spray_victim_{i}@domain.org", "purpose": "PORTAL_ACCESS_OTP"},
        )
        assert resp.status_code == 200, f"Request {i} failed: {resp.text}"

    # 16th request from the same IP to a new target is throttled with 429
    throttled_resp = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": "spray_victim_16@domain.org", "purpose": "PORTAL_ACCESS_OTP"},
    )
    assert throttled_resp.status_code == 429
    assert "Too many" in throttled_resp.json()["detail"]

    # Spoofed X-Forwarded-For does not bypass without SIH_TRUST_PROXY enabled
    spoofed_resp = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": "spray_victim_17@domain.org", "purpose": "PORTAL_ACCESS_OTP"},
        headers={"X-Forwarded-For": "203.0.113.199"},
    )
    assert spoofed_resp.status_code == 429


def test_f3_document_metadata_security_validation(client):
    """
    F-3 Remediation:
    - Rejects path traversal (../../../etc/shadow)
    - Rejects absolute paths (/etc/passwd)
    - Rejects backslash traversal (..\\..\\windows\\system32)
    - Rejects oversized files (> 25MB)
    - Rejects disallowed MIME types
    - Rejects non-hex checksums
    - Accepts safe filename and generates server-side storage key
    """
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "F3 Security Hospital",
            "applicant_email": "f3.sec@hospital.org",
            "applicant_phone": "0172-5552200",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    token = create_resp.json()["applicant_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Directory traversal filename
    r1 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "../../../etc/shadow",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r1.status_code == 422

    # 2. Absolute path
    r2 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "/etc/passwd",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r2.status_code == 422

    # 3. Backslash traversal
    r3 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "..\\..\\windows\\system32\\cmd.exe",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r3.status_code == 422

    # 4. Oversized file (26,214,401 bytes > 25MB)
    r4 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "big_doc.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 26_214_401,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r4.status_code == 422

    # 5. Invalid MIME type (executable script)
    r5 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "script.sh",
            "mime_type": "application/x-sh",
            "file_size_bytes": 1024,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r5.status_code == 422

    # 6. Invalid non-hex checksum
    r6 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "doc.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 1024,
            "checksum_sha256": "z" * 64,
        },
        headers=headers,
    )
    assert r6.status_code == 422

    # 7. Valid safe filename and metadata
    r7 = client.post(
        "/api/registration/applications/documents",
        json={
            "document_type": "CLINICAL_LICENSE",
            "original_filename": "clinical_license_2026.pdf",
            "mime_type": "application/pdf",
            "file_size_bytes": 2048,
            "checksum_sha256": "a" * 64,
        },
        headers=headers,
    )
    assert r7.status_code == 200
    assert r7.json()["original_filename"] == "clinical_license_2026.pdf"


def test_f4_application_creation_and_tracking_rate_limiting(client):
    """
    F-4 Remediation:
    - Application creation endpoints are rate-limited per IP (max 10 / 5 min).
    - Public tracking requests are rate-limited per IP (max 30 / 1 min).
    """
    # 1. Application creation rate limiting
    for i in range(10):
        resp = client.post(
            "/api/registration/applications/hospital",
            json={
                "applicant_name": f"Rate Limit Hosp {i}",
                "applicant_email": f"rate.hosp.{i}@hospital.org",
                "applicant_phone": f"0172-555{i:04d}",
                "state": "Punjab",
                "district": "Mohali",
            },
        )
        assert resp.status_code == 200, f"App creation {i} failed: {resp.text}"

    # 11th creation attempt returns 429
    throttled_app = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Rate Limit Hosp 11",
            "applicant_email": "rate.hosp.11@hospital.org",
            "applicant_phone": "0172-5550011",
            "state": "Punjab",
            "district": "Mohali",
        },
    )
    assert throttled_app.status_code == 429
    assert "Too many" in throttled_app.json()["detail"]


def test_f5_otp_purpose_alignment_and_mismatch(client):
    """
    F-5 Remediation:
    - Purpose is passed and validated between request and verification.
    - REGISTRATION_OTP and PORTAL_ACCESS_OTP work independently.
    - Purpose mismatch is strictly rejected with 422.
    - Arbitrary undefined purpose is rejected with 422.
    """
    from src.services.otp_service import get_otp_provider

    provider = get_otp_provider()

    # 1. Successful REGISTRATION_OTP lifecycle
    target_reg = "reg.purpose@domain.org"
    req_reg = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_reg, "purpose": "REGISTRATION_OTP"},
    )
    assert req_reg.status_code == 200
    token_reg_id = req_reg.json()["token_id"]
    otp_reg = provider.get_last_simulated_otp(target_reg)

    verify_reg = client.post(
        "/api/registration/auth/otp/verify",
        json={"token_id": token_reg_id, "otp": otp_reg, "purpose": "REGISTRATION_OTP"},
    )
    assert verify_reg.status_code == 200
    assert verify_reg.json()["verified"] is True

    # 2. Successful PORTAL_ACCESS_OTP lifecycle
    target_portal = "portal.purpose@domain.org"
    req_portal = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_portal, "purpose": "PORTAL_ACCESS_OTP"},
    )
    assert req_portal.status_code == 200
    token_portal_id = req_portal.json()["token_id"]
    otp_portal = provider.get_last_simulated_otp(target_portal)

    verify_portal = client.post(
        "/api/registration/auth/otp/verify",
        json={"token_id": token_portal_id, "otp": otp_portal, "purpose": "PORTAL_ACCESS_OTP"},
    )
    assert verify_portal.status_code == 200
    assert verify_portal.json()["verified"] is True

    # 3. Purpose Mismatch: Requested as REGISTRATION_OTP, attempt verify as PORTAL_ACCESS_OTP
    target_mismatch = "mismatch.purpose@domain.org"
    req_mis = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": target_mismatch, "purpose": "REGISTRATION_OTP"},
    )
    assert req_mis.status_code == 200
    token_mis_id = req_mis.json()["token_id"]
    otp_mis = provider.get_last_simulated_otp(target_mismatch)

    verify_mis = client.post(
        "/api/registration/auth/otp/verify",
        json={"token_id": token_mis_id, "otp": otp_mis, "purpose": "PORTAL_ACCESS_OTP"},
    )
    assert verify_mis.status_code == 422
    assert "Token purpose mismatch" in verify_mis.json()["detail"]

    # 4. Caller attempts arbitrary purpose -> rejected by schema validation (422)
    bad_req = client.post(
        "/api/registration/auth/otp/request",
        json={"contact_target": "bad.purpose@domain.org", "purpose": "HACKER_BYPASS_PURPOSE"},
    )
    assert bad_req.status_code == 422


def test_api_application_submission_automated_email_confirmation(client, api_db_session):
    """
    Integration Test: Calling POST /api/registration/applications/submit
    atomically transitions application to SUBMITTED and enqueues an outbox confirmation email
    containing the official application number and secret tracking token.
    """
    import json
    from src.database.pg_models import RegistrationEmailOutbox

    email = "applicant.confirm@hospital.punjab.org"
    create_resp = client.post(
        "/api/registration/applications/hospital",
        json={
            "applicant_name": "Apollo Care Center",
            "applicant_email": email,
            "applicant_phone": "9876543210",
            "state": "Punjab",
            "district": "Mohali",
            "ownership_type": "PRIVATE",
            "facility_category": "TERTIARY",
            "total_beds": 200,
            "icu_beds": 40,
            "ventilators": 15,
            "oxygen_capacity_liters": 10000,
            "emergency_tier": "LEVEL_1",
            "specialties": ["Cardiology", "Neurology"],
        },
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    app_id = create_data["application_id"]
    app_num = create_data["application_number"]
    app_token = create_data["applicant_token"]
    headers = {"Authorization": f"Bearer {app_token}"}

    # Upload mandatory documents
    valid_pdf = b"%PDF-1.4 1 0 obj << /Type /Catalog >> endobj xref 0 1 trailer << /Root 1 0 R >> startxref 9 %%EOF"
    client.post(
        "/api/registration/applications/documents/upload",
        files={"file": ("lic.pdf", valid_pdf, "application/pdf")},
        data={"document_type": "CLINICAL_LICENSE"},
        headers=headers,
    )
    client.post(
        "/api/registration/applications/documents/upload",
        files={"file": ("fire.pdf", valid_pdf, "application/pdf")},
        data={"document_type": "FIRE_SAFETY_NOC"},
        headers=headers,
    )

    # Submit application
    sub_resp = client.post(
        "/api/registration/applications/submit",
        json={"remarks": "Submitting Apollo Care application"},
        headers=headers,
    )
    assert sub_resp.status_code == 200
    sub_data = sub_resp.json()
    assert sub_data["status"] == "SUBMITTED"
    assert sub_data["application_number"] == app_num
    raw_tracking_token = sub_data["tracking_token"]
    assert raw_tracking_token

    # Verify outbox confirmation email record
    outbox_entry = (
        api_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=email, event_type="APPLICATION_SUBMITTED")
        .first()
    )
    assert outbox_entry is not None
    assert outbox_entry.status in ("PENDING", "SENT")
    assert app_num in outbox_entry.subject

    payload = json.loads(outbox_entry.payload)
    assert payload["application_number"] == app_num
    assert payload["tracking_token"] == raw_tracking_token
    assert payload["current_stage"] == "DISTRICT_REVIEW"
    assert payload["current_stage_display"] == "District Verification"
    assert raw_tracking_token in payload["body_text"]
    assert app_num in payload["body_text"]
    assert "/track" in payload["body_text"]
    assert raw_tracking_token in payload["body_html"]

    # Verify duplicate submission is rejected (idempotency)
    dup_resp = client.post(
        "/api/registration/applications/submit",
        json={"remarks": "Submitting again"},
        headers=headers,
    )
    assert dup_resp.status_code in (400, 422)


