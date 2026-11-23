"""
FastAPI Backend
AI Powered Smart Hospital Referral System
"""

import math
from contextlib import asynccontextmanager
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware
from src.database.database import SessionLocal
from src.database.models import Hospital
from typing import Optional
from pydantic import BaseModel
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Request,
    Header,
    Query,
)
from src.auth.jwt_utils import (
    create_access_token,
    validate_production_security_config,
)
from src.auth.dependencies import (
    require_current_user,
)
from src.auth.rate_limiter import (
    check_rate_limit,
    check_login_rate_limits,
    record_failure,
    record_login_failure,
    record_success,
    record_login_success,
    revoke_token,
    is_token_revoked,
    log_security_event,
    validate_production_redis_config,
    get_rate_limiter_status,
)

from sqlalchemy.orm import Session
from src.database.db_manager import get_db_session
from src.database.pg_repository import PgReferralRepository

from src.api.schemas import (
    PatientReferralRequest,
    CreateReferralRequest,
    ReferralStatusUpdateRequest,
    BedCapacityUpdateItem,
    HospitalInventoryUpdateRequest,
    HospitalResourcesUpdateRequest,
)
from src.auth.schemas import (
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from src.auth.jwt_utils import (
    create_access_token,
)

from src.auth.auth_store import (
    authenticate_user,
)
from src.auth.authorization import (
    can_view_referral,
    can_accept_or_reject,
    can_update_referral_status,
    can_access_hospital,
)

from src.prediction.referral_engine import (
    reserve_best_hospital
)
from src.prediction.feature_builder import (
    build_referral_features
)

from src.prediction.predict import (
    predict_referral_success,
    load_model,
    MODEL_FEATURES,
)

from src.prediction.ranking_engine import (
    rank_hospitals
)
from src.prediction.recommendation import (
    generate_recommendation_reason
)

from src.utils.referral_rules import (
    evaluate_hospital_capability
)
from src.prediction.bed_reservation import (
    reserve_bed,
    confirm_reservation,
    mark_bed_occupied,
    release_bed,
    discharge_patient,
    expire_reservation,
    get_reservation,
)

from src.prediction.reservation_store import (
    get_hospital_inventory,
    load_bed_inventory,
)
from src.prediction.referral_store import (
    create_referral as create_stored_referral,
    get_referral,
    get_patient_referrals,
    update_referral_status,
    attach_reservation,
)
from src.api.patient_routes import router as patient_router
from src.api.hospital_patient_routes import router as hospital_patient_router
from src.api.admin_routes import router as admin_router
from src.api.registration_routes import router as registration_router
from src.api.observability import (
    ProductionSecurityAndLoggingMiddleware,
    get_liveness,
    get_readiness,
    get_system_metrics,
)
from src.config import get_settings, validate_production_configuration
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    validate_production_configuration()
    validate_production_security_config()
    from src.database.db_manager import validate_production_database_config
    validate_production_database_config()
    validate_production_redis_config()

    # Automatically register all ORM models and ensure all tables (including verification_tokens) exist
    from src.database.init_db import init_database
    init_database()

    yield


app = FastAPI(
    title="SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform",
    description=(
        "Production-grade Backend API for SWASTHYA SAMANVAY hospital referral, "
        "hierarchical healthcare registration, multi-tier review, and bed reservation."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Production security headers and request-id correlation middleware
app.add_middleware(ProductionSecurityAndLoggingMiddleware)

# CORS configuration with configurable origins
_app_settings = get_settings()
_cors_origins = list(_app_settings.cors_origins)
if "https://swasthya-samanvay.vercel.app" not in _cors_origins:
    _cors_origins.append("https://swasthya-samanvay.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"^https://(swasthya-samanvay.*|arogyasetu-grid.*)\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(patient_router)
app.include_router(hospital_patient_router, prefix="/api/hospital")
app.include_router(hospital_patient_router, prefix="/hospital")
app.include_router(admin_router)
app.include_router(registration_router)

# ============================================================
# HOSPITAL ACCESS AUTHORIZATION
# ============================================================

def require_hospital_access(
    hospital_id: str,
    current_user: dict
):
    """
    Ensure the authenticated user has jurisdictional authorization
    to access or manage the target hospital's resources.
    - CENTRAL_ADMIN: National access.
    - STATE_ADMIN: Hospitals within user.state.
    - DISTRICT_ADMIN: Hospitals within user.state and user.district.
    - HOSPITAL: Strictly user.hospital_id.
    """
    from src.auth.authorization import can_access_hospital
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to access "
                "this hospital resource."
            )
        )




def serialize_hospital(hospital):

    if hospital is None:
        return None

    data = (
        hospital.to_dict()
        if hasattr(hospital, "to_dict")
        else dict(hospital)
    )

    # Convert pandas NaN to None
    for key, value in data.items():

        try:
            if pd.isna(value):
                data[key] = None

        except (TypeError, ValueError):
            pass

    # Normalize boolean-like values
    boolean_fields = [
        "emergency_24x7",
        "accepts_referral",
        "ambulance",
        "oxygen_support",
        "ventilator",
        "blood_bank",
        "cardiology",
        "neurology",
        "nephrology",
        "pulmonology",
        "orthopedics",
        "general_medicine",
        "general_surgery",
        "trauma_unit",
        "burn_unit",
        "ct_scan",
        "mri",
        "xray",
        "ultrasound",
        "ecg",
        "dialysis",
        "blood_test",
        "cbc",
        "troponin_test",
        "dengue_ns1_test",
        "malaria_test",
        "blood_glucose_test",
        "hba1c_test",
        "kidney_function_test",
        "pulmonary_function_test",
        "blood_culture",
        "lactate_test",
        "stool_test",
    ]

    for field in boolean_fields:

        if field not in data:
            continue

        value = data[field]

        if value in [1, "1", True, "Yes", "yes"]:
            data[field] = "Yes"

        elif value in [0, "0", False, "No", "no"]:
            data[field] = "No"

    # Ensure success_probability is a valid float in [0.0, 1.0] or None
    raw_prob = data.get("success_probability")
    validated_prob = None
    try:
        if raw_prob is not None and not pd.isna(raw_prob):
            p = float(raw_prob)
            if not math.isnan(p) and 0.0 <= p <= 1.0:
                validated_prob = round(p, 4)
    except (TypeError, ValueError):
        validated_prob = None

    # Safe numeric distance
    raw_distance = data.get("distance_km")
    distance_km = None
    try:
        if raw_distance is not None and not pd.isna(raw_distance):
            d = float(raw_distance)
            if not math.isnan(d):
                distance_km = round(d, 2)
    except (TypeError, ValueError):
        distance_km = None

    # Safe capability matching values (normalize to 1 or 0 integers)
    def _to_match_int(v):
        if v in [1, "1", True, "Yes", "yes"]:
            return 1
        return 0

    specialty_match = _to_match_int(data.get("specialty_match"))
    test_match = _to_match_int(data.get("test_match"))
    bed_match = _to_match_int(data.get("bed_match"))
    icu_match = _to_match_int(data.get("icu_match"))

    hospital_name = data.get("name") or data.get("hospital_name") or ""
    hospital_id = data.get("hospital_id") or ""

    return {
        # Flat properties for backward compatibility and direct UI access
        "hospital_id": hospital_id,
        "hospital_name": hospital_name,
        "name": hospital_name,
        "state": data.get("state") or "",
        "district": data.get("district") or "",
        "city": data.get("city") or "",
        "latitude": data.get("latitude"),
        "longitude": data.get("longitude"),
        "distance_km": distance_km,
        "distance_zone": data.get("distance_zone") or "LOCAL",
        "total_beds": data.get("total_beds") or 0,
        "occupied_beds": data.get("occupied_beds") or 0,
        "available_beds": data.get("available_beds") or 0,
        "icu_beds": data.get("icu_beds") or 0,
        "available_icu_beds": data.get("available_icu_beds") or 0,
        "emergency_beds": data.get("emergency_beds") or 0,
        "available_emergency_beds": data.get("available_emergency_beds") or 0,
        "final_score": data.get("final_score"),
        "hospital_score": data.get("hospital_score"),
        "success_probability": validated_prob,
        "ml_probability": validated_prob,
        "occupancy_rate": data.get("occupancy_rate"),
        "rank": data.get("rank"),
        "recommendation_type": data.get("recommendation_type") or "Standard Recommendation",
        "specialty_match": specialty_match,
        "test_match": test_match,
        "bed_match": bed_match,
        "icu_match": icu_match,

        # Structured nested objects
        "hospital": {
            "hospital_id": hospital_id,
            "name": hospital_name,
            "location": {
                "state": data.get("state") or "",
                "district": data.get("district") or "",
                "city": data.get("city") or "",
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "distance_km": distance_km,
                "distance_zone": data.get("distance_zone") or "LOCAL",
            },
        },

        "beds": {
            "total_beds": data.get("total_beds") or 0,
            "occupied_beds": data.get("occupied_beds") or 0,
            "available_beds": data.get("available_beds") or 0,
            "icu_beds": data.get("icu_beds") or 0,
            "available_icu_beds": data.get("available_icu_beds") or 0,
            "emergency_beds": data.get("emergency_beds") or 0,
            "available_emergency_beds": data.get("available_emergency_beds") or 0,
        },

        "scores": {
            "final_score": data.get("final_score"),
            "hospital_score": data.get("hospital_score"),
            "success_probability": validated_prob,
            "occupancy_rate": data.get("occupancy_rate"),
        },

        "matching": {
            "specialty_match": specialty_match,
            "test_match": test_match,
            "bed_match": bed_match,
            "icu_match": icu_match,
        },

        "services": {
            "emergency_24x7": data.get("emergency_24x7"),
            "accepts_referral": data.get("accepts_referral"),
            "ambulance": data.get("ambulance"),
            "oxygen_support": data.get("oxygen_support"),
            "ventilator": data.get("ventilator"),
            "blood_bank": data.get("blood_bank"),
        },

        "departments": {
            "cardiology": data.get("cardiology"),
            "neurology": data.get("neurology"),
            "nephrology": data.get("nephrology"),
            "pulmonology": data.get("pulmonology"),
            "orthopedics": data.get("orthopedics"),
            "general_medicine": data.get("general_medicine"),
            "general_surgery": data.get("general_surgery"),
            "trauma_unit": data.get("trauma_unit"),
            "burn_unit": data.get("burn_unit"),
        },
    }


# ============================================================
# DATA
# ============================================================

PATIENTS_PATH = "datasets/final/patients.csv"
HOSPITALS_PATH = "datasets/final/hospitals.csv"


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "success": True,
        "message": (
            "SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform API is running."
        ),
        "service": "SWASTHYA SAMANVAY",
        "version": "1.0.0",
    }


# ============================================================
# HEALTH & OBSERVABILITY
# ============================================================

@app.get("/health", tags=["Observability"])
def health_check():
    return {
        "success": True,
        "status": "healthy",
    }


@app.get("/health/live", tags=["Observability"])
def health_liveness():
    """Liveness probe: returns 200 if the process is running."""
    return get_liveness()


@app.get("/health/ready", tags=["Observability"])
def health_readiness():
    """Readiness probe: validates backend dependencies (PostgreSQL, Redis, Config)."""
    res = get_readiness()
    status_code = 200 if res.get("ready") else 503
    return JSONResponse(status_code=status_code, content=res)


@app.get("/metrics", tags=["Observability"])
def system_metrics(req: Request):
    """Operational metrics: requests, latencies, outbox queue, worker stats."""
    from src.api.observability import check_metrics_access
    if not check_metrics_access(req):
        raise HTTPException(status_code=403, detail="Access to operational metrics is restricted to authorized operators.")
    return get_system_metrics()


@app.get("/admin/monitoring", tags=["Observability"])
@app.get("/api/admin/monitoring", tags=["Observability"], include_in_schema=False)
def get_admin_monitoring_dashboard(
    current_user: dict = Depends(require_current_user),
):
    """
    Protected monitoring dashboard data endpoint.
    Only accessible to CENTRAL_ADMIN role.
    Returns system metrics + alert summary. Never exposes PII.
    """
    if current_user.get("role") not in ("CENTRAL_ADMIN",):
        raise HTTPException(status_code=403, detail="Access restricted to system administrators.")
    from src.api.observability import get_system_metrics
    from src.services.alerting_service import evaluate_thresholds, get_alert_summary
    metrics = get_system_metrics()
    evaluate_thresholds(metrics)
    alert_summary = get_alert_summary()
    return {
        "system_metrics": metrics,
        "alerts": alert_summary,
        "dashboard_version": "4D-4",
        "generated_at": metrics.get("timestamp"),
    }


# ============================================================
# AUTHENTICATION
# ============================================================

def get_client_ip(req: Request) -> str:
    """Extract client IP address, honoring X-Forwarded-For when deployed behind reverse proxies."""
    forwarded = req.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if req.client and req.client.host:
        return req.client.host
    return "unknown"


@app.post(
    "/login",
    response_model=LoginResponse
)
@app.post(
    "/api/auth/login",
    response_model=LoginResponse
)
def login(request: LoginRequest, req: Request):
    client_ip = get_client_ip(req)
    raw_username = request.username.strip()
    normalized_username = raw_username.lower()
    rate_key = f"{client_ip}:{normalized_username}"

    # Dual-key rate limiting: checks both client IP and username atomically
    check_login_rate_limits(client_ip=client_ip, username=normalized_username)
    check_rate_limit(rate_key)

    user = authenticate_user(
        request.username,
        request.password
    )

    if user is None:
        record_login_failure(client_ip=client_ip, username=normalized_username)
        record_failure(rate_key)
        log_security_event("LOGIN_FAILED", {
            "ip": client_ip,
            "username": normalized_username,
            "reason": "invalid_credentials",
        })
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )

    # Successful login resets failed attempts for this IP, username, and composite key
    record_login_success(client_ip=client_ip, username=normalized_username)
    record_success(rate_key)
    log_security_event("LOGIN_SUCCESS", {
        "ip": client_ip,
        "username": normalized_username,
        "user_id": user["user_id"],
        "role": user["role"],
    })

    access_token = create_access_token(user)

    return {
        "success": True,
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "name": user["name"],
            "role": user["role"],
            "hospital_id": user.get("hospital_id"),
            "state": user.get("state"),
            "district": user.get("district"),
        },
    }


@app.post("/logout")
@app.post("/api/auth/logout")
def logout(req: Request, authorization: Optional[str] = Header(default=None)):
    """
    Invalidate the current session by placing the JWT on the distributed blocklist.
    Subsequent requests using this token will be rejected with HTTP 401.
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
            detail="Invalid authorization header."
        )

    token = parts[1]
    client_ip = get_client_ip(req)

    user_id = "unknown"
    exp_ts = None
    try:
        import jwt as pyjwt
        unverified = pyjwt.decode(token, options={"verify_signature": False})
        user_id = unverified.get("user_id") or unverified.get("sub", "unknown")
        exp_ts = unverified.get("exp")
    except Exception:
        pass

    revoke_token(token, exp_timestamp=exp_ts)
    log_security_event("LOGOUT", {
        "ip": client_ip,
        "user_id": user_id,
        "status": "revoked",
    })

    return {
        "success": True,
        "message": "Successfully logged out. Token has been revoked.",
    }


@app.get("/health/rate-limiter")
def rate_limiter_health():
    """Observability endpoint for rate limiter backend status."""
    return get_rate_limiter_status()
  


# ============================================================
# REFERRAL
# ============================================================

@app.post("/referral")
def create_referral(
    request: PatientReferralRequest
):

    # ----------------------------------------
    # Load datasets
    # ----------------------------------------

    try:

        patients = pd.read_csv(
            PATIENTS_PATH
        )

        hospitals = pd.read_csv(
            HOSPITALS_PATH
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load referral datasets: "
                f"{str(error)}"
            )
        )

    # ----------------------------------------
    # Find patient
    # ----------------------------------------

    patient_rows = patients[
        patients["patient_id"]
        == request.patient_id
    ]

    if patient_rows.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Patient {request.patient_id} "
                "not found."
            )
        )

    # ----------------------------------------
    # Convert patient to dictionary
    # ----------------------------------------

    patient = (
        patient_rows
        .iloc[0]
        .to_dict()
    )

    # ----------------------------------------
    # Run referral engine
    # ----------------------------------------

    try:

        result = reserve_best_hospital(
            patient,
            hospitals,
            hospital_id=request.hospital_id
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail={
                "message": (
                    "Referral engine failed."
                ),
                "error": str(error),
            }
        )

    # ----------------------------------------
    # Return result
    # ----------------------------------------

    return {
        "success": result["success"],
        "status": result["status"],
        "message": result.get("message"),
        "hospital": serialize_hospital(
            result.get("hospital")
        ),
        "reservation": result.get(
            "reservation"
        ),
        "attempts": result.get(
            "attempts", []
        ),
    }

# ============================================================
# RESERVE BED
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/reserve"
)
def reserve_bed_api(
    hospital_id: str,
    patient_id: str,
    bed_type: str,
    current_user: dict = Depends(
        require_current_user
    ),
):
    require_hospital_access(
    hospital_id,
    current_user
    )

    inventory = get_hospital_inventory(
        hospital_id
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    result = reserve_bed(
        hospital_id=hospital_id,
        patient_id=patient_id,
        bed_type=bed_type,
        inventory=inventory,
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": result["message"],
        "reservation": result["reservation"],
        "inventory": get_hospital_inventory(
            hospital_id
        ),
    }

# ============================================================
# EXPIRE RESERVATION
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/expire"
)
def expire_reservation_api(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    reservation = get_reservation(
        hospital_id,
        patient_id
    )

    if reservation is None:

        raise HTTPException(
            status_code=404,
            detail="Reservation not found."
        )

    inventory = get_hospital_inventory(
        hospital_id
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    result = expire_reservation(
        hospital_id=hospital_id,
        patient_id=patient_id,
        inventory=inventory,
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": "Reservation expired successfully.",
        "reservation": result["reservation"],
        "inventory": inventory,
    }


# ============================================================
# GET RESERVATION
# ============================================================

@app.get(
    "/reservation/{hospital_id}/{patient_id}"
)
def get_reservation_status(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    reservation = get_reservation(
        hospital_id,
        patient_id
    )

    if reservation is None:

        raise HTTPException(
            status_code=404,
            detail="Reservation not found."
        )

    return {
        "success": True,
        "status": reservation["status"],
        "reservation": reservation,
    }


# ============================================================
# MARK BED OCCUPIED
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/occupy"
)
def occupy_bed_api(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    result = mark_bed_occupied(
        hospital_id=hospital_id,
        patient_id=patient_id,
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": "Bed marked as occupied successfully.",
        "reservation": result["reservation"],
    }


# ============================================================
# CONFIRM RESERVATION
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/confirm"
)
def confirm_reservation_api(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    inventory = get_hospital_inventory(
        hospital_id
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    result = confirm_reservation(
        hospital_id,
        patient_id,
        inventory
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": "Reservation confirmed successfully.",
        "reservation": result["reservation"],
        "inventory": get_hospital_inventory(
            hospital_id
        ),
    }


# ============================================================
# RELEASE RESERVATION
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/release"
)
def release_reservation_api(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    reservation = get_reservation(
        hospital_id,
        patient_id
    )

    if reservation is None:

        raise HTTPException(
            status_code=404,
            detail="Reservation not found."
        )

    inventory = get_hospital_inventory(
        hospital_id
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    result = release_bed(
        hospital_id=hospital_id,
        patient_id=patient_id,
        inventory=inventory,
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": "Reservation released successfully.",
        "reservation": result["reservation"],
        "inventory": get_hospital_inventory(
            hospital_id
        ),
    }

# ============================================================
# DISCHARGE PATIENT
# ============================================================

@app.post(
    "/reservation/{hospital_id}/{patient_id}/discharge"
)
def discharge_patient_api(
    hospital_id: str,
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

    require_hospital_access(hospital_id, current_user)

    inventory = get_hospital_inventory(
        hospital_id
    )

    if inventory is None:

        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    result = discharge_patient(
        hospital_id=hospital_id,
        patient_id=patient_id,
        inventory=inventory,
    )

    if not result["success"]:

        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result["status"],
        "message": "Patient discharged successfully.",
        "reservation": result["reservation"],
        "inventory": get_hospital_inventory(
            hospital_id
        ),
    }



# ============================================================
# HOSPITAL DASHBOARD INVENTORY & BED MANAGEMENT (PHASE 4A)
# ============================================================

@app.get("/hospitals/{hospital_id}/inventory")
def get_hospital_dashboard_inventory(
    hospital_id: str,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db_session),
):
    # ----------------------------------------
    # Geographic role authorization check
    # ----------------------------------------
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to access this hospital inventory."
        )

    # ----------------------------------------
    # 1. Authoritative Load from PostgreSQL
    # ----------------------------------------
    inventory = None
    try:
        repo = PgReferralRepository(db)
        inventory = repo.get_hospital_inventory(hospital_id)
    except Exception:
        inventory = None

    # ----------------------------------------
    # 2. Fallback to legacy JSON store for test mocks if not found in PG
    # ----------------------------------------
    if inventory is None:
        inventory = get_hospital_inventory(hospital_id)

    if inventory is None:
        raise HTTPException(
            status_code=404,
            detail="Hospital inventory not found."
        )

    return {
        "success": True,
        "hospital_id": hospital_id,
        "inventory": inventory,
        "available_beds": inventory.get("available_beds", 0),
        "available_icu_beds": inventory.get("available_icu_beds", 0),
        "reserved_beds": inventory.get("reserved_beds", 0),
        "reserved_icu_beds": inventory.get("reserved_icu_beds", 0),
    }


@app.put("/hospitals/{hospital_id}/inventory")
def update_hospital_inventory_endpoint(
    hospital_id: str,
    payload: HospitalInventoryUpdateRequest,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db_session),
):
    """
    Atomically updates hospital bed capacity in PostgreSQL.
    Enforces role-based permissions, hospital scoping, and capacity invariants.
    """
    role = current_user.get("role")
    if role not in ("HOSPITAL", "DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
        raise HTTPException(status_code=403, detail="Unauthorized role for modifying hospital inventory.")

    if role == "HOSPITAL" and current_user.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=403, detail="Hospital administrators can only update their own inventory.")

    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(status_code=403, detail="You are not authorized for this hospital's jurisdiction.")

    items_to_update = []
    if payload.capacities:
        items_to_update.extend(payload.capacities)
    elif payload.bed_type is not None and payload.total_capacity is not None:
        items_to_update.append(BedCapacityUpdateItem(bed_type=payload.bed_type, total_capacity=payload.total_capacity))
    else:
        raise HTTPException(
            status_code=422,
            detail="Must provide either (bed_type and total_capacity) or a list of capacities."
        )

    repo = PgReferralRepository(db)
    user_id = current_user.get("user_id") or current_user.get("username")
    latest_inventory = None

    try:
        for item in items_to_update:
            latest_inventory = repo.update_hospital_bed_capacity(
                hospital_id=hospital_id,
                bed_type=item.bed_type,
                total_capacity=item.total_capacity,
                user_id=user_id,
            )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=422, detail=err_msg)

    return {
        "success": True,
        "message": "Hospital bed inventory updated successfully.",
        "hospital_id": hospital_id,
        "inventory": latest_inventory,
    }


@app.patch("/hospitals/{hospital_id}/resources")
def update_hospital_resources_endpoint(
    hospital_id: str,
    payload: HospitalResourcesUpdateRequest,
    current_user: dict = Depends(require_current_user),
    db: Session = Depends(get_db_session),
):
    """
    Updates hospital support resources (oxygen, ventilator, ambulance, etc.) in PostgreSQL.
    """
    role = current_user.get("role")
    if role not in ("HOSPITAL", "DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
        raise HTTPException(status_code=403, detail="Unauthorized role for modifying hospital resources.")

    if role == "HOSPITAL" and current_user.get("hospital_id") != hospital_id:
        raise HTTPException(status_code=403, detail="Hospital administrators can only update their own resources.")

    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(status_code=403, detail="You are not authorized for this hospital's jurisdiction.")

    resource_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not resource_data:
        raise HTTPException(status_code=422, detail="No resource fields provided for update.")

    repo = PgReferralRepository(db)
    user_id = current_user.get("user_id") or current_user.get("username")

    try:
        updated_inventory = repo.update_hospital_resources(
            hospital_id=hospital_id,
            resources=resource_data,
            user_id=user_id,
        )
    except ValueError as e:
        err_msg = str(e)
        if "not found" in err_msg.lower():
            raise HTTPException(status_code=404, detail=err_msg)
        raise HTTPException(status_code=422, detail=err_msg)

    return {
        "success": True,
        "message": "Hospital resources updated successfully.",
        "hospital_id": hospital_id,
        "inventory": updated_inventory,
    }


# ============================================================
# RANKED HOSPITALS
# ============================================================

_PATIENTS_CACHE: dict[str, dict] | None = None
_HOSPITALS_CACHE: list[dict] | None = None


def get_cached_patient(patient_id: str) -> dict | None:
    global _PATIENTS_CACHE
    if _PATIENTS_CACHE is None:
        try:
            df = pd.read_csv(PATIENTS_PATH)
            _PATIENTS_CACHE = {
                str(row["patient_id"]).strip(): row.to_dict()
                for _, row in df.iterrows()
            }
        except Exception:
            _PATIENTS_CACHE = {}

    pat = _PATIENTS_CACHE.get(patient_id)
    if pat is not None:
        return pat

    # Database fallback for dynamically admitted inpatients
    try:
        from src.database.database import SessionLocal
        db = SessionLocal()
        try:
            from src.database.models import Patient as SqlitePatient
            db_pat = db.query(SqlitePatient).filter(SqlitePatient.patient_id == patient_id).first()
            if db_pat:
                return {
                    "patient_id": db_pat.patient_id,
                    "name": db_pat.name,
                    "age": db_pat.age,
                    "gender": db_pat.gender,
                    "disease": db_pat.disease,
                    "priority": db_pat.priority,
                    "icu_required": getattr(db_pat, "icu_required", "No"),
                    "ambulance_required": getattr(db_pat, "ambulance_required", "No"),
                    "referral_required": getattr(db_pat, "referral_required", "Yes"),
                    "spo2": getattr(db_pat, "spo2", 98),
                    "systolic_bp": getattr(db_pat, "systolic_bp", 120),
                    "diastolic_bp": getattr(db_pat, "diastolic_bp", 80),
                    "heart_rate": getattr(db_pat, "heart_rate", 75),
                    "respiratory_rate": getattr(db_pat, "respiratory_rate", 18),
                    "temperature": getattr(db_pat, "temperature", 98.6),
                    "state": getattr(db_pat, "state", "Punjab"),
                    "district": getattr(db_pat, "district", "Amritsar"),
                    "latitude": getattr(db_pat, "latitude", 31.634),
                    "longitude": getattr(db_pat, "longitude", 74.872),
                }
        finally:
            db.close()
    except Exception:
        pass

    try:
        from src.database.db_manager import is_postgres, get_session_factory
        if is_postgres():
            from src.database.pg_models import Patient as PgPatient
            session = get_session_factory()()
            try:
                db_pat = session.query(PgPatient).filter(PgPatient.patient_id == patient_id).first()
                if db_pat:
                    return {
                        "patient_id": db_pat.patient_id,
                        "name": db_pat.name,
                        "age": db_pat.age,
                        "gender": db_pat.gender,
                        "disease": db_pat.disease,
                        "priority": db_pat.priority,
                        "icu_required": db_pat.icu_required,
                        "ambulance_required": db_pat.ambulance_required,
                        "referral_required": db_pat.referral_required,
                        "spo2": db_pat.spo2 or 98,
                        "systolic_bp": db_pat.systolic_bp or 120,
                        "diastolic_bp": db_pat.diastolic_bp or 80,
                        "heart_rate": db_pat.heart_rate or 75,
                        "respiratory_rate": db_pat.respiratory_rate or 18,
                        "temperature": db_pat.temperature or 98.6,
                        "state": db_pat.state or "Punjab",
                        "district": db_pat.district or "Amritsar",
                        "latitude": db_pat.latitude or 31.634,
                        "longitude": db_pat.longitude or 74.872,
                    }
            finally:
                session.close()
    except Exception:
        pass

    return None


def get_cached_hospitals() -> list[dict]:
    global _HOSPITALS_CACHE
    if _HOSPITALS_CACHE is None:
        db = SessionLocal()
        try:
            records = db.query(Hospital).all()
            _HOSPITALS_CACHE = [
                {
                    column.name: getattr(hospital, column.name)
                    for column in Hospital.__table__.columns
                }
                for hospital in records
            ]
        finally:
            db.close()
    return _HOSPITALS_CACHE


@app.get("/hospitals")
def get_ranked_hospitals(
    patient_id: str
):
    if not patient_id or not patient_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Patient ID is required."
        )
    patient_id = patient_id.strip()

    # ----------------------------------------
    # Find patient
    # ----------------------------------------
    patient = get_cached_patient(patient_id)

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Patient {patient_id} "
                "not found."
            )
        )

    # ----------------------------------------
    # Referral required check
    # ----------------------------------------
    if patient.get("referral_required") != "Yes":
        return {
            "success": True,
            "patient_id": patient_id,
            "priority": patient.get("priority", "Stable"),
            "total_hospitals": 0,
            "referral_required": patient.get("referral_required", "No"),
            "message": "Hospital referral is not clinically required for this patient.",
            "reason": "Patient condition is evaluated as manageable locally without hospital transfer.",
            "hospitals": [],
        }

    # ----------------------------------------
    # Load hospitals reference data
    # ----------------------------------------
    hospitals_base = get_cached_hospitals()
    if not hospitals_base:
        raise HTTPException(
            status_code=404,
            detail="No hospitals found in database."
        )

    # ----------------------------------------
    # Load live bed inventory ONCE outside loop
    # (Eliminates repeated disk reads / JSON deserialization)
    # ----------------------------------------
    inventory_map = load_bed_inventory()

    eligible_hospitals = []
    feature_rows = []
    disease = patient.get("disease")
    priority = patient.get("priority")

    # ----------------------------------------
    # Build eligible hospitals & vector features
    # ----------------------------------------
    for h_base in hospitals_base:
        hospital = h_base.copy()

        # Apply live inventory counters in memory
        inv = inventory_map.get(hospital["hospital_id"])
        if inv is not None:
            beds = inv.get("beds", {})
            hospital["available_beds"] = sum(
                s == "AVAILABLE" for b, s in beds.items() if b.startswith("GENERAL")
            )
            hospital["available_icu_beds"] = sum(
                s == "AVAILABLE" for b, s in beds.items() if b.startswith("ICU")
            )
            hospital["available_emergency_beds"] = inv.get(
                "available_emergency_beds", hospital.get("available_emergency_beds", 0)
            )

        capability = evaluate_hospital_capability(
            patient,
            hospital
        )

        if not capability["eligible"]:
            continue

        features = build_referral_features(
            patient,
            hospital
        )

        hospital_data = hospital.copy()
        hospital_data.update(features)
        eligible_hospitals.append(hospital_data)

        # Assemble feature row for single-pass batch inference
        row = features.copy()
        for feat in MODEL_FEATURES:
            if feat.startswith("disease_"):
                row[feat] = int(disease == feat[len("disease_"):])
            elif feat.startswith("priority_"):
                row[feat] = int(priority == feat[len("priority_"):])
        feature_rows.append(row)

    # ----------------------------------------
    # No eligible hospital
    # ----------------------------------------
    if not eligible_hospitals:
        return {
            "success": True,
            "patient_id": patient_id,
            "priority": patient.get("priority", "Standard"),
            "total_hospitals": 0,
            "disqualified_hospitals_count": len(hospitals_base),
            "referral_required": patient.get("referral_required", "Yes"),
            "message": "No eligible hospitals found matching patient clinical requirements.",
            "reason": "All evaluated facilities either lack required specialties/tests, have zero matching beds, or do not accept external referrals.",
            "hospitals": [],
        }

    # ----------------------------------------
    # High-Performance Batch ML Prediction
    # ----------------------------------------
    model = load_model()
    batch_X = pd.DataFrame(feature_rows, columns=MODEL_FEATURES)
    probabilities = model.predict_proba(batch_X)

    for i, h_data in enumerate(eligible_hospitals):
        prob = float(probabilities[i][1])
        if math.isnan(prob) or not (0.0 <= prob <= 1.0):
            h_data["success_probability"] = None
            h_data["ml_prediction"] = 0
        else:
            prob = round(prob, 4)
            h_data["success_probability"] = prob
            h_data["ml_prediction"] = int(prob >= 0.5)

    # ----------------------------------------
    # Rank hospitals
    # ----------------------------------------
    eligible_df = pd.DataFrame(eligible_hospitals)
    ranked = rank_hospitals(
        eligible_df,
        patient["priority"]
    )
    ranked = ranked.head(10)

    # ----------------------------------------
    # Serialization
    # ----------------------------------------
    hospitals_response = []
    for _, hospital in ranked.iterrows():
        hospital_data = hospital.to_dict()
        serialized = serialize_hospital(hospital_data)

        try:
            serialized["reasons"] = generate_recommendation_reason(
                hospital_data,
                patient
            )
        except Exception:
            serialized["reasons"] = []

        hospitals_response.append(serialized)

    return {
        "success": True,
        "patient_id": patient_id,
        "priority": patient.get("priority", "Standard"),
        "total_hospitals": len(hospitals_response),
        "disqualified_hospitals_count": len(hospitals_base) - len(eligible_hospitals),
        "referral_required": patient.get("referral_required", "Yes"),
        "message": f"Found {len(hospitals_response)} eligible hospital(s) ranked by clinical capability and AI scoring.",
        "ai_disclaimer": (
            "AI recommendation is an assistive decision-support model based on proximity, "
            "live bed availability, and specialty matching. It is not an autonomous medical certification."
        ),
        "hospitals": hospitals_response,
    }


# ============================================================
# LIVE HOSPITAL REFERRAL
# ============================================================

@app.post("/referrals")
def create_live_referral(
    request: CreateReferralRequest,
    current_user: Optional[dict] = Depends(require_current_user),
):
    # Role authorization: Hospital accounts can only initiate or record referrals involving their hospital
    if current_user and current_user.get("role") == "HOSPITAL":
        user_hosp = current_user.get("hospital_id")
        if user_hosp not in [request.from_hospital_id, request.to_hospital_id]:
            raise HTTPException(
                status_code=403,
                detail="Hospital users are only authorized to initiate or record referrals involving their own hospital.",
            )

    if request.from_hospital_id == request.to_hospital_id:
        raise HTTPException(
            status_code=400,
            detail="Source and destination hospitals cannot be identical.",
        )

    result = create_stored_referral(
        patient_id=request.patient_id,
        from_hospital_id=request.from_hospital_id,
        to_hospital_id=request.to_hospital_id,
        reason=request.reason,
        priority=request.priority,
        bed_type=request.bed_type,
        user_id=current_user.get("user_id") if current_user else None,
    )

    if not result.get("success"):
        status_code = 409 if result.get("status") == "ACTIVE_REFERRAL_EXISTS" else 400
        raise HTTPException(
            status_code=status_code,
            detail=result.get("message", "Referral creation failed."),
        )

    return result


# ============================================================
# GET REFERRAL
# ============================================================

@app.get("/referrals/{referral_id}")
def get_live_referral(
    referral_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):
    referral = get_referral(
        referral_id
    )

    if referral is None:
        raise HTTPException(
            status_code=404,
            detail="Referral not found."
        )

    if not can_view_referral(
        current_user,
        referral
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to view this referral."
        )

    return {
        "success": True,
        "referral": referral,
    }


# ============================================================
# PATIENT REFERRAL HISTORY
# ============================================================

@app.get("/patients/{patient_id}/referrals")
def get_patient_referral_history(
    patient_id: str,
    current_user: dict = Depends(
        require_current_user
    ),
):
    if not patient_id or not patient_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Patient ID is required."
        )

    patient_id = patient_id.strip()

    # Verify patient exists in system (CSV, SQLite DB, or runtime referrals)
    patient_exists = False
    try:
        patients = pd.read_csv(PATIENTS_PATH)
        patient_exists = not patients[patients["patient_id"] == patient_id].empty
    except Exception:
        pass

    if not patient_exists:
        from src.database.database import SessionLocal
        from src.database.models import Patient
        db = SessionLocal()
        try:
            db_pat = db.query(Patient).filter(Patient.patient_id == patient_id).first()
            if db_pat is not None:
                patient_exists = True
        finally:
            db.close()

    referrals = get_patient_referrals(
        patient_id
    )

    if referrals:
        patient_exists = True

    if not patient_exists:
        raise HTTPException(
            status_code=404,
            detail=f"Patient {patient_id} not found."
        )

    # Filter referrals according to the logged-in user's permissions.
    authorized_referrals = [
        referral
        for referral in referrals
        if can_view_referral(
            current_user,
            referral
        )
    ]

    scope_restricted = len(referrals) > 0 and len(authorized_referrals) == 0

    if scope_restricted:
        message = (
            "Referral records exist for this patient, but they are restricted "
            "to the originating or destination hospital."
        )
    elif len(authorized_referrals) == 0:
        message = "No referral records exist for this patient."
    else:
        message = f"Found {len(authorized_referrals)} authorized referral record(s)."

    return {
        "success": True,
        "patient_id": patient_id,
        "total_referrals": len(
            authorized_referrals
        ),
        "total_system_referrals": len(referrals),
        "scope_restricted": scope_restricted,
        "message": message,
        "referrals": authorized_referrals,
    }


# ============================================================
# HOSPITAL REFERRAL INBOX & OUTBOX
# ============================================================

@app.get("/hospitals/{hospital_id}/referrals")
def get_hospital_referrals(
    hospital_id: str,
    scope: str = Query(default="incoming", pattern="^(incoming|outgoing|all)$"),
    current_user: dict = Depends(
        require_current_user
    ),
):
    from src.prediction.referral_store import _load_referrals
    from src.database.db_manager import is_postgres, get_referral_repository

    # Geographic role authorization check
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(
            status_code=403,
            detail=(
                "You are not authorized to view referrals "
                "for this hospital."
            ),
        )

    if is_postgres():
        try:
            repo = get_referral_repository()
            db_referrals = repo.get_hospital_referrals(hospital_id, scope=scope)
            authorized = [r for r in db_referrals if can_view_referral(current_user, r)]
            return {
                "success": True,
                "hospital_id": hospital_id,
                "scope": scope,
                "total_referrals": len(authorized),
                "referrals": authorized,
            }
        except Exception:
            pass

    stored_referrals = _load_referrals()

    hid = hospital_id.strip().lower()
    if scope == "outgoing":
        hospital_referrals = [
            referral
            for referral in stored_referrals
            if str(referral.get("from_hospital_id") or "").strip().lower() == hid
            and can_view_referral(current_user, referral)
        ]
    elif scope == "all":
        hospital_referrals = [
            referral
            for referral in stored_referrals
            if (
                str(referral.get("to_hospital_id") or "").strip().lower() == hid
                or str(referral.get("from_hospital_id") or "").strip().lower() == hid
            )
            and can_view_referral(current_user, referral)
        ]
    else:
        hospital_referrals = [
            referral
            for referral in stored_referrals
            if str(referral.get("to_hospital_id") or "").strip().lower() == hid
            and can_view_referral(current_user, referral)
        ]

    return {
        "success": True,
        "hospital_id": hospital_id,
        "scope": scope,
        "total_referrals": len(hospital_referrals),
        "referrals": hospital_referrals,
    }


# ============================================================
# UPDATE REFERRAL STATUS
# ============================================================

@app.post("/referrals/{referral_id}/status/{new_status}")
def update_live_referral_status(
    referral_id: str,
    new_status: str,
    body: Optional[ReferralStatusUpdateRequest] = None,
    current_user: dict = Depends(
        require_current_user
    ),
):

    new_status = new_status.upper().strip()
    if new_status == "IN_TREATMENT":
        new_status = "TREATMENT_ACTIVE"

    allowed_statuses = [
        "ACCEPTED",
        "REJECTED",
        "IN_TRANSIT",
        "ARRIVED",
        "TREATMENT_ACTIVE",
        "IN_TREATMENT",
        "COMPLETED",
        "DISCHARGED",
        "TRANSFERRED",
        "DIED",
    ]

    if new_status not in allowed_statuses:

        raise HTTPException(
            status_code=400,
            detail={
                "message":
                    "Invalid referral status.",
                "allowed_statuses":
                    allowed_statuses,
            }
        )

    # ----------------------------------------
    # Get referral
    # ----------------------------------------

    referral = get_referral(
        referral_id
    )

    if referral is None:

        raise HTTPException(
            status_code=404,
            detail="Referral not found."
        )

    # ----------------------------------------
    # Authorization rules
    # ----------------------------------------

    role = current_user.get("role")
    hospital_id = current_user.get("hospital_id")

    if role != "HOSPITAL":
        raise HTTPException(
            status_code=403,
            detail="Administrative roles cannot execute clinical referral transitions."
        )

    if not can_update_referral_status(current_user, referral, new_status):
        if new_status in ["ACCEPTED", "REJECTED"]:
            detail = "Only the destination hospital can accept or reject this referral."
        elif new_status == "IN_TRANSIT":
            detail = "Only the source hospital can mark this referral as in transit."
        else:
            detail = "Only the destination hospital can update this referral status."
        raise HTTPException(
            status_code=403,
            detail=detail,
        )

    # ----------------------------------------
    # Update referral status
    # ----------------------------------------

    result = update_referral_status(
        referral_id=referral_id,
        new_status=new_status,
        notes=body.notes if body else None,
        ambulance_id=body.ambulance_id if body else None,
        eta_minutes=body.eta_minutes if body else None,
        user_id=current_user.get("user_id"),
    )

    if not result["success"]:

        status_code = (
            404
            if result["status"] == "NOT_FOUND"
            else 409
        )

        raise HTTPException(
            status_code=status_code,
            detail=result,
        )

    # ----------------------------------------
    # Include reservation details in response
    # ----------------------------------------

    response = dict(result)

    referral_data = result.get("referral", {})

    response["reservation"] = {
        "reservation_status": referral_data.get(
            "reservation_status"
        ),
        "bed_id": referral_data.get("bed_id"),
        "bed_type": referral_data.get("bed_type"),
        "reservation_hospital_id": referral_data.get(
            "reservation_hospital_id"
        ),
        "auto_reservation": referral_data.get(
            "auto_reservation"
        ),
        "reservation_message": referral_data.get(
            "reservation_message"
        ),
    }

    return response


class ReferralPatchStatusRequest(BaseModel):
    status: str
    notes: Optional[str] = None
    ambulance_id: Optional[str] = None
    eta_minutes: Optional[int] = None
    reason: Optional[str] = None


@app.patch("/referrals/{referral_id}/status")
def patch_referral_status(
    referral_id: str,
    payload: ReferralPatchStatusRequest,
    current_user: dict = Depends(require_current_user),
):
    body = ReferralStatusUpdateRequest(
        notes=payload.notes,
        ambulance_id=payload.ambulance_id,
        eta_minutes=payload.eta_minutes,
        reason=payload.reason,
    )
    return update_live_referral_status(
        referral_id=referral_id,
        new_status=payload.status,
        body=body,
        current_user=current_user,
    )


# ============================================================
# IN-APP NOTIFICATIONS
# ============================================================

@app.get("/hospitals/{hospital_id}/notifications")
def get_notifications_endpoint(
    hospital_id: str,
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    current_user: dict = Depends(require_current_user),
):
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(status_code=403, detail="Unauthorized to view notifications for this hospital.")
    from src.prediction.notification_store import get_hospital_notifications
    return get_hospital_notifications(
        hospital_id,
        unread_only=unread_only,
        limit=limit,
        page=page,
        page_size=page_size,
        event_category=category,
    )


@app.post("/hospitals/{hospital_id}/notifications/{notification_id}/read")
def mark_notification_read_endpoint(
    hospital_id: str,
    notification_id: int,
    current_user: dict = Depends(require_current_user),
):
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(status_code=403, detail="Unauthorized.")
    from src.prediction.notification_store import mark_notification_as_read
    success = mark_notification_as_read(notification_id, hospital_id)
    return {"success": success}


@app.post("/hospitals/{hospital_id}/notifications/read-all")
def mark_all_notifications_read_endpoint(
    hospital_id: str,
    current_user: dict = Depends(require_current_user),
):
    if not can_access_hospital(current_user, hospital_id):
        raise HTTPException(status_code=403, detail="Unauthorized.")
    from src.prediction.notification_store import mark_all_notifications_read
    count = mark_all_notifications_read(hospital_id)
    return {"success": True, "marked_read": count}


@app.get("/notifications/me")
def get_my_notifications_endpoint(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    page_size: Optional[int] = Query(default=None, ge=1, le=100),
    category: Optional[str] = Query(default=None),
    current_user: dict = Depends(require_current_user),
):
    """
    Unified notification endpoint for the authenticated user based on role / hospital.
    """
    from src.database.db_manager import is_postgres, get_referral_repository
    if is_postgres():
        repo = get_referral_repository()
        return repo.get_user_notifications(
            user=current_user,
            unread_only=unread_only,
            limit=limit,
            page=page,
            page_size=page_size,
            event_category=category,
        )
    hosp_id = current_user.get("hospital_id")
    if hosp_id:
        from src.prediction.notification_store import get_hospital_notifications
        return get_hospital_notifications(
            hosp_id,
            unread_only=unread_only,
            limit=limit,
            page=page,
            page_size=page_size,
            event_category=category,
        )
    return {"user_id": current_user.get("user_id"), "unread_count": 0, "total_returned": 0, "notifications": []}


@app.post("/notifications/{notification_id}/read")
def mark_user_notification_read_endpoint(
    notification_id: str,
    current_user: dict = Depends(require_current_user),
):
    """Mark a notification as read for current authenticated user."""
    from src.database.db_manager import is_postgres, get_referral_repository
    if is_postgres():
        repo = get_referral_repository()
        success = repo.mark_user_notification_as_read(notification_id, current_user)
        return {"success": success}
    hosp_id = current_user.get("hospital_id")
    if hosp_id:
        from src.prediction.notification_store import mark_notification_as_read
        try:
            nid = int(notification_id)
        except ValueError:
            return {"success": False}
        return {"success": mark_notification_as_read(nid, hosp_id)}
    return {"success": False}


@app.post("/notifications/read-all")
def mark_all_user_notifications_read_endpoint(
    current_user: dict = Depends(require_current_user),
):
    """Mark all notifications as read for current authenticated user."""
    from src.database.db_manager import is_postgres, get_referral_repository
    if is_postgres():
        repo = get_referral_repository()
        count = repo.mark_all_user_notifications_read(current_user)
        return {"success": True, "marked_read": count}
    hosp_id = current_user.get("hospital_id")
    if hosp_id:
        from src.prediction.notification_store import mark_all_notifications_read
        count = mark_all_notifications_read(hosp_id)
        return {"success": True, "marked_read": count}
    return {"success": True, "marked_read": 0}


# ============================================================
# ATTACH BED RESERVATION TO REFERRAL
# ============================================================

@app.post("/referrals/{referral_id}/reservation")
def attach_referral_reservation(
    referral_id: str,
    hospital_id: str,
    bed_type: str,
    current_user: dict = Depends(
        require_current_user
    ),
):

        # ----------------------------------------
    # Authorization
    # ----------------------------------------

    referral = get_referral(
        referral_id
    )

    if referral is None:
        raise HTTPException(
            status_code=404,
            detail="Referral not found."
        )

    if current_user["role"] == "HOSPITAL":

        if current_user.get(
            "hospital_id"
        ) != referral["to_hospital_id"]:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Only the destination hospital can "
                    "attach a bed reservation."
                )
            )

    elif current_user["role"] == "STATE_ADMIN":
        from src.auth.authorization import can_access_hospital
        if not can_access_hospital(current_user, referral["to_hospital_id"]):
            raise HTTPException(
                status_code=403,
                detail=(
                    "You are not authorized to attach a reservation for "
                    "a hospital outside your state jurisdiction."
                )
            )

    elif current_user["role"] != "CENTRAL_ADMIN":

        raise HTTPException(
            status_code=403,
            detail="You are not authorized to attach a reservation."
        )

    if hospital_id != referral["to_hospital_id"]:
        raise HTTPException(
            status_code=403,
            detail=(
                "Reservation can only be attached "
                "to the destination hospital."
            )
        )

    bed_type = bed_type.upper()

    if bed_type not in [
        "GENERAL",
        "ICU"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid bed type."
        )

    reservation = get_reservation(
        hospital_id,
        get_referral(
            referral_id
        )["patient_id"]
        if get_referral(referral_id)
        else ""
    )

    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail="Active reservation not found."
        )

    if reservation["bed_type"] != bed_type:
        raise HTTPException(
            status_code=409,
            detail="Bed type does not match reservation."
        )

    result = attach_reservation(
        referral_id=referral_id,
        hospital_id=hospital_id,
        bed_type=bed_type,
    )

    if not result["success"]:
        raise HTTPException(
            status_code=404,
            detail=result
        )

    return result