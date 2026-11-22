"""
Production Referral Feature Builder
AI Powered Smart Hospital Referral System
"""

import pandas as pd

from src.utils.helpers import calculate_distance_km

from src.utils.referral_rules import (
    check_test_availability,
    check_specialty_availability,
)


def build_referral_features(patient, hospital):
    """
    Build referral features from a patient-hospital pair.

    This uses the same business logic that was used
    while generating the historical referral dataset.
    """

    # --------------------------------
    # Distance
    # --------------------------------

    try:
        raw_plat = patient.get("latitude")
        raw_plon = patient.get("longitude")
        raw_hlat = hospital.get("latitude")
        raw_hlon = hospital.get("longitude")

        import math
        plat = float(raw_plat) if raw_plat is not None else float("nan")
        plon = float(raw_plon) if raw_plon is not None else float("nan")
        hlat = float(raw_hlat) if raw_hlat is not None else float("nan")
        hlon = float(raw_hlon) if raw_hlon is not None else float("nan")

        if (
            math.isnan(plat)
            or math.isnan(plon)
            or math.isnan(hlat)
            or math.isnan(hlon)
        ):
            distance_km = 50.0
        else:
            distance_km = calculate_distance_km(
                plat,
                plon,
                hlat,
                hlon,
            )
    except (TypeError, ValueError, KeyError):
        distance_km = 50.0

    # --------------------------------
    # Test Match
    # --------------------------------

    test_result = check_test_availability(
        patient,
        hospital,
    )

    test_match = (
        1
        if test_result.get("all_available")
        else 0
    )

    # --------------------------------
    # Specialty Match
    # --------------------------------

    specialty_result = check_specialty_availability(
        patient,
        hospital,
    )

    specialty_match = (
        1
        if specialty_result.get("all_available")
        else 0
    )

    # --------------------------------
    # ICU Match
    # --------------------------------

    if patient.get("icu_required") == "Yes":

        icu_match = (
            1
            if (hospital.get("available_icu_beds") or 0) > 0
            else 0
        )

    else:

        icu_match = 1

    # --------------------------------
    # Bed Match
    # --------------------------------

    if patient.get("priority") == "Critical":

        bed_match = (
            1
            if (hospital.get("available_emergency_beds") or 0) > 0
            else 0
        )

    else:

        bed_match = (
            1
            if (hospital.get("available_beds") or 0) > 0
            else 0
        )

    # --------------------------------
    # Occupancy Rate
    # --------------------------------

    total_beds = hospital.get("total_beds") or 0
    occupied_beds = hospital.get("occupied_beds")
    if occupied_beds is None:
        avail = hospital.get("available_beds")
        occupied_beds = max(0, total_beds - (avail or 0)) if avail is not None else 0

    occupancy_rate = (
        occupied_beds / total_beds
        if total_beds > 0
        else 1.0
    )

    # --------------------------------
    # Hospital Capabilities
    # --------------------------------

    emergency_24x7 = (
        1
        if hospital["emergency_24x7"] == "Yes"
        else 0
    )

    ambulance = (
        1
        if hospital["ambulance"] == "Yes"
        else 0
    )

    oxygen_support = (
        1
        if hospital["oxygen_support"] == "Yes"
        else 0
    )

    ventilator = (
        1
        if hospital["ventilator"] == "Yes"
        else 0
    )

    blood_bank = (
        1
        if hospital["blood_bank"] == "Yes"
        else 0
    )

    # --------------------------------
    # Return
    # --------------------------------

    return {
        "distance_km": distance_km,

        "available_beds":
            hospital["available_beds"],

        "available_icu_beds":
            hospital["available_icu_beds"],

        "occupancy_rate":
            round(occupancy_rate, 3),

        "specialty_match":
            specialty_match,

        "test_match":
            test_match,

        "bed_match":
            bed_match,

        "icu_match":
            icu_match,

        "emergency_24x7":
            emergency_24x7,

        "ambulance":
            ambulance,

        "oxygen_support":
            oxygen_support,

        "ventilator":
            ventilator,

        "blood_bank":
            blood_bank,
    }