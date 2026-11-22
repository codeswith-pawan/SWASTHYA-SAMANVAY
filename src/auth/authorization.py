from functools import lru_cache

HOSPITAL = "HOSPITAL"
DISTRICT_ADMIN = "DISTRICT_ADMIN"
STATE_ADMIN = "STATE_ADMIN"
CENTRAL_ADMIN = "CENTRAL_ADMIN"

ALL_ROLES = {HOSPITAL, DISTRICT_ADMIN, STATE_ADMIN, CENTRAL_ADMIN}

_GEO_CACHE: dict[str, dict] = {}


def get_hospital_geo(hospital_id: str) -> dict | None:
    """
    Look up state and district for a given hospital_id.
    Checks PostgreSQL primary database first, with fallback to SQLite master records.
    Uses an in-memory cache for fast lookups.
    """
    if not hospital_id:
        return None

    if hospital_id in _GEO_CACHE:
        return _GEO_CACHE[hospital_id]

    # 1. Try PostgreSQL master/provisioned hospital records
    try:
        from src.database.db_manager import get_session_factory
        from src.database.pg_models import Hospital as PgHospital

        factory = get_session_factory()
        session = factory()
        try:
            record = session.query(PgHospital).filter(PgHospital.hospital_id == hospital_id).first()
            if record:
                geo = {
                    "hospital_id": record.hospital_id,
                    "name": record.name,
                    "state": record.state,
                    "district": record.district,
                    "city": record.city,
                }
                _GEO_CACHE[hospital_id] = geo
                return geo
        finally:
            session.close()
    except Exception:
        pass

    # 2. Fallback to SQLite hospital records
    try:
        from src.database.database import SessionLocal
        from src.database.models import Hospital

        db = SessionLocal()
        try:
            record = (
                db.query(Hospital)
                .filter(Hospital.hospital_id == hospital_id)
                .first()
            )
            if record:
                geo = {
                    "hospital_id": record.hospital_id,
                    "name": record.name,
                    "state": record.state,
                    "district": record.district,
                    "city": record.city,
                }
                _GEO_CACHE[hospital_id] = geo
                return geo
        finally:
            db.close()
    except Exception:
        pass

    return None


def can_access_hospital(user: dict, hospital_id: str, hospital_info: dict | None = None) -> bool:
    """
    Validate whether the authenticated user has geographic permission
    to view/manage the target hospital.

    Hierarchy:
    - CENTRAL_ADMIN: Global national access.
    - STATE_ADMIN: Limited to hospitals within user.state.
    - DISTRICT_ADMIN: Limited to hospitals within user.state and user.district.
    - HOSPITAL: Limited strictly to user.hospital_id.
    """
    if not user or "role" not in user:
        return False

    role = user["role"]

    if role == CENTRAL_ADMIN:
        return True

    if role == HOSPITAL:
        u_hid = str(user.get("hospital_id") or "").strip().lower()
        t_hid = str(hospital_id or "").strip().lower()
        return bool(u_hid and u_hid == t_hid)

    # For district or state admins, fetch hospital geo metadata if not provided
    geo = hospital_info or get_hospital_geo(hospital_id)
    if not geo:
        # If hospital metadata not found, reject access for regional admins
        return False

    h_state = geo.get("state")
    h_district = geo.get("district")

    if role == STATE_ADMIN:
        user_state = user.get("state")
        return bool(user_state and h_state and user_state.lower() == h_state.lower())

    if role == DISTRICT_ADMIN:
        user_state = user.get("state")
        user_district = user.get("district")
        return bool(
            user_state
            and user_district
            and h_state
            and h_district
            and user_state.lower() == h_state.lower()
            and user_district.lower() == h_district.lower()
        )

    return False


def can_view_referral(user: dict, referral: dict) -> bool:
    """
    Check whether a logged-in user can view a referral based on role and geography.
    """
    if not user or not referral:
        return False

    role = user.get("role")

    # Central admin can view all referrals (aggregate / tracking)
    if role == CENTRAL_ADMIN:
        return True

    # Hospital users can only view referrals where they are the sender or receiver
    if role == HOSPITAL:
        h_id = user.get("hospital_id")
        if not h_id:
            return False
        h_id_lower = str(h_id).lower()
        from_id = str(referral.get("from_hospital_id") or "").lower()
        to_id = str(referral.get("to_hospital_id") or "").lower()
        return h_id_lower in (from_id, to_id)

    # For regional admins, inspect states and districts of both source and destination
    from_geo = {
        "state": referral.get("from_state"),
        "district": referral.get("from_district"),
    }
    if not from_geo["state"]:
        from_lookup = get_hospital_geo(referral.get("from_hospital_id"))
        if from_lookup:
            from_geo = from_lookup

    to_geo = {
        "state": referral.get("to_state"),
        "district": referral.get("to_district"),
    }
    if not to_geo["state"]:
        to_lookup = get_hospital_geo(referral.get("to_hospital_id"))
        if to_lookup:
            to_geo = to_lookup

    u_state = user.get("state")
    u_district = user.get("district")

    if role == STATE_ADMIN:
        if not u_state:
            return False
        u_state_l = u_state.lower()
        from_matches = bool(
            from_geo.get("state") and from_geo["state"].lower() == u_state_l
        )
        to_matches = bool(
            to_geo.get("state") and to_geo["state"].lower() == u_state_l
        )
        return from_matches or to_matches

    if role == DISTRICT_ADMIN:
        if not u_state or not u_district:
            return False
        u_state_l = u_state.lower()
        u_district_l = u_district.lower()

        from_matches = bool(
            from_geo.get("state")
            and from_geo.get("district")
            and from_geo["state"].lower() == u_state_l
            and from_geo["district"].lower() == u_district_l
        )
        to_matches = bool(
            to_geo.get("state")
            and to_geo.get("district")
            and to_geo["state"].lower() == u_state_l
            and to_geo["district"].lower() == u_district_l
        )
        return from_matches or to_matches

    return False


def can_accept_or_reject(user: dict, referral: dict) -> bool:
    """
    Only the receiving hospital can accept or reject a pending referral.
    Administrative roles cannot make clinical acceptance decisions.
    """
    if user.get("role") != HOSPITAL:
        return False

    return (
        referral.get("to_hospital_id") == user.get("hospital_id")
        and referral.get("status") == "PENDING"
    )


def can_update_referral_status(user: dict, referral: dict, new_status: str | None = None) -> bool:
    """
    Only the directly involved hospitals can update a referral status.
    State, District, and Central administrators cannot perform clinical transitions.

    Role breakdown:
    - Source Hospital:
        - can trigger 'IN_TRANSIT' once referral is ACCEPTED.
        - can cancel a PENDING referral.
    - Destination Hospital:
        - can transition to 'ACCEPTED' or 'REJECTED' when PENDING.
        - can transition to 'ARRIVED' when IN_TRANSIT.
        - can transition to 'TREATMENT_ACTIVE' when ARRIVED.
        - can transition to 'COMPLETED' or 'DISCHARGED' when TREATMENT_ACTIVE.
        - can transition to terminal outcomes 'TRANSFERRED' or 'DIED'.
    """
    if user.get("role") != HOSPITAL:
        return False

    hospital_id = str(user.get("hospital_id") or "").strip().lower()
    from_id = str(referral.get("from_hospital_id") or "").strip().lower()
    to_id = str(referral.get("to_hospital_id") or "").strip().lower()
    is_source = bool(hospital_id and hospital_id == from_id)
    is_destination = bool(hospital_id and hospital_id == to_id)

    if not is_source and not is_destination:
        return False

    if new_status is None:
        return True

    current_status = str(referral.get("status") or "").upper().strip()
    new_status = str(new_status).upper().strip()

    # Source hospital permissions
    if is_source:
        if new_status == "IN_TRANSIT":
            return current_status in ("ACCEPTED", "ACCEPTED_AND_RESERVED")
        if new_status == "CANCELLED":
            return current_status == "PENDING"
        # Source hospital cannot accept, reject, arrive, treat, or complete
        return False

    # Destination hospital permissions
    if is_destination:
        if new_status in ("ACCEPTED", "REJECTED"):
            return current_status == "PENDING"
        if new_status == "ARRIVED":
            return current_status in ("IN_TRANSIT", "ACCEPTED", "ACCEPTED_AND_RESERVED")
        if new_status in ("TREATMENT_ACTIVE", "IN_TREATMENT"):
            return current_status in ("ARRIVED", "ACCEPTED", "IN_TRANSIT")
        if new_status in ("COMPLETED", "DISCHARGED"):
            return current_status in ("TREATMENT_ACTIVE", "IN_TREATMENT", "ARRIVED")
        if new_status in ("TRANSFERRED", "DIED"):
            return current_status in ("ARRIVED", "TREATMENT_ACTIVE", "IN_TREATMENT", "ACCEPTED")

    return False


def can_access_patient(user: dict, patient_id: str, db=None) -> bool:
    """
    Check whether a user has geographic and clinical authorization to view
    a specific patient's confidential health record.

    Access Rules:
    - CENTRAL_ADMIN: Global national authorization.
    - STATE_ADMIN: Allowed if patient has any visit or referral in user.state.
    - DISTRICT_ADMIN: Allowed if patient has any visit or referral in user.state and user.district.
    - HOSPITAL: Allowed if:
        1. Patient has a past or current visit at user.hospital_id, OR
        2. Patient has an active or past referral where user.hospital_id is from_hospital_id or to_hospital_id.
    """
    if not user or "role" not in user:
        return False

    role = user.get("role")
    if role == CENTRAL_ADMIN:
        return True

    visits = []
    if db is not None:
        try:
            from src.database.models import HospitalVisit
            visits = db.query(HospitalVisit).filter(HospitalVisit.patient_id == patient_id).all()
        except Exception:
            visits = []

    referrals = []
    try:
        from src.prediction.referral_store import load_referrals
        all_refs = load_referrals()
        referrals = [r for r in all_refs if r.get("patient_id") == patient_id]
    except Exception:
        referrals = []

    if role == HOSPITAL:
        h_id = user.get("hospital_id")
        if not h_id:
            return False
        if any(v.hospital_id == h_id for v in visits):
            return True
        if any(r.get("from_hospital_id") == h_id or r.get("to_hospital_id") == h_id for r in referrals):
            return True
        return False

    u_state = (user.get("state") or "").lower()
    u_district = (user.get("district") or "").lower()

    if role == STATE_ADMIN:
        if not u_state:
            return False
        for v in visits:
            geo = get_hospital_geo(v.hospital_id)
            if geo and (geo.get("state") or "").lower() == u_state:
                return True
        for r in referrals:
            from_st = (r.get("from_state") or "").lower()
            to_st = (r.get("to_state") or "").lower()
            if from_st == u_state or to_st == u_state:
                return True
        return False

    if role == DISTRICT_ADMIN:
        if not u_state or not u_district:
            return False
        for v in visits:
            geo = get_hospital_geo(v.hospital_id)
            if (
                geo
                and (geo.get("state") or "").lower() == u_state
                and (geo.get("district") or "").lower() == u_district
            ):
                return True
        for r in referrals:
            from_st = (r.get("from_state") or "").lower()
            from_dt = (r.get("from_district") or "").lower()
            to_st = (r.get("to_state") or "").lower()
            to_dt = (r.get("to_district") or "").lower()
            if (from_st == u_state and from_dt == u_district) or (to_st == u_state and to_dt == u_district):
                return True
        return False

    return False

