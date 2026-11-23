"""
Integration Tests for Purnea / Purnia District Alias Normalization,
Reviewer Queue Visibility, and Jurisdiction Authority.
SWASTHYA SAMANVAY — AI-Powered Smart Hospital Referral System
"""

import secrets
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.init_db import init_database
from src.services.registration_service import (
    normalize_district_name,
    get_district_aliases,
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


def test_district_normalization_helpers():
    """Verify phonetic and spelling normalization for Purnea / Purnia."""
    assert normalize_district_name("Purnia") == "purnea"
    assert normalize_district_name("Purnea") == "purnea"
    assert normalize_district_name("PURNEA ") == "purnea"
    assert normalize_district_name("  purnia") == "purnea"
    assert normalize_district_name("Patna") == "patna"

    aliases = get_district_aliases("Purnia")
    assert "purnea" in aliases
    assert "purnia" in aliases

    aliases_e = get_district_aliases("Purnea")
    assert "purnea" in aliases_e
    assert "purnia" in aliases_e


def test_purnea_and_purnia_applications_in_reviewer_queue():
    """
    Verify that applications submitted with either 'Purnia' or 'Purnea':
    1. Are accepted by application creation.
    2. Appear in district.purnea@swasthya.gov.in queue via GET /api/registration/applications.
    3. Allow dossier viewing via GET /api/registration/applications/{id} without 403 Forbidden.
    """
    suffix = secrets.token_hex(4)
    email_purnia = f"hospital.purnia.{suffix}@test.gov.in"
    email_purnea = f"hospital.purnea.{suffix}@test.gov.in"

    with TestClient(app) as client:
        # 1. Create application with spelling 'Purnia'
        resp_purnia = client.post(
            "/api/registration/applications/hospital",
            json={
                "applicant_name": f"Purnia Care Center {suffix}",
                "state": "Bihar",
                "district": "Purnia",
                "city": "Purnia",
                "address": "Line Bazar, Purnia",
                "pincode": "854301",
                "nodal_officer_name": "Dr. Purnia Incharge",
                "official_designation": "Medical Superintendent",
                "applicant_email": email_purnia,
                "applicant_phone": "9876543210",
                "profile_data": {"total_beds": 50, "icu_beds": 10},
            },
        )
        assert resp_purnia.status_code == 200, resp_purnia.text
        data_purnia = resp_purnia.json()
        app_id_purnia = data_purnia["application_id"]
        token_purnia = data_purnia["applicant_token"]
        headers_purnia = {"Authorization": f"Bearer {token_purnia}"}

        # Upload docs and submit
        client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "CLINICAL_LICENSE"},
            files={"file": ("clinical_license.pdf", VALID_PDF_BYTES, "application/pdf")},
            headers=headers_purnia,
        )
        client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "FIRE_SAFETY_NOC"},
            files={"file": ("fire_noc.jpg", VALID_JPEG_BYTES, "image/jpeg")},
            headers=headers_purnia,
        )
        sub_purnia = client.post(
            "/api/registration/applications/submit",
            json={"remarks": "Ready for district review"},
            headers=headers_purnia,
        )
        assert sub_purnia.status_code == 200, sub_purnia.text

        # 2. Create application with spelling 'Purnea'
        resp_purnea = client.post(
            "/api/registration/applications/hospital",
            json={
                "applicant_name": f"Purnea General Hospital {suffix}",
                "state": "Bihar",
                "district": "Purnea",
                "city": "Purnea",
                "address": "Bhatta Bazar, Purnea",
                "pincode": "854301",
                "nodal_officer_name": "Dr. Purnea Incharge",
                "official_designation": "Director",
                "applicant_email": email_purnea,
                "applicant_phone": "9876543211",
                "profile_data": {"total_beds": 75, "icu_beds": 15},
            },
        )
        assert resp_purnea.status_code == 200, resp_purnea.text
        data_purnea = resp_purnea.json()
        app_id_purnea = data_purnea["application_id"]
        token_purnea = data_purnea["applicant_token"]
        headers_purnea = {"Authorization": f"Bearer {token_purnea}"}

        # Upload docs and submit
        client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "CLINICAL_LICENSE"},
            files={"file": ("clinical_license.pdf", VALID_PDF_BYTES, "application/pdf")},
            headers=headers_purnea,
        )
        client.post(
            "/api/registration/applications/documents/upload",
            data={"document_type": "FIRE_SAFETY_NOC"},
            files={"file": ("fire_noc.jpg", VALID_JPEG_BYTES, "image/jpeg")},
            headers=headers_purnea,
        )
        sub_purnea = client.post(
            "/api/registration/applications/submit",
            json={"remarks": "Ready for district review"},
            headers=headers_purnea,
        )
        assert sub_purnea.status_code == 200, sub_purnea.text

        # 3. Login as Purnea District Reviewer
        dist_token = _login(client, "district.purnea@swasthya.gov.in", "DistPurnea@2026")
        headers = {"Authorization": f"Bearer {dist_token}"}

        # 4. Fetch reviewer applications queue
        list_resp = client.get("/api/registration/applications", headers=headers)
        assert list_resp.status_code == 200, list_resp.text
        data = list_resp.json()
        app_ids_in_queue = [a["application_id"] for a in data.get("applications", [])]

        assert app_id_purnia in app_ids_in_queue, f"Application with 'Purnia' ({app_id_purnia}) not found in Purnea reviewer queue"
        assert app_id_purnea in app_ids_in_queue, f"Application with 'Purnea' ({app_id_purnea}) not found in Purnea reviewer queue"

        # 5. Access dossier detail for both applications
        detail_purnia = client.get(f"/api/registration/applications/{app_id_purnia}", headers=headers)
        assert detail_purnia.status_code == 200, detail_purnia.text

        detail_purnea = client.get(f"/api/registration/applications/{app_id_purnea}", headers=headers)
        assert detail_purnea.status_code == 200, detail_purnea.text
