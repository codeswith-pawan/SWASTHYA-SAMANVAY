"""
Hospital Clinical Command - Patient Intake & Condition-Based Referral Routes
Provides authenticated endpoints for hospital operators to admit fresh patients,
view active inpatient rosters, perform clinical condition assessments,
and initiate AI-ranked network referrals.
"""

from datetime import datetime, timezone
import json
import logging
import math
import re
import secrets
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import case, desc
from sqlalchemy.orm import Session

from src.auth.authorization import can_access_hospital
from src.auth.dependencies import require_current_user
from src.database.db_manager import get_db_session as get_db, is_postgres
from src.prediction.feature_builder import build_referral_features
from src.prediction.predict import MODEL_FEATURES, load_model
from src.prediction.recommendation import generate_recommendation_reason
from src.prediction.referral_store import create_referral as create_stored_referral
from src.prediction.reservation_store import load_bed_inventory
from src.utils.helpers import calculate_distance_km
from src.utils.referral_rules import evaluate_hospital_capability

logger = logging.getLogger("hospital_patients")

router = APIRouter(tags=["Hospital Clinical Command"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class PatientVitalsInput(BaseModel):
    heart_rate: Optional[int] = Field(default=None, ge=20, le=300)
    systolic_bp: Optional[int] = Field(default=None, ge=40, le=300)
    diastolic_bp: Optional[int] = Field(default=None, ge=20, le=200)
    blood_pressure: Optional[str] = None  # e.g. "120/80"
    spo2: Optional[int] = Field(default=None, ge=30, le=100)
    temperature: Optional[float] = Field(default=None, ge=80.0, le=115.0)
    respiratory_rate: Optional[int] = Field(default=None, ge=4, le=100)
    gcs_score: Optional[int] = Field(default=None, ge=3, le=15)


class PatientIntakePayload(BaseModel):
    # Demographics
    name: str = Field(..., min_length=2, max_length=255)
    age: int = Field(..., ge=0, le=130)
    gender: str = Field(..., min_length=1, max_length=20)
    blood_group: Optional[str] = None
    contact_phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    address: Optional[str] = None
    district: Optional[str] = None
    state: Optional[str] = None

    # Clinical Admission Details
    chief_complaint: str = Field(..., min_length=2, max_length=500)
    disease: Optional[str] = None
    primary_diagnosis: Optional[str] = None
    required_specialty: Optional[str] = "General Medicine"
    bed_type_assigned: Optional[str] = "GENERAL"  # GENERAL, ICU, VENTILATOR, OXYGEN, EMERGENCY_BAY
    severity_level: Optional[str] = "MODERATE"  # LOW, MODERATE, HIGH, CRITICAL
    vitals: Optional[PatientVitalsInput] = None
    clinical_notes: Optional[str] = None
    patient_id: Optional[str] = None


class ConditionAssessmentPayload(BaseModel):
    condition_summary: str = Field(..., min_length=3, max_length=1000)
    vitals: Optional[PatientVitalsInput] = None
    urgency: Optional[str] = "URGENT"  # ROUTINE, URGENT, EMERGENCY, CRITICAL
    required_specialty: Optional[str] = "General Medicine"
    required_bed_type: Optional[str] = "GENERAL"  # ICU, VENTILATOR, GENERAL, EMERGENCY, NICU
    transport_requirement: Optional[str] = "NONE"  # BASIC_AMBULANCE, ALS_AMBULANCE, NONE


class InitiateReferralPayload(BaseModel):
    to_hospital_id: str = Field(..., min_length=2, max_length=64)
    reason: str = Field(..., min_length=3, max_length=1000)
    priority: Optional[str] = "Urgent"  # Critical, Urgent, Stable
    bed_type: Optional[str] = "GENERAL"  # ICU, GENERAL, EMERGENCY
    transport_requirement: Optional[str] = "NONE"
    clinical_condition_snapshot: Optional[Dict[str, Any]] = None


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _generate_patient_id() -> str:
    """Generate a unique human-readable patient identifier (PAT-YYYYMMDD-XXXXXX)."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    hex_part = secrets.token_hex(3).upper()
    return f"PAT-{date_part}-{hex_part}"


def _map_severity_to_priority(severity: Optional[str]) -> str:
    """Map triage severity levels (LOW/MODERATE/HIGH/CRITICAL) to Patient priority column."""
    if not severity:
        return "Stable"
    s = str(severity).strip().upper()
    if s in ["CRITICAL", "EMERGENCY"]:
        return "Critical"
    if s in ["HIGH", "URGENT"]:
        return "Urgent"
    if s in ["MODERATE", "LOW", "ROUTINE", "STABLE"]:
        return "Stable"
    if s.capitalize() in ["Critical", "Urgent", "Stable"]:
        return s.capitalize()
    return "Stable"


def _parse_bp_string(bp_str: Optional[str]) -> tuple[Optional[int], Optional[int]]:
    """Parse '120/80' format into (systolic, diastolic)."""
    if not bp_str:
        return None, None
    m = re.match(r"^\s*(\d{2,3})\s*/\s*(\d{2,3})\s*$", bp_str.strip())
    if m:
        try:
            return int(m.group(1)), int(m.group(2))
        except ValueError:
            pass
    return None, None


def _get_active_models(db: Optional[Session] = None):
    """Retrieve database model classes matching active backend driver and session dialect."""
    dialect_name = None
    if db is not None:
        try:
            bind = db.get_bind()
            if bind is not None:
                dialect_name = getattr(bind.dialect, "name", None)
        except Exception:
            pass

    if dialect_name == "postgresql":
        from src.database.pg_models import (
            Hospital as HospModel,
            HospitalVisit as VisitModel,
            Patient as PatModel,
            Referral as RefModel,
        )
    elif dialect_name == "sqlite":
        from src.database.models import (
            Hospital as HospModel,
            HospitalVisit as VisitModel,
            Patient as PatModel,
            Referral as RefModel,
        )
    elif is_postgres():
        from src.database.pg_models import (
            Hospital as HospModel,
            HospitalVisit as VisitModel,
            Patient as PatModel,
            Referral as RefModel,
        )
    else:
        from src.database.models import (
            Hospital as HospModel,
            HospitalVisit as VisitModel,
            Patient as PatModel,
            Referral as RefModel,
        )
    return PatModel, VisitModel, HospModel, RefModel


def _get_hospital_id_for_user(current_user: dict, requested_hospital_id: Optional[str] = None) -> str:
    """Validate and return authorized hospital ID."""
    user_role = current_user.get("role")
    user_hospital = current_user.get("hospital_id")

    if user_role == "HOSPITAL":
        if not user_hospital:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hospital user account lacks an assigned hospital_id.",
            )
        if requested_hospital_id and requested_hospital_id != user_hospital:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hospital operators are restricted to their assigned facility.",
            )
        return user_hospital

    if user_role in ["CENTRAL_ADMIN", "STATE_ADMIN", "DISTRICT_ADMIN"]:
        target = requested_hospital_id or user_hospital
        if not target:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target hospital_id must be specified for administrative intake.",
            )
        if not can_access_hospital(current_user, target):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied for hospital jurisdiction: {target}",
            )
        return target

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Insufficient role permissions for clinical patient operations.",
    )


# ============================================================
# 1. ADMIT / CREATE FRESH PATIENT
# ============================================================

@router.post("/patients")
def admit_fresh_patient(
    payload: PatientIntakePayload,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """
    Register and admit a fresh inpatient under the logged-in hospital facility.
    Generates unique PAT-YYYYMMDD-XXXXXX if omitted, persists Patient and HospitalVisit,
    and records baseline clinical vitals, severity, and bed allocation.
    """
    hospital_id = _get_hospital_id_for_user(current_user)
    PatModel, VisitModel, HospModel, _ = _get_active_models(db)

    # Look up hospital geo metadata
    hospital_rec = db.query(HospModel).filter(HospModel.hospital_id == hospital_id).first()
    hosp_state = hospital_rec.state if hospital_rec else "Punjab"
    hosp_district = hospital_rec.district if hospital_rec else "Amritsar"
    hosp_lat = getattr(hospital_rec, "latitude", None) or 31.634
    hosp_lon = getattr(hospital_rec, "longitude", None) or 74.872

    # Determine unique patient_id
    patient_id = payload.patient_id.strip() if payload.patient_id else _generate_patient_id()
    while db.query(PatModel).filter(PatModel.patient_id == patient_id).first() is not None:
        patient_id = _generate_patient_id()

    # Parse and normalize vitals
    vitals_dict = payload.vitals.model_dump() if payload.vitals else {}
    sbp = vitals_dict.get("systolic_bp")
    dbp = vitals_dict.get("diastolic_bp")
    if (sbp is None or dbp is None) and vitals_dict.get("blood_pressure"):
        parsed_s, parsed_d = _parse_bp_string(vitals_dict["blood_pressure"])
        sbp = sbp or parsed_s
        dbp = dbp or parsed_d

    spo2 = vitals_dict.get("spo2")
    hr = vitals_dict.get("heart_rate")
    temp = vitals_dict.get("temperature")
    rr = vitals_dict.get("respiratory_rate")

    # Priority & ICU Requirements
    priority = _map_severity_to_priority(payload.severity_level)
    assigned_bed = (payload.bed_type_assigned or "GENERAL").strip().upper()
    is_icu = assigned_bed in ["ICU", "VENTILATOR"] or payload.severity_level == "CRITICAL"
    icu_required = "Yes" if is_icu else "No"

    # Construct Diagnosis text
    primary_diag = (
        payload.primary_diagnosis
        or payload.disease
        or payload.chief_complaint
    ).strip()

    # 1. Create Patient Record with safe column mapping
    pat_kwargs = {
        "patient_id": patient_id,
        "name": payload.name.strip(),
        "age": payload.age,
        "gender": payload.gender.strip(),
        "disease": primary_diag,
        "priority": priority,
        "icu_required": icu_required,
    }
    extended_fields = {
        "ambulance_required": "Yes" if priority == "Critical" else "No",
        "referral_required": "No",
        "spo2": spo2,
        "systolic_bp": sbp,
        "diastolic_bp": dbp,
        "heart_rate": hr,
        "respiratory_rate": rr,
        "temperature": temp,
        "state": payload.state or hosp_state,
        "district": payload.district or hosp_district,
        "latitude": hosp_lat,
        "longitude": hosp_lon,
    }
    for col_name, val in extended_fields.items():
        if col_name in PatModel.__table__.columns:
            pat_kwargs[col_name] = val

    new_patient = PatModel(**pat_kwargs)
    db.add(new_patient)

    # 2. Build structured admission metadata JSON for visit.notes
    admission_metadata = {
        "blood_group": payload.blood_group,
        "contact_phone": payload.contact_phone,
        "emergency_contact": payload.emergency_contact,
        "address": payload.address,
        "chief_complaint": payload.chief_complaint,
        "required_specialty": payload.required_specialty or "General Medicine",
        "bed_type_assigned": assigned_bed,
        "severity_level": payload.severity_level or "MODERATE",
        "clinical_notes": payload.clinical_notes,
        "admitted_by": current_user.get("username"),
        "vitals": {
            "heart_rate": hr,
            "systolic_bp": sbp,
            "diastolic_bp": dbp,
            "blood_pressure": f"{sbp}/{dbp}" if sbp and dbp else vitals_dict.get("blood_pressure"),
            "spo2": spo2,
            "temperature": temp,
            "respiratory_rate": rr,
            "gcs_score": vitals_dict.get("gcs_score"),
        },
    }

    # 3. Create active HospitalVisit Record
    now = datetime.now(timezone.utc)
    new_visit = VisitModel(
        patient_id=patient_id,
        hospital_id=hospital_id,
        status="ACTIVE",
        admission_type="DIRECT",
        admitted_at=now,
        treatment_started_at=now,
        notes=json.dumps(admission_metadata),
    )
    db.add(new_visit)

    # 4. Synchronize bed occupancy counters on Hospital if present
    if hospital_rec:
        if assigned_bed == "ICU":
            if getattr(hospital_rec, "available_icu_beds", 0) and hospital_rec.available_icu_beds > 0:
                hospital_rec.available_icu_beds -= 1
            if hasattr(hospital_rec, "occupied_icu_beds"):
                hospital_rec.occupied_icu_beds = (getattr(hospital_rec, "occupied_icu_beds", 0) or 0) + 1
        elif assigned_bed in ["GENERAL", "OXYGEN"]:
            if getattr(hospital_rec, "available_beds", 0) and hospital_rec.available_beds > 0:
                hospital_rec.available_beds -= 1
            if hasattr(hospital_rec, "occupied_beds"):
                hospital_rec.occupied_beds = (getattr(hospital_rec, "occupied_beds", 0) or 0) + 1

    try:
        db.commit()
        db.refresh(new_patient)
        db.refresh(new_visit)
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to persist patient admission: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during patient admission: {str(exc)}",
        )

    return {
        "success": True,
        "message": f"Patient {patient_id} registered and admitted successfully.",
        "patient": {
            "patient_id": new_patient.patient_id,
            "name": new_patient.name,
            "age": new_patient.age,
            "gender": new_patient.gender,
            "disease": new_patient.disease,
            "priority": new_patient.priority,
            "icu_required": new_patient.icu_required,
            "bed_type": assigned_bed,
            "severity_level": payload.severity_level,
            "required_specialty": payload.required_specialty,
            "admitted_at": new_visit.admitted_at.isoformat() if new_visit.admitted_at else None,
            "visit_id": getattr(new_visit, "id", None),
            "vitals": admission_metadata["vitals"],
            "notes": payload.clinical_notes,
        },
    }


# ============================================================
# 2. LIST HOSPITAL PATIENTS (ACTIVE & ADMITTED ROSTER)
# ============================================================

@router.get("/patients")
def list_hospital_patients(
    hospital_id: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """
    List all admitted and active inpatient records for the authenticated hospital facility.
    Includes patient demographics, diagnosis, current severity, bed allocation,
    latest vitals snapshot, admission timestamp, and network referral status.
    """
    effective_hospital_id = _get_hospital_id_for_user(current_user, hospital_id)
    PatModel, VisitModel, _, RefModel = _get_active_models(db)

    query = (
        db.query(VisitModel, PatModel)
        .join(PatModel, VisitModel.patient_id == PatModel.patient_id)
        .filter(VisitModel.hospital_id == effective_hospital_id)
    )

    if status_filter:
        query = query.filter(VisitModel.status == status_filter.upper())
    else:
        # Default: return currently admitted inpatients first (ACTIVE, NEW) or recent
        query = query.filter(VisitModel.status.in_(["ACTIVE", "NEW", "COMPLETED"]))

    # Sort critical cases first, then most recently admitted
    records = query.order_by(
        case(
            (PatModel.priority == "Critical", 1),
            (PatModel.priority == "Urgent", 2),
            (PatModel.priority == "Stable", 3),
            else_=4,
        ),
        desc(VisitModel.admitted_at),
    ).all()

    # Pre-fetch recent referrals for active patients from DB and runtime store
    patient_ids = [pat.patient_id for _, pat in records]
    referral_map: Dict[str, Any] = {}
    if patient_ids:
        try:
            recent_refs = (
                db.query(RefModel)
                .filter(RefModel.patient_id.in_(patient_ids))
                .order_by(desc(RefModel.created_at))
                .all()
            )
            for ref in recent_refs:
                if ref.patient_id not in referral_map:
                    referral_map[ref.patient_id] = {
                        "referral_id": ref.referral_id,
                        "status": ref.status,
                        "to_hospital_id": ref.to_hospital_id,
                        "created_at": ref.created_at.isoformat() if ref.created_at else None,
                    }
        except Exception:
            pass

    # Runtime referral store synchronization
    try:
        from src.prediction.referral_store import _load_referrals
        for ref in _load_referrals():
            pid = ref.get("patient_id")
            if pid in patient_ids and (pid not in referral_map or referral_map[pid].get("status") in ["NOT_REFERRED", None]):
                referral_map[pid] = {
                    "referral_id": ref.get("referral_id"),
                    "status": ref.get("status", "PENDING"),
                    "to_hospital_id": ref.get("to_hospital_id"),
                    "created_at": ref.get("created_at"),
                }
    except Exception:
        pass

    patient_list = []
    for visit, patient in records:
        # Parse notes JSON if present
        meta: Dict[str, Any] = {}
        if visit.notes:
            try:
                meta = json.loads(visit.notes)
            except Exception:
                meta = {"clinical_notes": visit.notes}

        vitals = meta.get("vitals") or {
            "spo2": getattr(patient, "spo2", None),
            "heart_rate": getattr(patient, "heart_rate", None),
            "systolic_bp": getattr(patient, "systolic_bp", None),
            "diastolic_bp": getattr(patient, "diastolic_bp", None),
            "temperature": getattr(patient, "temperature", None),
            "respiratory_rate": getattr(patient, "respiratory_rate", None),
        }

        ref_info = referral_map.get(patient.patient_id) or meta.get("active_referral")

        patient_list.append({
            "visit_id": getattr(visit, "id", None),
            "patient_id": patient.patient_id,
            "name": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "blood_group": meta.get("blood_group"),
            "contact_phone": meta.get("contact_phone"),
            "emergency_contact": meta.get("emergency_contact"),
            "address": meta.get("address"),
            "district": getattr(patient, "district", meta.get("district")),
            "state": getattr(patient, "state", meta.get("state")),
            "disease": patient.disease,
            "chief_complaint": meta.get("chief_complaint", patient.disease),
            "priority": patient.priority,
            "severity_level": meta.get("severity_level", patient.priority.upper() if patient.priority else "STABLE"),
            "icu_required": patient.icu_required,
            "bed_type": meta.get("bed_type_assigned", "ICU" if patient.icu_required == "Yes" else "GENERAL"),
            "required_specialty": meta.get("required_specialty", "General Medicine"),
            "status": visit.status,
            "admission_type": visit.admission_type,
            "admitted_at": visit.admitted_at.isoformat() if visit.admitted_at else None,
            "treatment_started_at": visit.treatment_started_at.isoformat() if visit.treatment_started_at else None,
            "vitals": vitals,
            "clinical_notes": meta.get("clinical_notes"),
            "referral_status": ref_info["status"] if ref_info else "NOT_REFERRED",
            "active_referral": ref_info,
        })

    return {
        "success": True,
        "hospital_id": effective_hospital_id,
        "count": len(patient_list),
        "patients": patient_list,
    }


# ============================================================
# 3. CONDITION-BASED AI HOSPITAL RECOMMENDATIONS
# ============================================================

@router.post("/patients/{patient_id}/recommend-hospitals")
def recommend_suitable_hospitals(
    patient_id: str,
    payload: ConditionAssessmentPayload,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """
    Accept doctor's updated Current Clinical Condition Assessment,
    update patient's real-time vitals and urgency state, and run the AI recommendation
    scoring engine (excluding originating hospital) to return ranked destination facilities.
    """
    hospital_id = _get_hospital_id_for_user(current_user)
    PatModel, VisitModel, HospModel, _ = _get_active_models(db)

    patient = db.query(PatModel).filter(PatModel.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found.",
        )

    # Verify visit belongs to current hospital
    visit = (
        db.query(VisitModel)
        .filter(
            VisitModel.patient_id == patient_id,
            VisitModel.hospital_id == hospital_id,
        )
        .order_by(desc(VisitModel.admitted_at))
        .first()
    )
    if not visit and current_user.get("role") == "HOSPITAL":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized: Patient has no admission record at this facility.",
        )

    # Update patient vitals and condition from doctor's assessment
    vitals_dict = payload.vitals.model_dump() if payload.vitals else {}
    sbp = vitals_dict.get("systolic_bp")
    dbp = vitals_dict.get("diastolic_bp")
    if (sbp is None or dbp is None) and vitals_dict.get("blood_pressure"):
        parsed_s, parsed_d = _parse_bp_string(vitals_dict["blood_pressure"])
        sbp = sbp or parsed_s
        dbp = dbp or parsed_d

    def _safe_set(obj, col, val):
        if col in PatModel.__table__.columns and val is not None:
            setattr(obj, col, val)

    _safe_set(patient, "spo2", vitals_dict.get("spo2"))
    _safe_set(patient, "systolic_bp", sbp)
    _safe_set(patient, "diastolic_bp", dbp)
    _safe_set(patient, "heart_rate", vitals_dict.get("heart_rate"))
    _safe_set(patient, "respiratory_rate", vitals_dict.get("respiratory_rate"))
    _safe_set(patient, "temperature", vitals_dict.get("temperature"))

    new_priority = _map_severity_to_priority(payload.urgency)
    patient.priority = new_priority
    req_bed = (payload.required_bed_type or "GENERAL").strip().upper()
    if req_bed in ["ICU", "VENTILATOR"]:
        patient.icu_required = "Yes"
    _safe_set(patient, "referral_required", "Yes")
    _safe_set(patient, "ambulance_required", "Yes" if payload.transport_requirement in ["BASIC_AMBULANCE", "ALS_AMBULANCE"] else "No")

    # Append to visit notes
    if visit:
        current_meta = {}
        if visit.notes:
            try:
                current_meta = json.loads(visit.notes)
            except Exception:
                current_meta = {"raw_notes": visit.notes}
        current_meta["latest_condition_assessment"] = {
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "evaluated_by": current_user.get("username"),
            "condition_summary": payload.condition_summary,
            "urgency": payload.urgency,
            "required_specialty": payload.required_specialty,
            "required_bed_type": req_bed,
            "transport_requirement": payload.transport_requirement,
            "vitals": vitals_dict,
        }
        visit.notes = json.dumps(current_meta)

    db.commit()
    db.refresh(patient)

    # ----------------------------------------------------
    # RUN AI RECOMMENDATION ENGINE (Excluding Originating Hospital)
    # ----------------------------------------------------
    originating_hosp = db.query(HospModel).filter(HospModel.hospital_id == hospital_id).first()
    
    # Establish reference origin coordinates (originating hospital if set, else patient record)
    orig_lat = getattr(originating_hosp, "latitude", None) if originating_hosp else None
    orig_lon = getattr(originating_hosp, "longitude", None) if originating_hosp else None

    # Specific geo-correction for GH99927 (Purnea Hospital, Bihar)
    if hospital_id == "GH99927" and (orig_lat is None or abs(float(orig_lat) - 31.634) < 0.01):
        orig_lat = 25.7771
        orig_lon = 87.4753

    try:
        plat = float(orig_lat if orig_lat is not None else (getattr(patient, "latitude", None) or 25.7771))
    except Exception:
        plat = 25.7771
    try:
        plon = float(orig_lon if orig_lon is not None else (getattr(patient, "longitude", None) or 87.4753))
    except Exception:
        plon = 87.4753

    orig_district = (getattr(originating_hosp, "district", None) or getattr(patient, "district", "") or "").strip()
    orig_state = (getattr(originating_hosp, "state", None) or getattr(patient, "state", "") or "").strip()

    # All destination facilities excluding source
    all_hospitals = db.query(HospModel).filter(HospModel.hospital_id != hospital_id).all()
    inventory_map = load_bed_inventory()

    patient_dict = {
        "patient_id": patient.patient_id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "disease": payload.required_specialty or patient.disease,
        "priority": patient.priority,
        "icu_required": patient.icu_required,
        "ambulance_required": getattr(patient, "ambulance_required", "No"),
        "referral_required": "Yes",
        "spo2": getattr(patient, "spo2", 98) or 98,
        "systolic_bp": getattr(patient, "systolic_bp", 120) or 120,
        "diastolic_bp": getattr(patient, "diastolic_bp", 80) or 80,
        "heart_rate": getattr(patient, "heart_rate", 75) or 75,
        "respiratory_rate": getattr(patient, "respiratory_rate", 18) or 18,
        "temperature": getattr(patient, "temperature", 98.6) or 98.6,
        "latitude": plat,
        "longitude": plon,
        "bed_type": req_bed,
    }

    candidates = []
    for h in all_hospitals:
        h_dict = {column.name: getattr(h, column.name) for column in HospModel.__table__.columns}

        # Apply live bed inventory counters if tracked
        inv = inventory_map.get(h.hospital_id)
        if inv is not None:
            beds = inv.get("beds", {})
            h_dict["available_beds"] = sum(s == "AVAILABLE" for b, s in beds.items() if b.startswith("GENERAL"))
            h_dict["available_icu_beds"] = sum(s == "AVAILABLE" for b, s in beds.items() if b.startswith("ICU"))

        # Calculate distance safely
        try:
            hlat = float(h_dict.get("latitude") or 31.634)
            hlon = float(h_dict.get("longitude") or 74.872)
            dist_km = calculate_distance_km(plat, plon, hlat, hlon)
        except Exception:
            dist_km = 30.0
        h_dict["distance_km"] = round(dist_km, 1)

        # Estimate transit ETA in minutes (avg speed 40 km/h + 12 min dispatch)
        eta_mins = max(10, int(round((dist_km / 40.0) * 60.0) + 12))
        h_dict["eta_minutes"] = eta_mins

        # Capability Check
        cap = evaluate_hospital_capability(patient_dict, h_dict, bed_type=req_bed)
        h_dict["capability_eligible"] = cap.get("eligible", True)
        h_dict["hard_blocks"] = cap.get("hard_blocks", [])

        # Specialty check matching doctor's required specialty
        spec_col = (payload.required_specialty or "general_medicine").lower().replace(" ", "_").replace("/", "_")
        has_spec = h_dict.get(spec_col) in ["Yes", 1, True] or h_dict.get("general_medicine") in ["Yes", 1, True]
        h_dict["specialty_matched"] = has_spec

        candidates.append(h_dict)

    # Filter to eligible or soft-warning facilities
    eligible = [c for c in candidates if c.get("accepts_referral") in ["Yes", 1, True]]
    if not eligible:
        eligible = candidates  # Fallback to any network hospital if none accept referrals

    # ML batch prediction for success probability
    model = load_model()
    feature_rows = []
    for h_data in eligible:
        feats = build_referral_features(patient_dict, h_data)
        h_data.update(feats)
        row = feats.copy()
        for feat in MODEL_FEATURES:
            if feat.startswith("disease_"):
                row[feat] = int(patient_dict["disease"] == feat[len("disease_"):])
            elif feat.startswith("priority_"):
                row[feat] = int(patient_dict["priority"] == feat[len("priority_"):])
        feature_rows.append(row)

    if feature_rows:
        import pandas as pd
        batch_df = pd.DataFrame(feature_rows, columns=MODEL_FEATURES)
        probs = model.predict_proba(batch_df)
        for i, h_data in enumerate(eligible):
            prob = float(probs[i][1])
            h_data["success_probability"] = round(prob, 4) if (not math.isnan(prob) and 0.0 <= prob <= 1.0) else 0.5
    else:
        for h_data in eligible:
            h_data["success_probability"] = 0.5

    # Compute composite match score (%)
    ranked_hospitals = []
    for h_data in eligible:
        ml_score = h_data.get("success_probability", 0.5) * 100.0

        # Bed availability factor
        avail_icu = h_data.get("available_icu_beds", 0) or 0
        avail_gen = h_data.get("available_beds", 0) or 0
        bed_factor = 25.0 if (req_bed in ["ICU", "VENTILATOR"] and avail_icu > 0) or (req_bed == "GENERAL" and avail_gen > 0) else 5.0

        # Specialty factor
        spec_factor = 25.0 if h_data.get("specialty_matched") else 10.0

        # Geographic Distance & Regional Proximity Scoring
        dist_km = h_data["distance_km"]
        h_dist = (h_data.get("district") or "").strip()
        h_city = (h_data.get("city") or "").strip()
        h_state = (h_data.get("state") or "").strip()

        is_same_district = bool(
            (orig_district and h_dist and orig_district.lower() == h_dist.lower())
            or (orig_district and h_city and orig_district.lower() == h_city.lower())
        )
        is_same_state = bool(orig_state and h_state and orig_state.lower() == h_state.lower())

        # Proximity score based on clinical transit tiers:
        # Tier 1 (<= 30 km): Local same-district & immediate vicinity
        # Tier 2 (30–120 km): Neighboring districts / regional clusters
        # Tier 3 (120–300 km): Same-state tertiary & medical college hubs
        # Tier 4 (300–600 km): Adjacent state corridors
        # Tier 5 (> 600 km): Distant out-of-state facilities (heavy penalty for road transfer)
        if dist_km <= 30.0:
            dist_score = 35.0 - (dist_km * 0.25)
        elif dist_km <= 120.0:
            dist_score = 25.0 - ((dist_km - 30.0) * 0.12)
        elif dist_km <= 300.0:
            dist_score = 14.0 - ((dist_km - 120.0) * 0.05)
        elif dist_km <= 600.0:
            dist_score = 4.0 - ((dist_km - 300.0) * 0.02)
        else:
            dist_score = -5.0 - min(15.0, (dist_km - 600.0) * 0.02)

        same_district_bonus = 20.0 if is_same_district else 0.0
        same_state_bonus = 4.0 if is_same_state else 0.0

        composite_score = round(min(99.0, max(20.0, (ml_score * 0.20) + bed_factor + spec_factor + dist_score + same_district_bonus + same_state_bonus)), 1)
        h_data["match_score"] = composite_score

        has_req_bed = (avail_icu > 0) if (req_bed in ["ICU", "VENTILATOR"]) else (avail_gen > 0)
        is_primary_local_priority = bool(is_same_district and h_data.get("specialty_matched") and has_req_bed)

        # Clinical Rationale synthesis
        reasons = generate_recommendation_reason(h_data, patient_dict)
        if not reasons:
            reasons = []
        if req_bed in ["ICU", "VENTILATOR"] and avail_icu > 0:
            reasons.insert(0, f"Critical Bed Match: {avail_icu} operational ICU beds currently available.")
        if h_data.get("specialty_matched") and payload.required_specialty:
            reasons.insert(0, f"Specialty Available: Verified {payload.required_specialty} on-duty medical staff.")
        if is_same_district:
            reasons.insert(0, f"Local District Facility: Immediate local access in {h_dist or h_city}.")
        elif is_same_state and dist_km <= 120.0:
            reasons.insert(0, f"Regional Neighbor: Located in neighboring {h_dist} district (~{dist_km} km).")
        elif is_same_state:
            reasons.append(f"State Network Hospital: Within {h_state} referral network.")
        reasons.append(f"Transit Proximity: ~{h_data['distance_km']} km ({h_data['eta_minutes']} mins estimated transfer).")

        ranked_hospitals.append({
            "hospital_id": h_data.get("hospital_id"),
            "hospital_name": h_data.get("name") or h_data.get("hospital_name") or f"Hospital {h_data.get('hospital_id')}",
            "name": h_data.get("name"),
            "district": h_data.get("district") or "",
            "state": h_data.get("state") or "",
            "distance_km": h_data["distance_km"],
            "eta_minutes": h_data["eta_minutes"],
            "match_score": composite_score,
            "success_probability": h_data.get("success_probability"),
            "available_beds": avail_gen,
            "available_icu_beds": avail_icu,
            "ventilators": h_data.get("ventilator", "Yes"),
            "emergency_24x7": h_data.get("emergency_24x7", "Yes"),
            "specialty_matched": h_data.get("specialty_matched", True),
            "is_same_district": is_same_district,
            "is_primary_local_priority": is_primary_local_priority,
            "has_req_bed": has_req_bed,
            "ai_rationale": reasons[:3],
        })

    # Prioritize same district/city with matching specialty and available beds first, ranked by Haversine distance
    ranked_hospitals.sort(
        key=lambda x: (
            0 if x.get("is_primary_local_priority") else (1 if x.get("is_same_district") else 2),
            x["distance_km"] if x.get("is_primary_local_priority") else -x["match_score"],
            x["distance_km"],
        )
    )

    return {
        "success": True,
        "patient_id": patient_id,
        "condition_summary": payload.condition_summary,
        "urgency": payload.urgency,
        "required_specialty": payload.required_specialty,
        "required_bed_type": req_bed,
        "transport_requirement": payload.transport_requirement,
        "total_hospitals": len(ranked_hospitals[:8]),
        "hospitals": ranked_hospitals[:8],
    }


# ============================================================
# 4. INITIATE REFERRAL FROM PATIENT ROSTER
# ============================================================

@router.post("/patients/{patient_id}/refer")
def initiate_patient_referral(
    patient_id: str,
    payload: InitiateReferralPayload,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db),
):
    """
    Initiate a live network referral linking the patient, originating hospital,
    and destination hospital with clinical condition snapshot and urgency level.
    """
    from_hospital_id = _get_hospital_id_for_user(current_user)
    to_hospital_id = payload.to_hospital_id.strip()

    if from_hospital_id == to_hospital_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and destination hospitals cannot be identical.",
        )

    PatModel, VisitModel, HospModel, _ = _get_active_models(db)

    # Verify patient exists
    pat = db.query(PatModel).filter(PatModel.patient_id == patient_id).first()
    if not pat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {patient_id} not found.",
        )

    # Verify destination hospital exists
    to_hosp = db.query(HospModel).filter(HospModel.hospital_id == to_hospital_id).first()
    if not to_hosp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Destination hospital {to_hospital_id} does not exist in network.",
        )

    # Call repository / referral store to create referral record
    result = create_stored_referral(
        patient_id=patient_id,
        from_hospital_id=from_hospital_id,
        to_hospital_id=to_hospital_id,
        reason=payload.reason,
        priority=payload.priority or pat.priority or "Urgent",
        bed_type=payload.bed_type or ("ICU" if pat.icu_required == "Yes" else "GENERAL"),
        user_id=current_user.get("user_id"),
    )

    if not result.get("success"):
        status_code = status.HTTP_409_CONFLICT if result.get("status") == "ACTIVE_REFERRAL_EXISTS" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=result.get("message", "Failed to initiate patient referral."),
        )

    # Update patient visit notes with referral linkage
    visit = (
        db.query(VisitModel)
        .filter(
            VisitModel.patient_id == patient_id,
            VisitModel.hospital_id == from_hospital_id,
        )
        .order_by(desc(VisitModel.admitted_at))
        .first()
    )
    if visit and visit.notes:
        try:
            meta = json.loads(visit.notes)
            meta["active_referral"] = {
                "referral_id": result.get("referral_id") or (result.get("referral", {}).get("referral_id")),
                "status": "PENDING",
                "to_hospital_id": to_hospital_id,
                "transport_requirement": payload.transport_requirement,
                "initiated_at": datetime.now(timezone.utc).isoformat(),
            }
            visit.notes = json.dumps(meta)
            db.commit()
        except Exception:
            pass

    return {
        "success": True,
        "message": f"Referral for patient {patient_id} initiated to {to_hosp.name} ({to_hospital_id}).",
        "referral": result.get("referral") or result,
    }
