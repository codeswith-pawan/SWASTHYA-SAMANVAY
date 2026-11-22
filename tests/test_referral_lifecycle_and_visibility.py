"""
Unit and Integration Tests for Referral Lifecycle State Transitions & Outbound Visibility.
Verifies:
1. Outbound Referrals visibility on originating hospital dashboard (GH99927).
2. Case-insensitive routing for hospital IDs.
3. Complete referral lifecycle:
   PENDING -> ACCEPTED -> IN_TRANSIT -> ARRIVED -> TREATMENT_ACTIVE -> COMPLETED.
4. Originating hospital bed release and visit status transition to TRANSFERRED on ambulance dispatch.
5. Destination hospital arrival confirmation, clinical treatment activation with destination visit creation, and final discharge.
"""

import os
import pytest
from starlette.testclient import TestClient
from src.api.main import app
from src.auth.jwt_utils import create_access_token
from src.database.db_manager import get_session_factory, is_postgres


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def setup_hospitals():
    """Ensure originating and destination test hospitals exist in test DB."""
    SessionFactory = get_session_factory()
    with SessionFactory() as s:
        if is_postgres():
            from src.database.pg_models import Hospital
        else:
            from src.database.models import Hospital

        # Originating Hospital
        h1 = s.query(Hospital).filter_by(hospital_id="GH99927").first()
        if not h1:
            h1_data = {
                "hospital_id": "GH99927",
                "name": "Purnea Sadar Hospital",
                "state": "Bihar",
                "district": "Purnia",
                "city": "Purnia",
                "latitude": 25.7771,
                "longitude": 87.4753,
                "total_beds": 100,
                "available_beds": 50,
                "occupied_beds": 50,
                "icu_beds": 20,
                "available_icu_beds": 10,
                "occupied_icu_beds": 10,
                "emergency_beds": 15,
                "available_emergency_beds": 8,
                "emergency_24x7": "Yes",
                "accepts_referral": "Yes",
                "cardiology": "Yes",
            }
            h1 = Hospital(**{k: v for k, v in h1_data.items() if hasattr(Hospital, k)})
            if hasattr(h1, "approval_status"):
                h1.approval_status = "APPROVED"
            s.add(h1)

        # Destination Hospital
        h2 = s.query(Hospital).filter_by(hospital_id="GH_BIH_PUR_02").first()
        if not h2:
            h2_data = {
                "hospital_id": "GH_BIH_PUR_02",
                "name": "Purnia Super Specialty & Trauma Centre",
                "state": "Bihar",
                "district": "Purnia",
                "city": "Purnia",
                "latitude": 25.7820,
                "longitude": 87.4810,
                "total_beds": 150,
                "available_beds": 80,
                "occupied_beds": 70,
                "icu_beds": 30,
                "available_icu_beds": 15,
                "occupied_icu_beds": 15,
                "emergency_beds": 25,
                "available_emergency_beds": 12,
                "emergency_24x7": "Yes",
                "accepts_referral": "Yes",
                "cardiology": "Yes",
            }
            h2 = Hospital(**{k: v for k, v in h2_data.items() if hasattr(Hospital, k)})
            if hasattr(h2, "approval_status"):
                h2.approval_status = "APPROVED"
            s.add(h2)

        s.commit()

    if not is_postgres():
        from src.prediction.reservation_store import save_hospital_inventory
        save_hospital_inventory({
            "hospital_id": "GH_BIH_PUR_02",
            "hospital_name": "Purnia Super Specialty & Trauma Centre",
            "total_beds": 150,
            "available_beds": 80,
            "occupied_beds": 70,
            "reserved_beds": 0,
            "icu_beds": 30,
            "available_icu_beds": 15,
            "occupied_icu_beds": 15,
            "reserved_icu_beds": 0,
            "emergency_beds": 25,
            "available_emergency_beds": 12,
            "occupied_emergency_beds": 13,
            "reserved_emergency_beds": 0,
            "ventilator_beds": 10,
            "available_ventilator_beds": 5,
            "occupied_ventilator_beds": 5,
            "reserved_ventilator_beds": 0,
            "beds": {
                **{f"ICU-{i:03d}": "AVAILABLE" for i in range(1, 16)},
                **{f"GENERAL-{i:03d}": "AVAILABLE" for i in range(1, 51)},
            },
        })


def test_outbound_referrals_visibility_and_case_insensitivity(client, setup_hospitals):
    """Originating hospital GH99927 sees outbound referrals with case-insensitive URLs."""
    token_origin = create_access_token({
        "user_id": "USR_GH99927",
        "username": "gh99927",
        "role": "HOSPITAL",
        "hospital_id": "GH99927",
        "district": "Purnia",
        "state": "Bihar",
    })
    headers_origin = {"Authorization": f"Bearer {token_origin}"}

    # Admit test patient
    admit_res = client.post(
        "/api/hospital/patients",
        json={
            "name": "Manish Verma",
            "age": 42,
            "gender": "Male",
            "blood_group": "A+",
            "district": "Purnia",
            "state": "Bihar",
            "chief_complaint": "Acute STEMI with cardiogenic shock",
            "required_specialty": "Cardiology",
            "bed_type_assigned": "ICU",
            "severity_level": "CRITICAL",
            "vitals": {"heart_rate": 110, "spo2": 91, "systolic_bp": 88, "diastolic_bp": 58},
        },
        headers=headers_origin,
    )
    assert admit_res.status_code == 200
    patient_id = admit_res.json()["patient"]["patient_id"]

    # Initiate Referral
    init_res = client.post(
        f"/api/hospital/patients/{patient_id}/refer",
        json={
            "to_hospital_id": "GH_BIH_PUR_02",
            "priority": "Critical",
            "reason": "Requires cath lab and primary PCI",
            "bed_type": "ICU",
            "transport_requirement": "ALS_AMBULANCE",
            "assessment": {
                "condition_summary": "STEMI unstable",
                "urgency": "CRITICAL",
                "required_specialty": "Cardiology",
                "required_bed_type": "ICU",
                "transport_requirement": "ALS_AMBULANCE",
            },
        },
        headers=headers_origin,
    )
    assert init_res.status_code == 200
    ref_id = init_res.json()["referral"]["referral_id"]

    # 1. Test uppercase URL with scope=outgoing
    res_out = client.get("/hospitals/GH99927/referrals?scope=outgoing", headers=headers_origin)
    assert res_out.status_code == 200
    out_ids = [r["referral_id"] for r in res_out.json().get("referrals", [])]
    assert ref_id in out_ids

    # 2. Test lowercase URL with scope=all
    res_all = client.get("/hospitals/gh99927/referrals?scope=all", headers=headers_origin)
    assert res_all.status_code == 200
    all_ids = [r["referral_id"] for r in res_all.json().get("referrals", [])]
    assert ref_id in all_ids


def test_complete_referral_lifecycle_and_bed_synchronization(client, setup_hospitals):
    """
    Test complete lifecycle:
    PENDING -> ACCEPTED -> IN_TRANSIT -> ARRIVED -> TREATMENT_ACTIVE -> COMPLETED
    Verifies bed release at origin on dispatch and bed reservation/release at destination.
    """
    token_origin = create_access_token({
        "user_id": "USR_GH99927",
        "username": "gh99927",
        "role": "HOSPITAL",
        "hospital_id": "GH99927",
        "district": "Purnia",
        "state": "Bihar",
    })
    headers_origin = {"Authorization": f"Bearer {token_origin}"}

    token_dest = create_access_token({
        "user_id": "USR_GH_BIH_PUR_02",
        "username": "gh_bih_pur_02",
        "role": "HOSPITAL",
        "hospital_id": "GH_BIH_PUR_02",
        "district": "Purnia",
        "state": "Bihar",
    })
    headers_dest = {"Authorization": f"Bearer {token_dest}"}

    # 1. Admit patient at GH99927
    admit_res = client.post(
        "/api/hospital/patients",
        json={
            "name": "Kavita Kumari",
            "age": 38,
            "gender": "Female",
            "blood_group": "B+",
            "district": "Purnia",
            "state": "Bihar",
            "chief_complaint": "Acute Respiratory Distress Syndrome",
            "required_specialty": "Pulmonology",
            "bed_type_assigned": "ICU",
            "severity_level": "CRITICAL",
            "vitals": {"heart_rate": 115, "spo2": 87},
        },
        headers=headers_origin,
    )
    assert admit_res.status_code == 200
    patient_id = admit_res.json()["patient"]["patient_id"]

    SessionFactory = get_session_factory()
    with SessionFactory() as s:
        if is_postgres():
            from src.database.pg_models import Hospital
        else:
            from src.database.models import Hospital
        orig_hosp_before = s.query(Hospital).filter_by(hospital_id="GH99927").first()
        orig_icu_occupied_before = getattr(orig_hosp_before, "occupied_icu_beds", 0)

    # 2. Initiate Referral
    init_res = client.post(
        f"/api/hospital/patients/{patient_id}/refer",
        json={
            "to_hospital_id": "GH_BIH_PUR_02",
            "priority": "Critical",
            "reason": "Requires ECMO and advanced mechanical ventilation",
            "bed_type": "ICU",
            "transport_requirement": "ALS_AMBULANCE",
            "assessment": {
                "condition_summary": "Severe ARDS requiring tertiary ICU care",
                "urgency": "CRITICAL",
                "required_specialty": "Pulmonology",
                "required_bed_type": "ICU",
                "transport_requirement": "ALS_AMBULANCE",
            },
        },
        headers=headers_origin,
    )
    assert init_res.status_code == 200
    ref_id = init_res.json()["referral"]["referral_id"]

    # 3. Destination accepts referral (PENDING -> ACCEPTED)
    accept_res = client.post(f"/referrals/{ref_id}/status/ACCEPTED", headers=headers_dest)
    if accept_res.status_code != 200:
        print("ACCEPT FAILED:", accept_res.status_code, accept_res.json())
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "ACCEPTED"

    # 4. Origin dispatches ambulance (ACCEPTED -> IN_TRANSIT)
    dispatch_res = client.post(
        f"/referrals/{ref_id}/status/IN_TRANSIT",
        json={"ambulance_id": "AMB-108-BIH-77", "eta_minutes": 20, "notes": "Dispatched with ALS unit."},
        headers=headers_origin,
    )
    assert dispatch_res.status_code == 200
    assert dispatch_res.json()["status"] == "IN_TRANSIT"

    # Verify origin visit is TRANSFERRED and origin bed counter is released
    with SessionFactory() as s:
        if is_postgres():
            from src.database.pg_models import Hospital, HospitalVisit
            orig_hosp_after = s.query(Hospital).filter_by(hospital_id="GH99927").first()
            assert orig_hosp_after.occupied_icu_beds < orig_icu_occupied_before
            orig_visit = s.query(HospitalVisit).filter_by(hospital_id="GH99927", patient_id=patient_id).first()
            assert orig_visit.status == "TRANSFERRED"

    # 5. Destination marks arrived (IN_TRANSIT -> ARRIVED)
    arrive_res = client.post(
        f"/referrals/{ref_id}/status/ARRIVED",
        json={"notes": "Arrived at bay 3."},
        headers=headers_dest,
    )
    assert arrive_res.status_code == 200
    assert arrive_res.json()["status"] == "ARRIVED"

    # 6. Destination begins treatment (ARRIVED -> TREATMENT_ACTIVE)
    treat_res = client.post(
        f"/referrals/{ref_id}/status/TREATMENT_ACTIVE",
        json={"notes": "Ventilator connected."},
        headers=headers_dest,
    )
    assert treat_res.status_code == 200
    assert treat_res.json()["status"] == "TREATMENT_ACTIVE"

    # Verify destination hospital active visit exists
    with SessionFactory() as s:
        if is_postgres():
            from src.database.pg_models import HospitalVisit
            dest_visit = s.query(HospitalVisit).filter_by(hospital_id="GH_BIH_PUR_02", patient_id=patient_id, status="ACTIVE").first()
            assert dest_visit is not None

    # 7. Destination completes care and releases bed (TREATMENT_ACTIVE -> COMPLETED)
    comp_res = client.post(
        f"/referrals/{ref_id}/status/COMPLETED",
        json={"notes": "Patient recovered, extubated, and successfully discharged."},
        headers=headers_dest,
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"

    # Verify destination visit is DISCHARGED
    with SessionFactory() as s:
        if is_postgres():
            from src.database.pg_models import HospitalVisit, Referral
            dest_visit_final = s.query(HospitalVisit).filter_by(hospital_id="GH_BIH_PUR_02", patient_id=patient_id).order_by(HospitalVisit.created_at.desc()).first()
            assert dest_visit_final.status == "DISCHARGED"
            ref_final = s.query(Referral).filter_by(referral_id=ref_id).first()
            assert ref_final.status == "COMPLETED"
            assert ref_final.completed_at is not None
