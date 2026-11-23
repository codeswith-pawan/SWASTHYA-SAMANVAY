"""
Integration Tests for Jurisdiction Isolation, Live Activation Link, Referral Proximity, and Clean Network Seeding.
SWASTHYA SAMANVAY — AI-Powered Smart Hospital Referral System
"""

import json
import secrets
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


@pytest.fixture(autouse=True)
def setup_clean_db():
    """Ensure database schema and baseline reference data are initialized."""
    init_database()


def _login(client: TestClient, username: str, password: str) -> str:
    """Helper to authenticate and return JWT Bearer token."""
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed for {username}: {resp.text}"
    return resp.json()["access_token"]


def test_strict_state_and_district_jurisdiction_isolation():
    """
    Verify that:
    - DISTRICT_ADMIN can only access applications matching their state and district.
    - STATE_ADMIN can only access applications matching their state.
    - Punjab reviewers cannot view, access details, or review Bihar applications.
    """
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        # Create a sample hospital registration application in Purnea, Bihar
        bihar_app = RegistrationApplication(
            application_id="APP_BIHAR_PURNEA_01",
            application_number="APP-BIHAR-2026-001",
            applicant_name="Purnea Community Hospital",
            applicant_email="nodal.purnea.test@swasthya.gov.in",
            applicant_phone="9876543210",
            applicant_type="HOSPITAL",
            state="Bihar",
            district="Purnea",
            current_stage="DISTRICT_REVIEW",
            status="SUBMITTED",
        )
        session.merge(bihar_app)
        session.commit()

    with TestClient(app) as client:
        # Logins
        purnea_token = _login(client, "district.purnea@swasthya.gov.in", "DistPurnea@2026")
        amritsar_token = _login(client, "district.amritsar@swasthya.gov.in", "DistAmritsar@2026")
        bihar_token = _login(client, "state.bihar@swasthya.gov.in", "StateBihar@2026")
        punjab_token = _login(client, "state.punjab@swasthya.gov.in", "StatePunjab@2026")

        # 1. District Queue Listing Scoping
        # Purnea admin should see it
        res_purnea = client.get(
            "/api/registration/review/applications?stage=DISTRICT_REVIEW",
            headers={"Authorization": f"Bearer {purnea_token}"},
        )
        assert res_purnea.status_code == 200
        purnea_app_ids = [a["application_id"] for a in res_purnea.json()["applications"]]
        assert "APP_BIHAR_PURNEA_01" in purnea_app_ids

        # Amritsar admin should NOT see it
        res_amritsar = client.get(
            "/api/registration/review/applications?stage=DISTRICT_REVIEW",
            headers={"Authorization": f"Bearer {amritsar_token}"},
        )
        assert res_amritsar.status_code == 200
        amritsar_app_ids = [a["application_id"] for a in res_amritsar.json()["applications"]]
        assert "APP_BIHAR_PURNEA_01" not in amritsar_app_ids

        # 2. Detail Endpoint Direct Access Control (HTTP 403 Forbidden)
        res_purnea_detail = client.get(
            "/api/registration/review/applications/APP_BIHAR_PURNEA_01",
            headers={"Authorization": f"Bearer {purnea_token}"},
        )
        assert res_purnea_detail.status_code == 200

        res_amritsar_detail = client.get(
            "/api/registration/review/applications/APP_BIHAR_PURNEA_01",
            headers={"Authorization": f"Bearer {amritsar_token}"},
        )
        assert res_amritsar_detail.status_code == 403
        assert "outside your district jurisdiction" in res_amritsar_detail.text

        # Punjab state admin should also be denied (403)
        res_punjab_detail = client.get(
            "/api/registration/review/applications/APP_BIHAR_PURNEA_01",
            headers={"Authorization": f"Bearer {punjab_token}"},
        )
        assert res_punjab_detail.status_code == 403
        assert "outside your state jurisdiction" in res_punjab_detail.text

        # 3. Decision Action Protection (Amritsar reviewer attempts unauthorized FORWARD decision)
        res_illegal_decision = client.post(
            "/api/registration/review/applications/APP_BIHAR_PURNEA_01/decision",
            headers={"Authorization": f"Bearer {amritsar_token}"},
            json={"action": "FORWARD", "remarks": "Unauthorized cross-district attempt"},
        )
        assert res_illegal_decision.status_code in (403, 422)


def test_central_approval_live_activation_link_and_hospital_login(monkeypatch):
    """
    Verify that:
    - Account activation link is constructed using PORTAL_BASE_URL (defaulting to https://swasthya-samanvay-ujxm.vercel.app).
    - Setting password via the token activates the user.
    - The newly activated hospital can immediately authenticate via POST /login and POST /api/auth/login.
    """
    # Simulate Render deployment environment where PORTAL_BASE_URL is not set but defaults to production portal
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.delenv("PORTAL_BASE_URL", raising=False)

    uid = secrets.token_hex(4)
    app_id = f"APP_ACT_{uid}"
    app_num = f"APP-ACT-2026-{uid}"
    email = f"apex.{uid}@swasthya.gov.in"

    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        test_app = RegistrationApplication(
            application_id=app_id,
            application_number=app_num,
            applicant_name="Purnea Test Apex Clinic",
            applicant_email=email,
            applicant_phone="9876543211",
            applicant_type="HOSPITAL",
            state="Bihar",
            district="Purnea",
            current_stage="CENTRAL_REVIEW",
            status="UNDER_REVIEW",
        )
        session.merge(test_app)

        # Attach required verified documents for final Central approval eligibility
        d1 = RegistrationDocument(
            document_id=f"DOC_CLINICAL_{uid}",
            application_id=app_id,
            document_type="CLINICAL_LICENSE",
            original_filename="clinical_license.pdf",
            storage_key=f"docs/clinical_license_{uid}.pdf",
            checksum_sha256="abc123456789",
            file_size_bytes=1024,
            mime_type="application/pdf",
            verification_status="VERIFIED",
        )
        d2 = RegistrationDocument(
            document_id=f"DOC_FIRE_{uid}",
            application_id=app_id,
            document_type="FIRE_SAFETY_NOC",
            original_filename="fire_safety_noc.pdf",
            storage_key=f"docs/fire_safety_noc_{uid}.pdf",
            checksum_sha256="def123456789",
            file_size_bytes=1024,
            mime_type="application/pdf",
            verification_status="VERIFIED",
        )
        session.merge(d1)
        session.merge(d2)
        session.commit()

    with TestClient(app) as client:
        central_token = _login(client, "central.admin@swasthya.gov.in", "Central@2026")

        # Central Admin executes final approval in production mode
        decision_res = client.post(
            f"/api/registration/review/applications/{app_id}/decision",
            headers={"Authorization": f"Bearer {central_token}"},
            json={"action": "APPROVE", "remarks": "Approved by National Health Authority"},
        )
        assert decision_res.status_code == 200, decision_res.text
        data = decision_res.json()
        assert data["new_status"] == "APPROVED"

        # Check the enqueued outbox email
        with SessionFactory() as session:
            outbox_entry = (
                session.query(RegistrationEmailOutbox)
                .filter_by(recipient_email=email, event_type="ACCOUNT_ACTIVATION")
                .order_by(RegistrationEmailOutbox.id.desc())
                .first()
            )
            assert outbox_entry is not None, "ACCOUNT_ACTIVATION email outbox event was not enqueued!"
            payload = json.loads(outbox_entry.payload)
            activation_link = payload["activation_link"]
            raw_token = payload["raw_token"]

            # Verify activation link domain matches live production portal
            assert "https://swasthya-samanvay-ujxm.vercel.app/activate?token=" in activation_link

            # Activate account with secure password
            activate_res = client.post(
                "/api/registration/auth/activate",
                json={
                    "activation_token": raw_token,
                    "password": "Hospital@Secure2026",
                    "confirm_password": "Hospital@Secure2026",
                },
            )
            assert activate_res.status_code == 200, activate_res.text
            act_data = activate_res.json()
            username = act_data["username"]

            # Log in with newly activated credentials via POST /api/auth/login
            login_res1 = client.post(
                "/api/auth/login",
                json={"username": username, "password": "Hospital@Secure2026"},
            )
            assert login_res1.status_code == 200, login_res1.text
            assert login_res1.json()["user"]["role"] == "HOSPITAL"

            # Log in via legacy POST /login
            login_res2 = client.post(
                "/login",
                json={"username": username, "password": "Hospital@Secure2026"},
            )
            assert login_res2.status_code == 200, login_res2.text
            assert login_res2.json()["user"]["role"] == "HOSPITAL"


def test_purnea_referral_search_returns_purnea_nearest_hospitals_first():
    """
    Verify that when a referral search is executed for a patient at a Purnea hospital,
    facilities in the same district (Purnea) with matching capabilities and available beds
    are prioritized first by Haversine distance over distant out-of-district facilities.
    """
    SessionFactory = get_session_factory()
    with SessionFactory() as session:
        # Create a patient and admission visit at Sadar Hospital Purnea (HOSP_PURNEA_01)
        from src.database.pg_models import Patient, HospitalVisit
        p = Patient(
            patient_id="PAT_PURNEA_CARDIO_01",
            name="Ramesh Kumar",
            age=52,
            gender="Male",
            disease="Cardiovascular / Acute Coronary Syndrome",
            priority="Critical",
            icu_required="Yes",
            referral_required="Yes",
            state="Bihar",
            district="Purnea",
            latitude=25.7785,
            longitude=87.4760,
        )
        session.merge(p)
        v = HospitalVisit(
            patient_id="PAT_PURNEA_CARDIO_01",
            hospital_id="HOSP_PURNEA_01",
            status="ACTIVE",
        )
        session.merge(v)
        session.commit()

    with TestClient(app) as client:
        # Originating hospital admin logs in
        hosp_token = _login(client, "purnea.hosp1@swasthya.gov.in", "Hospital@2026")

        # Request hospital recommendations for acute cardiology & ICU bed transfer
        rec_res = client.post(
            "/api/hospital/patients/PAT_PURNEA_CARDIO_01/recommend-hospitals",
            headers={"Authorization": f"Bearer {hosp_token}"},
            json={
                "urgency": "CRITICAL",
                "condition_summary": "Acute STEMI with hemodynamic instability requiring immediate ICU intervention.",
                "required_specialty": "cardiology",
                "required_bed_type": "ICU",
                "transport_requirement": "ALS_AMBULANCE",
                "vitals": {
                    "heart_rate": 115,
                    "systolic_bp": 90,
                    "diastolic_bp": 60,
                    "spo2": 91,
                    "respiratory_rate": 26,
                    "temperature": 98.6,
                },
            },
        )
        assert rec_res.status_code == 200, rec_res.text
        data = rec_res.json()
        hospitals = data["hospitals"]
        assert len(hospitals) > 0

        # Top ranked hospitals MUST be located in Purnea with minimal Haversine distance
        top_hosp = hospitals[0]
        assert top_hosp["district"].lower() == "purnea", f"Top hospital was {top_hosp['name']} in {top_hosp['district']}"
        assert top_hosp["distance_km"] < 15.0, f"Expected nearest local hospital (<15 km), got {top_hosp['distance_km']} km"

        # Verify distance ordering among same-district candidates
        purnea_hospitals = [h for h in hospitals if h["district"].lower() == "purnea"]
        distances = [h["distance_km"] for h in purnea_hospitals]
        assert distances == sorted(distances), f"Purnea hospitals were not sorted by distance: {distances}"
