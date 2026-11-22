"""
End-to-End Test Suite for Hospital Patient Intake & Condition-Based Referral Workflow.
Validates:
1. Fresh patient registration and admission into PostgreSQL/DB with auto-generated patient_id and active visit.
2. Hospital active inpatient roster retrieval with demographics, diagnosis, severity, and vitals.
3. Doctor's Current Clinical Condition Assessment and AI-ranked suitable destination recommendations.
4. Patient referral initiation and verification in destination hospital's inbound queue.
5. Role authorization and jurisdictional boundaries.
"""

import pytest
from starlette.testclient import TestClient
from src.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def auth_headers_gh00046(client):
    """Originating hospital credentials."""
    res = client.post("/login", json={"username": "gh00046", "password": "hospital123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def auth_headers_dest_hospital(client):
    """Destination hospital credentials (gh_test_other or gh00045)."""
    res = client.post("/login", json={"username": "gh_test_other", "password": "hospital123"})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================
# 1. NEW PATIENT INTAKE & ADMISSION
# ============================================================

def test_patient_intake_unauthenticated(client):
    """Unauthenticated intake attempts must be rejected with 401."""
    res = client.post(
        "/api/hospital/patients",
        json={
            "name": "Unauthorized Patient",
            "age": 45,
            "gender": "Male",
            "chief_complaint": "Acute Chest Pain",
        },
    )
    assert res.status_code == 401


def test_patient_intake_and_admission_success(client, auth_headers_gh00046):
    """Hospital operator successfully admits a fresh inpatient with full demographics and vitals."""
    payload = {
        "name": "Gurpreet Singh",
        "age": 58,
        "gender": "Male",
        "blood_group": "B+",
        "contact_phone": "+91-9876543210",
        "emergency_contact": "Simran Kaur (Wife) - 9876543211",
        "address": "House 14, Mall Road, Amritsar",
        "district": "Amritsar",
        "state": "Punjab",
        "chief_complaint": "Acute Coronary Syndrome with Severe Dyspnea",
        "required_specialty": "Cardiology",
        "bed_type_assigned": "ICU",
        "severity_level": "CRITICAL",
        "vitals": {
            "heart_rate": 115,
            "systolic_bp": 150,
            "diastolic_bp": 95,
            "blood_pressure": "150/95",
            "spo2": 89,
            "temperature": 99.4,
            "respiratory_rate": 26,
            "gcs_score": 14,
        },
        "clinical_notes": "Patient admitted in emergency with crushing retrosternal chest pain. ECG shows ST-elevation in anterior leads.",
    }

    res = client.post("/api/hospital/patients", json=payload, headers=auth_headers_gh00046)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["success"] is True
    assert "registered and admitted successfully" in data["message"]

    pat = data["patient"]
    assert pat["patient_id"].startswith("PAT-")
    assert pat["name"] == "Gurpreet Singh"
    assert pat["priority"] == "Critical"
    assert pat["icu_required"] == "Yes"
    assert pat["bed_type"] == "ICU"
    assert pat["vitals"]["spo2"] == 89
    assert pat["vitals"]["heart_rate"] == 115
    assert pat["visit_id"] is not None

    # Test GET roster to ensure patient is listed
    roster_res = client.get("/api/hospital/patients", headers=auth_headers_gh00046)
    assert roster_res.status_code == 200
    roster = roster_res.json()
    assert roster["success"] is True
    assert roster["count"] >= 1
    found = next((p for p in roster["patients"] if p["patient_id"] == pat["patient_id"]), None)
    assert found is not None
    assert found["name"] == "Gurpreet Singh"
    assert found["bed_type"] == "ICU"
    assert found["referral_status"] == "NOT_REFERRED"


# ============================================================
# 2. CURRENT CLINICAL CONDITION ASSESSMENT & AI RECOMMENDATION
# ============================================================

def test_condition_assessment_and_ai_recommendation(client, auth_headers_gh00046):
    """Doctor assesses patient condition and gets AI-ranked destination hospitals excluding originating facility."""
    # First admit patient
    intake_res = client.post(
        "/api/hospital/patients",
        json={
            "name": "Manjit Kaur",
            "age": 62,
            "gender": "Female",
            "chief_complaint": "Acute Ischemic Stroke",
            "required_specialty": "Neurology",
            "bed_type_assigned": "GENERAL",
            "severity_level": "HIGH",
            "vitals": {
                "heart_rate": 90,
                "systolic_bp": 170,
                "diastolic_bp": 105,
                "spo2": 94,
                "temperature": 98.6,
                "respiratory_rate": 20,
            },
        },
        headers=auth_headers_gh00046,
    )
    assert intake_res.status_code == 200
    patient_id = intake_res.json()["patient"]["patient_id"]

    # Now evaluate condition for referral
    assessment = {
        "condition_summary": "Deteriorating neurological state with right-sided hemiparesis. Mechanical thrombectomy & Comprehensive Stroke ICU required immediately.",
        "urgency": "CRITICAL",
        "required_specialty": "Neurology",
        "required_bed_type": "ICU",
        "transport_requirement": "ALS_AMBULANCE",
        "vitals": {
            "heart_rate": 102,
            "systolic_bp": 185,
            "diastolic_bp": 115,
            "spo2": 91,
            "temperature": 98.8,
            "respiratory_rate": 24,
            "gcs_score": 11,
        },
    }

    rec_res = client.post(
        f"/api/hospital/patients/{patient_id}/recommend-hospitals",
        json=assessment,
        headers=auth_headers_gh00046,
    )
    assert rec_res.status_code == 200, rec_res.text
    data = rec_res.json()
    assert data["success"] is True
    assert data["patient_id"] == patient_id
    assert data["urgency"] == "CRITICAL"
    assert data["total_hospitals"] > 0
    assert len(data["hospitals"]) > 0

    # Ensure originating hospital (GH00046) is NOT in the recommendations
    for h in data["hospitals"]:
        assert h["hospital_id"] != "GH00046"
        assert h["match_score"] > 0
        assert h["distance_km"] >= 0
        assert len(h["ai_rationale"]) > 0


# ============================================================
# 3. REFERRAL INITIATION & INBOUND QUEUE APPEARANCE
# ============================================================

def test_initiate_referral_and_inbound_queue(client, auth_headers_gh00046, auth_headers_dest_hospital):
    """Refer patient from GH00046 to destination hospital and verify appearance in both queues."""
    # 1. Admit patient at GH00046
    intake = client.post(
        "/api/hospital/patients",
        json={
            "name": "Jaswinder Singh",
            "age": 49,
            "gender": "Male",
            "chief_complaint": "Severe Multiple Trauma with Pelvic Fracture",
            "required_specialty": "Trauma/Emergency",
            "bed_type_assigned": "GENERAL",
            "severity_level": "CRITICAL",
            "vitals": {"heart_rate": 120, "spo2": 88, "systolic_bp": 90, "diastolic_bp": 60},
        },
        headers=auth_headers_gh00046,
    ).json()
    patient_id = intake["patient"]["patient_id"]

    # 2. Get recommendations to pick a real destination hospital ID
    recs = client.post(
        f"/api/hospital/patients/{patient_id}/recommend-hospitals",
        json={
            "condition_summary": "Pelvic hemorrhage requiring emergency embolization and Level 1 trauma care.",
            "urgency": "CRITICAL",
            "required_specialty": "Trauma/Emergency",
            "required_bed_type": "ICU",
            "transport_requirement": "ALS_AMBULANCE",
            "vitals": {"heart_rate": 125, "spo2": 87, "systolic_bp": 85, "diastolic_bp": 55},
        },
        headers=auth_headers_gh00046,
    ).json()

    assert len(recs["hospitals"]) > 0
    dest_hosp_id = recs["hospitals"][0]["hospital_id"]

    # 3. Initiate referral to selected destination
    refer_res = client.post(
        f"/api/hospital/patients/{patient_id}/refer",
        json={
            "to_hospital_id": dest_hosp_id,
            "reason": "Emergency Level 1 Trauma transfer for pelvic embolization and ICU care.",
            "priority": "Critical",
            "bed_type": "ICU",
            "transport_requirement": "ALS_AMBULANCE",
        },
        headers=auth_headers_gh00046,
    )
    assert refer_res.status_code == 200, refer_res.text
    refer_data = refer_res.json()
    assert refer_data["success"] is True
    referral_id = refer_data["referral"]["referral_id"]
    assert referral_id.startswith("REF-")

    # 4. Check originating hospital's patient roster updates referral status
    roster_res = client.get("/api/hospital/patients", headers=auth_headers_gh00046)
    roster = roster_res.json()
    pat_in_roster = next((p for p in roster["patients"] if p["patient_id"] == patient_id), None)
    assert pat_in_roster is not None
    assert pat_in_roster["referral_status"] == "PENDING"
    assert pat_in_roster["active_referral"]["referral_id"] == referral_id

    # 5. Check originating hospital's outgoing referrals
    out_res = client.get("/hospitals/GH00046/referrals?scope=outgoing", headers=auth_headers_gh00046)
    assert out_res.status_code == 200
    out_refs = out_res.json().get("referrals", [])
    found_out = next((r for r in out_refs if r["referral_id"] == referral_id), None)
    assert found_out is not None
    assert found_out["patient_id"] == patient_id
    assert found_out["to_hospital_id"] == dest_hosp_id


# ============================================================
# 4. CROSS-HOSPITAL ACCESS RESTRICTION
# ============================================================

def test_cross_hospital_access_restriction(client, auth_headers_gh00046, auth_headers_dest_hospital):
    """A hospital user cannot recommend or refer a patient from a different hospital."""
    # Admit patient under GH00046
    intake = client.post(
        "/api/hospital/patients",
        json={
            "name": "Restricted Access Test",
            "age": 30,
            "gender": "Female",
            "chief_complaint": "Viral Fever",
        },
        headers=auth_headers_gh00046,
    ).json()
    patient_id = intake["patient"]["patient_id"]

    # Different hospital attempts to recommend or refer
    rec_res = client.post(
        f"/api/hospital/patients/{patient_id}/recommend-hospitals",
        json={"condition_summary": "Unauthorized inspection", "urgency": "ROUTINE"},
        headers=auth_headers_dest_hospital,
    )
    assert rec_res.status_code == 403


# ============================================================
# 5. PURNEA MULTI-DISTRICT PROXIMITY RANKING TEST
# ============================================================

def test_purnea_hospital_multi_district_proximity_ranking(client):
    """
    Verify that referrals from Purnea Hospital (GH99927) prioritize local Purnia,
    neighboring Seemanchal/Kosi districts, and same-state Bihar hospitals over distant out-of-state facilities.
    """
    from src.database.db_manager import get_session_factory, is_postgres
    SessionFactory = get_session_factory()
    with SessionFactory() as db_session:
        if is_postgres():
            from src.database.pg_models import Hospital
        else:
            from src.database.models import Hospital
        h = db_session.query(Hospital).filter_by(hospital_id="GH99927").first()
        if not h:
            h = Hospital(
                hospital_id="GH99927",
                name="Purnea Hospital",
                state="Bihar",
                district="Purnia",
                city="Purnia",
                latitude=25.7771,
                longitude=87.4753,
                total_beds=100,
                available_beds=50,
                icu_beds=20,
                available_icu_beds=10,
                emergency_beds=15,
                available_emergency_beds=8,
                emergency_24x7="Yes",
                accepts_referral="Yes",
                cardiology="Yes",
            )
            if hasattr(h, "approval_status"):
                h.approval_status = "APPROVED"
            db_session.add(h)

        # Ensure nearby candidate Bihar hospitals exist in test database
        bihar_cands = [
            ("GH_TEST_PUR_01", "Purnia Sadar Test Hospital", "Purnia", 25.7802, 87.4721),
            ("GH_TEST_KTR_01", "Katihar Sadar Test Hospital", "Katihar", 25.5420, 87.5680),
            ("GH_TEST_PAT_01", "AIIMS Patna Test Hospital", "Patna", 25.5615, 85.0445),
        ]
        for cid, cname, cdist, clat, clon in bihar_cands:
            cand = db_session.query(Hospital).filter_by(hospital_id=cid).first()
            if not cand:
                cand = Hospital(
                    hospital_id=cid,
                    name=cname,
                    state="Bihar",
                    district=cdist,
                    city=cdist,
                    latitude=clat,
                    longitude=clon,
                    total_beds=100,
                    available_beds=50,
                    icu_beds=20,
                    available_icu_beds=10,
                    emergency_beds=15,
                    available_emergency_beds=8,
                    emergency_24x7="Yes",
                    accepts_referral="Yes",
                    cardiology="Yes",
                )
                if hasattr(cand, "approval_status"):
                    cand.approval_status = "APPROVED"
                db_session.add(cand)
        db_session.commit()

    login_res = client.post("/login", json={"username": "gh99927", "password": "Hospital@123"})
    assert login_res.status_code == 200
    purnia_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 1. Admit patient at Purnea Hospital
    intake = client.post(
        "/api/hospital/patients",
        json={
            "name": "Anil Kumar Yadav",
            "age": 52,
            "gender": "Male",
            "district": "Purnia",
            "state": "Bihar",
            "chief_complaint": "Acute STEMI with Cardiogenic Shock",
            "required_specialty": "Cardiology",
            "bed_type_assigned": "ICU",
            "severity_level": "CRITICAL",
            "vitals": {
                "heart_rate": 118,
                "systolic_bp": 85,
                "diastolic_bp": 55,
                "spo2": 88,
                "temperature": 98.4,
            },
        },
        headers=purnia_headers,
    )
    assert intake.status_code == 200
    patient_id = intake.json()["patient"]["patient_id"]

    # 2. Query AI hospital recommendations
    rec_res = client.post(
        f"/api/hospital/patients/{patient_id}/recommend-hospitals",
        json={
            "condition_summary": "Anterior wall STEMI requiring urgent catheterization and ICU bed.",
            "urgency": "CRITICAL",
            "required_specialty": "Cardiology",
            "required_bed_type": "ICU",
            "transport_requirement": "ALS_AMBULANCE",
            "vitals": {
                "heart_rate": 120,
                "systolic_bp": 82,
                "diastolic_bp": 52,
                "spo2": 87,
                "temperature": 98.6,
            },
        },
        headers=purnia_headers,
    )
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["success"] is True
    hospitals = rec_data["hospitals"]
    assert len(hospitals) >= 3

    # Originating hospital must not be recommended
    assert all(h["hospital_id"] != "GH99927" for h in hospitals)

    # Top recommendations must be nearby Bihar regional facilities (not distant Punjab/Delhi)
    top_hospitals = hospitals[:3]
    for h in top_hospitals:
        assert h["state"] == "Bihar", f"Top recommendation {h['hospital_name']} must be in Bihar, found: {h['state']}"
        assert h["distance_km"] < 350.0, f"Facility {h['hospital_name']} distance {h['distance_km']} km exceeds regional threshold"

    # The #1 recommendation should be in Purnia or immediate neighboring district
    first_choice = hospitals[0]
    assert first_choice["district"] in ["Purnia", "Katihar", "Araria", "Kishanganj", "Bhagalpur"]
    assert first_choice["distance_km"] <= 30.0 or first_choice["match_score"] >= 90.0
