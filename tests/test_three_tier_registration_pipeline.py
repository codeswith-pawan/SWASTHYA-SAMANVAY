"""
End-to-End Integration Tests for 3-Tier Registration Review Pipeline (District -> State -> Central),
Geographic Jurisdiction Isolation, Document Verification, and Live Activation Link Workflow.
SWASTHYA SAMANVAY — AI-Powered Smart Hospital Referral System
"""

import json
import secrets
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.db_manager import get_session_factory
from src.database.init_db import init_database
from src.database.pg_models import (
    RegistrationApplication,
    RegistrationDocument,
    RegistrationEmailOutbox,
    AccountActivationToken,
    User,
    Hospital,
)

VALID_PDF_BYTES = b"%PDF-1.4 \n%\xe2\xe3\xcf\xd3\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\nxref\n0 2\ntrailer<</Size 2/Root 1 0 R>>\nstartxref\n99\n%%EOF"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xd9"


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Ensure database schema and baseline reference data are initialized."""
    init_database()


def _login(client: TestClient, username: str, password: str) -> str:
    """Helper to authenticate and return JWT Bearer token."""
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["access_token"]


def test_complete_three_tier_registration_review_and_activation_pipeline(monkeypatch):
    """
    Test complete lifecycle:
    1. Hospital registers in Bihar / Purnea -> uploads docs -> submits (DISTRICT_REVIEW).
    2. Purnea District Reviewer sees application, verifies docs, and forwards (STATE_REVIEW).
       - Other district reviewers (e.g., Amritsar) cannot see or access it.
    3. Bihar State Reviewer sees application and forwards (CENTRAL_REVIEW).
       - Other state reviewers (e.g., Punjab) cannot see or access it (403).
    4. Central Reviewer sees application and grants final APPROVE.
    5. Operational account is provisioned with live activation link pointing to
       https://swasthya-samanvay-ujxm.vercel.app/activate?token=...
    6. Hospital activates account with new password and successfully logs in.
    """
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("PORTAL_BASE_URL", raising=False)
    test_email = f"sunrise.purnea.{secrets.token_hex(4)}@swasthya.gov.in"
    with TestClient(app) as client:
        # ---------------------------------------------------------
        # 1. Hospital Facility Registration & Submission
        # ---------------------------------------------------------
        create_res = client.post(
            "/api/registration/applications/hospital",
            json={
                "applicant_name": "Purnea Sunrise Specialty Hospital",
                "state": "Bihar",
                "district": "Purnea",
                "city": "Purnea",
                "address": "Line Bazar, Medical Zone, Purnea",
                "pincode": "854301",
                "nodal_officer_name": "Dr. Anand Sen",
                "official_designation": "Medical Superintendent",
                "applicant_email": test_email,
                "applicant_phone": "9876500001",
                "profile_data": {
                    "total_beds": 120,
                    "icu_beds": 25,
                    "emergency_beds": 15,
                    "ventilator_count": 10,
                    "emergency_24x7": True,
                    "latitude": 25.7785,
                    "longitude": 87.4760,
                },
            },
        )
        assert create_res.status_code == 200, create_res.text
        create_data = create_res.json()
        applicant_token = create_data["applicant_token"]
        app_id = create_data["application_id"]
        app_number = create_data["application_number"]
        app_headers = {"Authorization": f"Bearer {applicant_token}"}

        # Upload mandatory compliance documents: CLINICAL_LICENSE and FIRE_SAFETY_NOC
        upload_lic = client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "CLINICAL_LICENSE"},
            files={"file": ("clinical_license.pdf", VALID_PDF_BYTES, "application/pdf")},
            headers=app_headers,
        )
        assert upload_lic.status_code == 200, upload_lic.text
        lic_doc_id = upload_lic.json()["document_id"]

        upload_fire = client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "FIRE_SAFETY_NOC"},
            files={"file": ("fire_noc.jpg", VALID_JPEG_BYTES, "image/jpeg")},
            headers=app_headers,
        )
        assert upload_fire.status_code == 200, upload_fire.text
        fire_doc_id = upload_fire.json()["document_id"]

        # Final Submit Application
        submit_res = client.post(
            "/api/registration/applications/submit",
            json={"remarks": "Ready for district authority review."},
            headers=app_headers,
        )
        assert submit_res.status_code == 200, submit_res.text
        submit_data = submit_res.json()
        assert submit_data["status"] == "SUBMITTED"
        assert submit_data["current_stage"] == "DISTRICT_REVIEW"

        # ---------------------------------------------------------
        # 2. Tier 1: District Review (Purnea, Bihar)
        # ---------------------------------------------------------
        purnea_token = _login(client, "district.purnea@swasthya.gov.in", "DistPurnea@2026")
        purnea_headers = {"Authorization": f"Bearer {purnea_token}"}

        # Check queue visibility via both endpoints
        res_purnea_queue = client.get("/api/registration/applications", headers=purnea_headers)
        assert res_purnea_queue.status_code == 200
        purnea_apps = res_purnea_queue.json()["applications"]
        assert any(a["application_id"] == app_id for a in purnea_apps), "App missing in Purnea queue"

        res_purnea_review = client.get("/api/registration/review/applications", headers=purnea_headers)
        assert res_purnea_review.status_code == 200

        # Check Amritsar (Punjab) district reviewer CANNOT see Purnea application
        amritsar_token = _login(client, "district.amritsar@swasthya.gov.in", "DistAmritsar@2026")
        res_asr_queue = client.get("/api/registration/applications", headers={"Authorization": f"Bearer {amritsar_token}"})
        assert res_asr_queue.status_code == 200
        assert not any(a["application_id"] == app_id for a in res_asr_queue.json()["applications"])

        # Fetch detail as Purnea reviewer
        detail_res = client.get(f"/api/registration/applications/{app_id}", headers=purnea_headers)
        assert detail_res.status_code == 200
        assert detail_res.json()["current_stage"] == "DISTRICT_REVIEW"

        # Verify documents
        v1 = client.post(
            f"/api/registration/review/documents/{lic_doc_id}/verify",
            json={"verification_status": "VERIFIED", "reviewer_remarks": "Clinical registration verified with state register."},
            headers=purnea_headers,
        )
        assert v1.status_code == 200

        v2 = client.post(
            f"/api/registration/documents/{fire_doc_id}/verify",
            json={"verification_status": "VERIFIED", "reviewer_remarks": "Fire safety clearance verified."},
            headers=purnea_headers,
        )
        assert v2.status_code == 200

        # Purnea District Reviewer forwards to State Review
        decision_dist = client.post(
            f"/api/registration/applications/{app_id}/decision",
            json={"action": "FORWARD", "remarks": "Purnea District CMO verified facility. Forwarded to State."},
            headers=purnea_headers,
        )
        assert decision_dist.status_code == 200
        assert decision_dist.json()["new_stage"] == "STATE_REVIEW"
        assert decision_dist.json()["new_status"] == "UNDER_REVIEW"

        # ---------------------------------------------------------
        # 3. Tier 2: State Review (Bihar Directorate)
        # ---------------------------------------------------------
        state_bihar_token = _login(client, "state.bihar@swasthya.gov.in", "StateBihar@2026")
        bihar_headers = {"Authorization": f"Bearer {state_bihar_token}"}

        # Verify application appears in Bihar State queue
        res_bihar_queue = client.get("/api/registration/applications", headers=bihar_headers)
        assert res_bihar_queue.status_code == 200
        assert any(a["application_id"] == app_id for a in res_bihar_queue.json()["applications"])

        # Verify Punjab State Reviewer cannot see or access Bihar application
        state_punjab_token = _login(client, "state.punjab@swasthya.gov.in", "StatePunjab@2026")
        res_punjab_queue = client.get("/api/registration/applications", headers={"Authorization": f"Bearer {state_punjab_token}"})
        assert res_punjab_queue.status_code == 200
        assert not any(a["application_id"] == app_id for a in res_punjab_queue.json()["applications"])

        res_punjab_detail = client.get(f"/api/registration/applications/{app_id}", headers={"Authorization": f"Bearer {state_punjab_token}"})
        assert res_punjab_detail.status_code == 403

        # Bihar State Reviewer forwards to Central Review
        decision_state = client.post(
            f"/api/registration/applications/{app_id}/decision",
            json={"action": "FORWARD", "remarks": "Bihar State Health Directorate approved regional network integration."},
            headers=bihar_headers,
        )
        assert decision_state.status_code == 200
        assert decision_state.json()["new_stage"] == "CENTRAL_REVIEW"
        assert decision_state.json()["new_status"] == "UNDER_REVIEW"

        # ---------------------------------------------------------
        # 4. Tier 3: Central Review (National Health Authority)
        # ---------------------------------------------------------
        central_token = _login(client, "central.admin@swasthya.gov.in", "Central@2026")
        central_headers = {"Authorization": f"Bearer {central_token}"}

        # Verify application appears in Central queue
        res_central_queue = client.get("/api/registration/applications", headers=central_headers)
        assert res_central_queue.status_code == 200
        assert any(a["application_id"] == app_id for a in res_central_queue.json()["applications"])

        # Central Reviewer approves application
        decision_central = client.post(
            f"/api/registration/applications/{app_id}/decision",
            json={"action": "APPROVE", "remarks": "Apex national health accreditation granted."},
            headers=central_headers,
        )
        assert decision_central.status_code == 200
        assert decision_central.json()["new_status"] == "APPROVED"
        assert decision_central.json()["new_stage"] == "APPROVED"

        # ---------------------------------------------------------
        # 5. Account Activation & Login
        # ---------------------------------------------------------
        SessionFactory = get_session_factory()
        with SessionFactory() as session:
            # Check Outbox has live activation email
            outbox_row = (
                session.query(RegistrationEmailOutbox)
                .filter_by(recipient_email=test_email, event_type="ACCOUNT_ACTIVATION")
                .order_by(RegistrationEmailOutbox.created_at.desc())
                .first()
            )
            assert outbox_row is not None
            payload_data = json.loads(outbox_row.payload) if isinstance(outbox_row.payload, str) else outbox_row.payload
            assert "https://swasthya-samanvay-ujxm.vercel.app/activate?token=" in payload_data["activation_link"]
            raw_token = payload_data["raw_token"]

        # Activate the hospital account
        act_res = client.post(
            "/api/registration/account/activate",
            json={
                "token": raw_token,
                "password": "NewHospital@2026",
                "confirm_password": "NewHospital@2026",
            },
        )
        assert act_res.status_code == 200, act_res.text

        # Verify hospital can now log in via standard and legacy endpoints
        login_res1 = client.post(
            "/api/auth/login",
            json={"username": test_email, "password": "NewHospital@2026"},
        )
        assert login_res1.status_code == 200, login_res1.text
        assert login_res1.json()["user"]["role"] == "HOSPITAL"
        assert "access_token" in login_res1.json()

        login_res2 = client.post(
            "/login",
            json={"username": test_email, "password": "NewHospital@2026"},
        )
        assert login_res2.status_code == 200, login_res2.text
        assert login_res2.json()["user"]["role"] == "HOSPITAL"
