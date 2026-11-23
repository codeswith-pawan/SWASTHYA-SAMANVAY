#!/usr/bin/env python3
"""
Regional Hospital Network Seeder for SIH Hospital AI.
Seeds realistic multi-district hospital networks across all 38 districts of Bihar
and major Indian states into `sih_hospital_local_preview`.
Provisions temporary hospital login credentials (Hospital@123) for end-to-end referral testing.

CRITICAL SAFETY DIRECTIVE:
NEVER touch `sih_hospital_dev`. This script strictly targets `sih_hospital_local_preview`.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import psycopg2
from psycopg2.extras import execute_values
from src.auth.auth_store import hash_password

DEFAULT_PREVIEW_URL = "postgresql://localhost:5432/sih_hospital_local_preview"
DEFAULT_PASSWORD = "Hospital@123"


def get_target_db_url() -> str:
    url = (
        os.getenv("PREVIEW_DATABASE_URL")
        or os.getenv("TARGET_DATABASE_URL")
        or os.getenv("SEED_DATABASE_URL")
        or DEFAULT_PREVIEW_URL
    )
    # Strict safety assertions
    if "sih_hospital_dev" in url:
        raise RuntimeError(
            "CRITICAL SAFETY VIOLATION: Refusing to seed `sih_hospital_dev`! "
            "Never target the core development database."
        )
    if "local_preview" not in url and not os.getenv("ALLOW_SEED_DEPLOYMENT"):
        raise RuntimeError(
            f"CRITICAL SAFETY VIOLATION: Database URL must target a local preview database or explicitly set ALLOW_SEED_DEPLOYMENT=1, got: {url}"
        )
    return url


# ==============================================================================
# HOSPITAL DEFINITIONS
# ==============================================================================

# Common specialty presets
TERTIARY_SPECIALTIES = {
    "cardiology": "Yes",
    "neurology": "Yes",
    "nephrology": "Yes",
    "pulmonology": "Yes",
    "orthopedics": "Yes",
    "general_medicine": "Yes",
    "general_surgery": "Yes",
    "trauma_unit": "Yes",
    "burn_unit": "Yes",
    "ct_scan": "Yes",
    "mri": "Yes",
    "xray": "Yes",
    "ultrasound": "Yes",
    "ecg": "Yes",
    "dialysis": "Yes",
    "blood_test": "Yes",
    "cbc": "Yes",
    "troponin_test": "Yes",
    "dengue_ns1_test": "Yes",
    "malaria_test": "Yes",
    "blood_glucose_test": "Yes",
    "hba1c_test": "Yes",
    "kidney_function_test": "Yes",
    "pulmonary_function_test": "Yes",
    "blood_culture": "Yes",
    "lactate_test": "Yes",
    "stool_test": "Yes",
}

DISTRICT_SPECIALTIES = {
    "cardiology": "Yes",
    "neurology": "No",
    "nephrology": "No",
    "pulmonology": "Yes",
    "orthopedics": "Yes",
    "general_medicine": "Yes",
    "general_surgery": "Yes",
    "trauma_unit": "Yes",
    "burn_unit": "No",
    "ct_scan": "Yes",
    "mri": "No",
    "xray": "Yes",
    "ultrasound": "Yes",
    "ecg": "Yes",
    "dialysis": "Yes",
    "blood_test": "Yes",
    "cbc": "Yes",
    "troponin_test": "Yes",
    "dengue_ns1_test": "Yes",
    "malaria_test": "Yes",
    "blood_glucose_test": "Yes",
    "hba1c_test": "Yes",
    "kidney_function_test": "Yes",
    "pulmonary_function_test": "No",
    "blood_culture": "Yes",
    "lactate_test": "No",
    "stool_test": "Yes",
}

SUPER_SPECIALTY_EXTRA = {
    **TERTIARY_SPECIALTIES,
    "dialysis": "Yes",
    "ct_scan": "Yes",
    "mri": "Yes",
}


def build_hospitals_data() -> List[Dict[str, Any]]:
    hospitals = []

    # --------------------------------------------------------------------------
    # 1. BIHAR — ALL 38 DISTRICTS
    # --------------------------------------------------------------------------

    # PURNIA (Origin District: at least 3-4 realistic hospitals)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_PUR_01",
            "name": "Purnia Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Purnia",
            "city": "Purnia",
            "latitude": 25.7802,
            "longitude": 87.4721,
            "total_beds": 180,
            "available_beds": 65,
            "icu_beds": 24,
            "available_icu_beds": 10,
            "emergency_beds": 20,
            "available_emergency_beds": 8,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_PUR_02",
            "name": "Purnia Super Specialty & Trauma Centre",
            "tier": "SUPER_SPECIALTY",
            "state": "Bihar",
            "district": "Purnia",
            "city": "Purnia",
            "latitude": 25.7850,
            "longitude": 87.4850,
            "total_beds": 250,
            "available_beds": 95,
            "icu_beds": 40,
            "available_icu_beds": 18,
            "emergency_beds": 25,
            "available_emergency_beds": 12,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_BIH_PUR_03",
            "name": "Katihar-Purnia Border Critical Care Hospital",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Purnia",
            "city": "Kasba",
            "latitude": 25.7100,
            "longitude": 87.5200,
            "total_beds": 120,
            "available_beds": 45,
            "icu_beds": 18,
            "available_icu_beds": 8,
            "emergency_beds": 15,
            "available_emergency_beds": 6,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_PUR_04",
            "name": "Max Care Emergency Hospital Purnia",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Purnia",
            "city": "Purnia",
            "latitude": 25.7720,
            "longitude": 87.4690,
            "total_beds": 90,
            "available_beds": 35,
            "icu_beds": 14,
            "available_icu_beds": 6,
            "emergency_beds": 12,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # SEEMANCHAL & KOSI IMMEDIATE NEIGHBORS (at least 2 hospitals each)
    # Katihar (~35 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_KTR_01",
            "name": "Katihar Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Katihar",
            "city": "Katihar",
            "latitude": 25.5420,
            "longitude": 87.5680,
            "total_beds": 160,
            "available_beds": 55,
            "icu_beds": 20,
            "available_icu_beds": 8,
            "emergency_beds": 15,
            "available_emergency_beds": 6,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_KTR_02",
            "name": "Katihar Medical College & Hospital",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Katihar",
            "city": "Katihar",
            "latitude": 25.5580,
            "longitude": 87.5850,
            "total_beds": 400,
            "available_beds": 140,
            "icu_beds": 50,
            "available_icu_beds": 22,
            "emergency_beds": 30,
            "available_emergency_beds": 14,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Araria (~45 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_ARA_01",
            "name": "Araria District Sadar Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Araria",
            "city": "Araria",
            "latitude": 26.1500,
            "longitude": 87.5150,
            "total_beds": 140,
            "available_beds": 48,
            "icu_beds": 16,
            "available_icu_beds": 6,
            "emergency_beds": 15,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_ARA_02",
            "name": "Forbesganj Sub-Divisional Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Araria",
            "city": "Forbesganj",
            "latitude": 26.3020,
            "longitude": 87.2600,
            "total_beds": 100,
            "available_beds": 38,
            "icu_beds": 12,
            "available_icu_beds": 4,
            "emergency_beds": 12,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Kishanganj (~60 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_KSG_01",
            "name": "Kishanganj Sadar Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Kishanganj",
            "city": "Kishanganj",
            "latitude": 26.0740,
            "longitude": 87.9430,
            "total_beds": 130,
            "available_beds": 42,
            "icu_beds": 14,
            "available_icu_beds": 5,
            "emergency_beds": 12,
            "available_emergency_beds": 4,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_KSG_02",
            "name": "MGM Medical College & LSK Hospital",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Kishanganj",
            "city": "Kishanganj",
            "latitude": 26.1020,
            "longitude": 87.9620,
            "total_beds": 450,
            "available_beds": 150,
            "icu_beds": 55,
            "available_icu_beds": 20,
            "emergency_beds": 35,
            "available_emergency_beds": 15,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Madhepura (~75 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_MDP_01",
            "name": "Jannayak Karpoori Thakur Medical College & Hospital",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Madhepura",
            "city": "Madhepura",
            "latitude": 25.9350,
            "longitude": 86.8020,
            "total_beds": 350,
            "available_beds": 120,
            "icu_beds": 45,
            "available_icu_beds": 18,
            "emergency_beds": 25,
            "available_emergency_beds": 10,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_MDP_02",
            "name": "Madhepura Sadar Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Madhepura",
            "city": "Madhepura",
            "latitude": 25.9210,
            "longitude": 86.7890,
            "total_beds": 120,
            "available_beds": 40,
            "icu_beds": 12,
            "available_icu_beds": 5,
            "emergency_beds": 12,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Saharsa (~85 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_SHS_01",
            "name": "Saharsa Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Saharsa",
            "city": "Saharsa",
            "latitude": 25.8820,
            "longitude": 86.5950,
            "total_beds": 150,
            "available_beds": 50,
            "icu_beds": 18,
            "available_icu_beds": 7,
            "emergency_beds": 15,
            "available_emergency_beds": 6,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_SHS_02",
            "name": "Lord Buddha Koshi Medical College & Hospital",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Saharsa",
            "city": "Baijnathpur",
            "latitude": 25.8710,
            "longitude": 86.6120,
            "total_beds": 300,
            "available_beds": 110,
            "icu_beds": 35,
            "available_icu_beds": 14,
            "emergency_beds": 20,
            "available_emergency_beds": 8,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Supaul (~95 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_SPL_01",
            "name": "Supaul Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Supaul",
            "city": "Supaul",
            "latitude": 26.1240,
            "longitude": 86.6020,
            "total_beds": 130,
            "available_beds": 45,
            "icu_beds": 14,
            "available_icu_beds": 5,
            "emergency_beds": 12,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_SPL_02",
            "name": "Birpur Sub-Divisional Hospital Supaul",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Supaul",
            "city": "Birpur",
            "latitude": 26.5180,
            "longitude": 87.0150,
            "total_beds": 90,
            "available_beds": 32,
            "icu_beds": 10,
            "available_icu_beds": 4,
            "emergency_beds": 10,
            "available_emergency_beds": 4,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Bhagalpur (~90 km across Ganga)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_BGP_01",
            "name": "Jawaharlal Nehru Medical College & Hospital (JLNMCH)",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Bhagalpur",
            "city": "Bhagalpur",
            "latitude": 25.2510,
            "longitude": 86.9920,
            "total_beds": 600,
            "available_beds": 180,
            "icu_beds": 70,
            "available_icu_beds": 28,
            "emergency_beds": 40,
            "available_emergency_beds": 16,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_BGP_02",
            "name": "Bhagalpur Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Bhagalpur",
            "city": "Bhagalpur",
            "latitude": 25.2410,
            "longitude": 86.9810,
            "total_beds": 150,
            "available_beds": 50,
            "icu_beds": 18,
            "available_icu_beds": 6,
            "emergency_beds": 15,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # ALL REMAINING BIHAR DISTRICTS (Covering all 38 districts of Bihar)
    # Patna (Capital & Apex Medical Hub ~270 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_PAT_01",
            "name": "AIIMS Patna",
            "tier": "SUPER_SPECIALTY",
            "state": "Bihar",
            "district": "Patna",
            "city": "Patna",
            "latitude": 25.5615,
            "longitude": 85.0445,
            "total_beds": 960,
            "available_beds": 280,
            "icu_beds": 120,
            "available_icu_beds": 45,
            "emergency_beds": 60,
            "available_emergency_beds": 25,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_BIH_PAT_02",
            "name": "Patna Medical College & Hospital (PMCH)",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Patna",
            "city": "Patna",
            "latitude": 25.6200,
            "longitude": 85.1580,
            "total_beds": 850,
            "available_beds": 220,
            "icu_beds": 95,
            "available_icu_beds": 35,
            "emergency_beds": 50,
            "available_emergency_beds": 20,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_PAT_03",
            "name": "Indira Gandhi Institute of Medical Sciences (IGIMS)",
            "tier": "SUPER_SPECIALTY",
            "state": "Bihar",
            "district": "Patna",
            "city": "Patna",
            "latitude": 25.6110,
            "longitude": 85.0880,
            "total_beds": 750,
            "available_beds": 210,
            "icu_beds": 85,
            "available_icu_beds": 30,
            "emergency_beds": 45,
            "available_emergency_beds": 18,
            **SUPER_SPECIALTY_EXTRA,
        },
    ])

    # Muzaffarpur (~220 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_MUZ_01",
            "name": "Sri Krishna Medical College & Hospital (SKMCH)",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Muzaffarpur",
            "city": "Muzaffarpur",
            "latitude": 26.1520,
            "longitude": 85.3950,
            "total_beds": 550,
            "available_beds": 160,
            "icu_beds": 60,
            "available_icu_beds": 22,
            "emergency_beds": 35,
            "available_emergency_beds": 14,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_MUZ_02",
            "name": "Muzaffarpur Sadar Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Muzaffarpur",
            "city": "Muzaffarpur",
            "latitude": 26.1180,
            "longitude": 85.3620,
            "total_beds": 160,
            "available_beds": 55,
            "icu_beds": 20,
            "available_icu_beds": 7,
            "emergency_beds": 15,
            "available_emergency_beds": 6,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Darbhanga (~170 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_DBG_01",
            "name": "Darbhanga Medical College & Hospital (DMCH)",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Darbhanga",
            "city": "Darbhanga",
            "latitude": 26.1480,
            "longitude": 85.9020,
            "total_beds": 650,
            "available_beds": 190,
            "icu_beds": 65,
            "available_icu_beds": 25,
            "emergency_beds": 40,
            "available_emergency_beds": 15,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_DBG_02",
            "name": "Darbhanga Sadar District Hospital",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Darbhanga",
            "city": "Darbhanga",
            "latitude": 26.1520,
            "longitude": 85.8890,
            "total_beds": 150,
            "available_beds": 50,
            "icu_beds": 18,
            "available_icu_beds": 6,
            "emergency_beds": 15,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Gaya (~290 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_GAY_01",
            "name": "Anugrah Narayan Magadh Medical College & Hospital (ANMMCH)",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Gaya",
            "city": "Gaya",
            "latitude": 24.7820,
            "longitude": 84.9750,
            "total_beds": 500,
            "available_beds": 150,
            "icu_beds": 55,
            "available_icu_beds": 20,
            "emergency_beds": 30,
            "available_emergency_beds": 12,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_GAY_02",
            "name": "Jayprakash Narayan Sadar Hospital Gaya",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Gaya",
            "city": "Gaya",
            "latitude": 24.7940,
            "longitude": 85.0010,
            "total_beds": 160,
            "available_beds": 55,
            "icu_beds": 20,
            "available_icu_beds": 8,
            "emergency_beds": 15,
            "available_emergency_beds": 6,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Nalanda / Bihar Sharif (~230 km)
    hospitals.extend([
        {
            "hospital_id": "GH_BIH_NAL_01",
            "name": "Vardhman Institute of Medical Sciences (VIMS) Pawapuri",
            "tier": "TERTIARY",
            "state": "Bihar",
            "district": "Nalanda",
            "city": "Pawapuri",
            "latitude": 25.0920,
            "longitude": 85.5280,
            "total_beds": 450,
            "available_beds": 140,
            "icu_beds": 48,
            "available_icu_beds": 18,
            "emergency_beds": 25,
            "available_emergency_beds": 10,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_BIH_NAL_02",
            "name": "Bihar Sharif Sadar Hospital Nalanda",
            "tier": "DISTRICT",
            "state": "Bihar",
            "district": "Nalanda",
            "city": "Bihar Sharif",
            "latitude": 25.2010,
            "longitude": 85.5200,
            "total_beds": 150,
            "available_beds": 50,
            "icu_beds": 16,
            "available_icu_beds": 6,
            "emergency_beds": 15,
            "available_emergency_beds": 5,
            **DISTRICT_SPECIALTIES,
        },
    ])

    # Begusarai (~150 km)
    hospitals.append({
        "hospital_id": "GH_BIH_BGS_01",
        "name": "Begusarai Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Begusarai",
        "city": "Begusarai",
        "latitude": 25.4200,
        "longitude": 86.1300,
        "total_beds": 180,
        "available_beds": 60,
        "icu_beds": 22,
        "available_icu_beds": 8,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # Rohtas / Sasaram (~360 km)
    hospitals.append({
        "hospital_id": "GH_BIH_ROH_01",
        "name": "Sasaram Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Rohtas",
        "city": "Sasaram",
        "latitude": 24.9520,
        "longitude": 84.0190,
        "total_beds": 150,
        "available_beds": 50,
        "icu_beds": 18,
        "available_icu_beds": 6,
        "emergency_beds": 15,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Saran / Chhapra (~280 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SAR_01",
        "name": "Chhapra Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Saran",
        "city": "Chhapra",
        "latitude": 25.7810,
        "longitude": 84.7520,
        "total_beds": 160,
        "available_beds": 52,
        "icu_beds": 18,
        "available_icu_beds": 7,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # East Champaran / Motihari (~270 km)
    hospitals.append({
        "hospital_id": "GH_BIH_ECH_01",
        "name": "Motihari Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "East Champaran",
        "city": "Motihari",
        "latitude": 26.6490,
        "longitude": 84.9120,
        "total_beds": 170,
        "available_beds": 58,
        "icu_beds": 20,
        "available_icu_beds": 8,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # West Champaran / Bettiah (~310 km)
    hospitals.append({
        "hospital_id": "GH_BIH_WCH_01",
        "name": "Government Medical College & Hospital Bettiah",
        "tier": "TERTIARY",
        "state": "Bihar",
        "district": "West Champaran",
        "city": "Bettiah",
        "latitude": 26.8040,
        "longitude": 84.5060,
        "total_beds": 350,
        "available_beds": 115,
        "icu_beds": 40,
        "available_icu_beds": 15,
        "emergency_beds": 25,
        "available_emergency_beds": 10,
        **TERTIARY_SPECIALTIES,
    })

    # Bhojpur / Ara (~290 km)
    hospitals.append({
        "hospital_id": "GH_BIH_BHO_01",
        "name": "Ara Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Bhojpur",
        "city": "Ara",
        "latitude": 25.5580,
        "longitude": 84.6620,
        "total_beds": 150,
        "available_beds": 48,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Buxar (~350 km)
    hospitals.append({
        "hospital_id": "GH_BIH_BUX_01",
        "name": "Buxar Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Buxar",
        "city": "Buxar",
        "latitude": 25.5660,
        "longitude": 83.9800,
        "total_beds": 130,
        "available_beds": 44,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Gopalganj (~320 km)
    hospitals.append({
        "hospital_id": "GH_BIH_GOP_01",
        "name": "Gopalganj Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Gopalganj",
        "city": "Gopalganj",
        "latitude": 26.4700,
        "longitude": 84.4460,
        "total_beds": 140,
        "available_beds": 46,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Siwan (~310 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SIW_01",
        "name": "Siwan Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Siwan",
        "city": "Siwan",
        "latitude": 26.2210,
        "longitude": 84.3590,
        "total_beds": 150,
        "available_beds": 50,
        "icu_beds": 18,
        "available_icu_beds": 7,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # Vaishali / Hajipur (~260 km)
    hospitals.append({
        "hospital_id": "GH_BIH_VAI_01",
        "name": "Hajipur Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Vaishali",
        "city": "Hajipur",
        "latitude": 25.6870,
        "longitude": 85.2170,
        "total_beds": 160,
        "available_beds": 54,
        "icu_beds": 18,
        "available_icu_beds": 7,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # Samastipur (~190 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SAM_01",
        "name": "Samastipur Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Samastipur",
        "city": "Samastipur",
        "latitude": 25.8640,
        "longitude": 85.7830,
        "total_beds": 160,
        "available_beds": 52,
        "icu_beds": 18,
        "available_icu_beds": 7,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # Madhubani (~160 km)
    hospitals.append({
        "hospital_id": "GH_BIH_MAD_01",
        "name": "Madhubani Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Madhubani",
        "city": "Madhubani",
        "latitude": 26.3560,
        "longitude": 86.0740,
        "total_beds": 150,
        "available_beds": 48,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Sitamarhi (~220 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SIT_01",
        "name": "Sitamarhi Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Sitamarhi",
        "city": "Sitamarhi",
        "latitude": 26.6000,
        "longitude": 85.4900,
        "total_beds": 140,
        "available_beds": 45,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Sheohar (~230 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SHE_01",
        "name": "Sheohar Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Sheohar",
        "city": "Sheohar",
        "latitude": 26.5180,
        "longitude": 85.2970,
        "total_beds": 100,
        "available_beds": 35,
        "icu_beds": 10,
        "available_icu_beds": 4,
        "emergency_beds": 10,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Khagaria (~110 km)
    hospitals.append({
        "hospital_id": "GH_BIH_KHA_01",
        "name": "Khagaria Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Khagaria",
        "city": "Khagaria",
        "latitude": 25.5050,
        "longitude": 86.4840,
        "total_beds": 130,
        "available_beds": 44,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Munger (~115 km)
    hospitals.append({
        "hospital_id": "GH_BIH_MUN_01",
        "name": "Munger Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Munger",
        "city": "Munger",
        "latitude": 25.3770,
        "longitude": 86.4760,
        "total_beds": 160,
        "available_beds": 52,
        "icu_beds": 18,
        "available_icu_beds": 7,
        "emergency_beds": 15,
        "available_emergency_beds": 6,
        **DISTRICT_SPECIALTIES,
    })

    # Jamui (~150 km)
    hospitals.append({
        "hospital_id": "GH_BIH_JAM_01",
        "name": "Jamui Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Jamui",
        "city": "Jamui",
        "latitude": 24.9220,
        "longitude": 86.2230,
        "total_beds": 140,
        "available_beds": 46,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Lakhisarai (~150 km)
    hospitals.append({
        "hospital_id": "GH_BIH_LAK_01",
        "name": "Lakhisarai Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Lakhisarai",
        "city": "Lakhisarai",
        "latitude": 25.1780,
        "longitude": 86.0960,
        "total_beds": 130,
        "available_beds": 42,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Sheikhpura (~170 km)
    hospitals.append({
        "hospital_id": "GH_BIH_SHK_01",
        "name": "Sheikhpura Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Sheikhpura",
        "city": "Sheikhpura",
        "latitude": 25.1400,
        "longitude": 85.8650,
        "total_beds": 110,
        "available_beds": 38,
        "icu_beds": 12,
        "available_icu_beds": 4,
        "emergency_beds": 10,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Nawada (~220 km)
    hospitals.append({
        "hospital_id": "GH_BIH_NAW_01",
        "name": "Nawada Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Nawada",
        "city": "Nawada",
        "latitude": 24.8890,
        "longitude": 85.5450,
        "total_beds": 140,
        "available_beds": 46,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Aurangabad (~340 km)
    hospitals.append({
        "hospital_id": "GH_BIH_AUR_01",
        "name": "Aurangabad Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Aurangabad",
        "city": "Aurangabad",
        "latitude": 24.7560,
        "longitude": 84.3770,
        "total_beds": 150,
        "available_beds": 48,
        "icu_beds": 16,
        "available_icu_beds": 6,
        "emergency_beds": 14,
        "available_emergency_beds": 5,
        **DISTRICT_SPECIALTIES,
    })

    # Jehanabad (~260 km)
    hospitals.append({
        "hospital_id": "GH_BIH_JEH_01",
        "name": "Jehanabad Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Jehanabad",
        "city": "Jehanabad",
        "latitude": 25.2160,
        "longitude": 84.9890,
        "total_beds": 130,
        "available_beds": 42,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Arwal (~280 km)
    hospitals.append({
        "hospital_id": "GH_BIH_ARW_01",
        "name": "Arwal Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Arwal",
        "city": "Arwal",
        "latitude": 25.2460,
        "longitude": 84.6750,
        "total_beds": 100,
        "available_beds": 35,
        "icu_beds": 10,
        "available_icu_beds": 4,
        "emergency_beds": 10,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Banka (~120 km)
    hospitals.append({
        "hospital_id": "GH_BIH_BNK_01",
        "name": "Banka Sadar District Hospital",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Banka",
        "city": "Banka",
        "latitude": 24.8890,
        "longitude": 86.9250,
        "total_beds": 120,
        "available_beds": 40,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # Kaimur / Bhabua (~400 km)
    hospitals.append({
        "hospital_id": "GH_BIH_KMR_01",
        "name": "Bhabua Sadar District Hospital Kaimur",
        "tier": "DISTRICT",
        "state": "Bihar",
        "district": "Kaimur",
        "city": "Bhabua",
        "latitude": 25.0460,
        "longitude": 83.6160,
        "total_beds": 130,
        "available_beds": 42,
        "icu_beds": 14,
        "available_icu_beds": 5,
        "emergency_beds": 12,
        "available_emergency_beds": 4,
        **DISTRICT_SPECIALTIES,
    })

    # --------------------------------------------------------------------------
    # 2. MAJOR INDIAN STATES COVERAGE (2-4 major hospitals per state)
    # --------------------------------------------------------------------------

    # Jharkhand
    hospitals.extend([
        {
            "hospital_id": "GH_JHK_RNC_01",
            "name": "Rajendra Institute of Medical Sciences (RIMS) Ranchi",
            "tier": "TERTIARY",
            "state": "Jharkhand",
            "district": "Ranchi",
            "city": "Ranchi",
            "latitude": 23.3720,
            "longitude": 85.3440,
            "total_beds": 800,
            "available_beds": 240,
            "icu_beds": 80,
            "available_icu_beds": 30,
            "emergency_beds": 50,
            "available_emergency_beds": 18,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_JHK_JMS_01",
            "name": "MGM Medical College & Hospital Jamshedpur",
            "tier": "TERTIARY",
            "state": "Jharkhand",
            "district": "East Singhbhum",
            "city": "Jamshedpur",
            "latitude": 22.8046,
            "longitude": 86.2029,
            "total_beds": 450,
            "available_beds": 130,
            "icu_beds": 45,
            "available_icu_beds": 16,
            "emergency_beds": 25,
            "available_emergency_beds": 10,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_JHK_DHN_01",
            "name": "SNMMCH Dhanbad",
            "tier": "DISTRICT",
            "state": "Jharkhand",
            "district": "Dhanbad",
            "city": "Dhanbad",
            "latitude": 23.8140,
            "longitude": 86.4320,
            "total_beds": 350,
            "available_beds": 105,
            "icu_beds": 35,
            "available_icu_beds": 12,
            "emergency_beds": 20,
            "available_emergency_beds": 8,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_JHK_DGH_01",
            "name": "AIIMS Deoghar",
            "tier": "SUPER_SPECIALTY",
            "state": "Jharkhand",
            "district": "Deoghar",
            "city": "Deoghar",
            "latitude": 24.4920,
            "longitude": 86.7010,
            "total_beds": 500,
            "available_beds": 160,
            "icu_beds": 60,
            "available_icu_beds": 24,
            "emergency_beds": 30,
            "available_emergency_beds": 12,
            **SUPER_SPECIALTY_EXTRA,
        },
    ])

    # West Bengal
    hospitals.extend([
        {
            "hospital_id": "GH_WB_SLG_01",
            "name": "North Bengal Medical College & Hospital Siliguri",
            "tier": "TERTIARY",
            "state": "West Bengal",
            "district": "Darjeeling",
            "city": "Siliguri",
            "latitude": 26.7110,
            "longitude": 88.3780,
            "total_beds": 650,
            "available_beds": 190,
            "icu_beds": 70,
            "available_icu_beds": 25,
            "emergency_beds": 40,
            "available_emergency_beds": 15,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_WB_MLD_01",
            "name": "Malda Medical College & Hospital",
            "tier": "DISTRICT",
            "state": "West Bengal",
            "district": "Malda",
            "city": "Malda",
            "latitude": 25.0110,
            "longitude": 88.1410,
            "total_beds": 400,
            "available_beds": 120,
            "icu_beds": 40,
            "available_icu_beds": 14,
            "emergency_beds": 25,
            "available_emergency_beds": 10,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_WB_KOL_01",
            "name": "SSKM Hospital & IPGMER Kolkata",
            "tier": "SUPER_SPECIALTY",
            "state": "West Bengal",
            "district": "Kolkata",
            "city": "Kolkata",
            "latitude": 22.5390,
            "longitude": 88.3430,
            "total_beds": 1200,
            "available_beds": 350,
            "icu_beds": 150,
            "available_icu_beds": 50,
            "emergency_beds": 70,
            "available_emergency_beds": 30,
            **SUPER_SPECIALTY_EXTRA,
        },
    ])

    # Uttar Pradesh
    hospitals.extend([
        {
            "hospital_id": "GH_UP_VNS_01",
            "name": "Institute of Medical Sciences BHU Varanasi",
            "tier": "SUPER_SPECIALTY",
            "state": "Uttar Pradesh",
            "district": "Varanasi",
            "city": "Varanasi",
            "latitude": 25.2750,
            "longitude": 82.9990,
            "total_beds": 900,
            "available_beds": 260,
            "icu_beds": 110,
            "available_icu_beds": 40,
            "emergency_beds": 50,
            "available_emergency_beds": 20,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_UP_GKP_01",
            "name": "BRD Medical College Gorakhpur",
            "tier": "TERTIARY",
            "state": "Uttar Pradesh",
            "district": "Gorakhpur",
            "city": "Gorakhpur",
            "latitude": 26.7910,
            "longitude": 83.3820,
            "total_beds": 600,
            "available_beds": 180,
            "icu_beds": 65,
            "available_icu_beds": 22,
            "emergency_beds": 35,
            "available_emergency_beds": 14,
            **TERTIARY_SPECIALTIES,
        },
        {
            "hospital_id": "GH_UP_LKO_01",
            "name": "King George's Medical University (KGMU) Lucknow",
            "tier": "SUPER_SPECIALTY",
            "state": "Uttar Pradesh",
            "district": "Lucknow",
            "city": "Lucknow",
            "latitude": 26.8680,
            "longitude": 80.9180,
            "total_beds": 1100,
            "available_beds": 320,
            "icu_beds": 140,
            "available_icu_beds": 48,
            "emergency_beds": 65,
            "available_emergency_beds": 25,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_UP_PRY_01",
            "name": "MLN Medical College Prayagraj",
            "tier": "TERTIARY",
            "state": "Uttar Pradesh",
            "district": "Prayagraj",
            "city": "Prayagraj",
            "latitude": 25.4520,
            "longitude": 81.8540,
            "total_beds": 550,
            "available_beds": 160,
            "icu_beds": 55,
            "available_icu_beds": 18,
            "emergency_beds": 30,
            "available_emergency_beds": 12,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Delhi NCR
    hospitals.extend([
        {
            "hospital_id": "GH_DL_NDL_01",
            "name": "AIIMS New Delhi",
            "tier": "SUPER_SPECIALTY",
            "state": "Delhi",
            "district": "New Delhi",
            "city": "New Delhi",
            "latitude": 28.5672,
            "longitude": 77.2100,
            "total_beds": 1500,
            "available_beds": 420,
            "icu_beds": 180,
            "available_icu_beds": 60,
            "emergency_beds": 80,
            "available_emergency_beds": 35,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_DL_NDL_02",
            "name": "Safdarjung Hospital Delhi",
            "tier": "TERTIARY",
            "state": "Delhi",
            "district": "South West Delhi",
            "city": "New Delhi",
            "latitude": 28.5700,
            "longitude": 77.2070,
            "total_beds": 1200,
            "available_beds": 340,
            "icu_beds": 130,
            "available_icu_beds": 42,
            "emergency_beds": 60,
            "available_emergency_beds": 22,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Maharashtra
    hospitals.extend([
        {
            "hospital_id": "GH_MH_MUM_01",
            "name": "King Edward Memorial (KEM) Hospital Mumbai",
            "tier": "SUPER_SPECIALTY",
            "state": "Maharashtra",
            "district": "Mumbai City",
            "city": "Mumbai",
            "latitude": 19.0020,
            "longitude": 72.8420,
            "total_beds": 1400,
            "available_beds": 380,
            "icu_beds": 160,
            "available_icu_beds": 55,
            "emergency_beds": 75,
            "available_emergency_beds": 30,
            **SUPER_SPECIALTY_EXTRA,
        },
        {
            "hospital_id": "GH_MH_PUN_01",
            "name": "Sassoon General Hospital Pune",
            "tier": "TERTIARY",
            "state": "Maharashtra",
            "district": "Pune",
            "city": "Pune",
            "latitude": 18.5280,
            "longitude": 73.8740,
            "total_beds": 800,
            "available_beds": 230,
            "icu_beds": 85,
            "available_icu_beds": 28,
            "emergency_beds": 45,
            "available_emergency_beds": 18,
            **TERTIARY_SPECIALTIES,
        },
    ])

    # Karnataka
    hospitals.append({
        "hospital_id": "GH_KA_BLR_01",
        "name": "Victoria Hospital / BMCRI Bengaluru",
        "tier": "SUPER_SPECIALTY",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "latitude": 12.9630,
        "longitude": 77.5750,
        "total_beds": 1000,
        "available_beds": 290,
        "icu_beds": 120,
        "available_icu_beds": 38,
        "emergency_beds": 55,
        "available_emergency_beds": 22,
        **SUPER_SPECIALTY_EXTRA,
    })

    # Tamil Nadu
    hospitals.append({
        "hospital_id": "GH_TN_CHE_01",
        "name": "Rajiv Gandhi Government General Hospital Chennai",
        "tier": "SUPER_SPECIALTY",
        "state": "Tamil Nadu",
        "district": "Chennai",
        "city": "Chennai",
        "latitude": 13.0810,
        "longitude": 80.2780,
        "total_beds": 1100,
        "available_beds": 310,
        "icu_beds": 130,
        "available_icu_beds": 45,
        "emergency_beds": 60,
        "available_emergency_beds": 25,
        **SUPER_SPECIALTY_EXTRA,
    })

    # Rajasthan
    hospitals.append({
        "hospital_id": "GH_RJ_JPR_01",
        "name": "Sawai Man Singh (SMS) Hospital Jaipur",
        "tier": "SUPER_SPECIALTY",
        "state": "Rajasthan",
        "district": "Jaipur",
        "city": "Jaipur",
        "latitude": 26.8980,
        "longitude": 75.8160,
        "total_beds": 1200,
        "available_beds": 350,
        "icu_beds": 140,
        "available_icu_beds": 48,
        "emergency_beds": 65,
        "available_emergency_beds": 26,
        **SUPER_SPECIALTY_EXTRA,
    })

    # Madhya Pradesh
    hospitals.append({
        "hospital_id": "GH_MP_BHO_01",
        "name": "AIIMS Bhopal",
        "tier": "SUPER_SPECIALTY",
        "state": "Madhya Pradesh",
        "district": "Bhopal",
        "city": "Bhopal",
        "latitude": 23.2080,
        "longitude": 77.4600,
        "total_beds": 750,
        "available_beds": 220,
        "icu_beds": 90,
        "available_icu_beds": 32,
        "emergency_beds": 45,
        "available_emergency_beds": 18,
        **SUPER_SPECIALTY_EXTRA,
    })

    # Gujarat
    hospitals.append({
        "hospital_id": "GH_GJ_AMD_01",
        "name": "Civil Hospital Ahmedabad",
        "tier": "TERTIARY",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "city": "Ahmedabad",
        "latitude": 23.0530,
        "longitude": 72.6020,
        "total_beds": 1100,
        "available_beds": 320,
        "icu_beds": 125,
        "available_icu_beds": 42,
        "emergency_beds": 60,
        "available_emergency_beds": 24,
        **TERTIARY_SPECIALTIES,
    })

    # Haryana
    hospitals.extend([
        {
            "hospital_id": "GH_HR_GUR_01",
            "name": "Civil Hospital Gurugram",
            "tier": "DISTRICT",
            "state": "Haryana",
            "district": "Gurugram",
            "city": "Gurugram",
            "latitude": 28.4610,
            "longitude": 77.0320,
            "total_beds": 250,
            "available_beds": 80,
            "icu_beds": 30,
            "available_icu_beds": 10,
            "emergency_beds": 20,
            "available_emergency_beds": 8,
            **DISTRICT_SPECIALTIES,
        },
        {
            "hospital_id": "GH_HR_AMB_01",
            "name": "Civil Hospital Ambala",
            "tier": "DISTRICT",
            "state": "Haryana",
            "district": "Ambala",
            "city": "Ambala",
            "latitude": 30.3780,
            "longitude": 76.7760,
            "total_beds": 220,
            "available_beds": 70,
            "icu_beds": 25,
            "available_icu_beds": 9,
            "emergency_beds": 18,
            "available_emergency_beds": 7,
            **DISTRICT_SPECIALTIES,
        },
    ])

    return hospitals


# ==============================================================================
# MAIN SEEDING FUNCTION
# ==============================================================================

def seed_database():
    db_url = get_target_db_url()
    print(f"\n[INFO] Connecting to target database: {db_url}")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        now = datetime.now(timezone.utc)
        default_pwd_hash = hash_password(DEFAULT_PASSWORD)

        # Ensure reference roles exist before provisioning users
        cur.execute(
            """
            INSERT INTO roles (id, description, created_at)
            VALUES 
                ('HOSPITAL', 'Hospital Staff', %s),
                ('DISTRICT_ADMIN', 'District Admin', %s),
                ('STATE_ADMIN', 'State Admin', %s),
                ('CENTRAL_ADMIN', 'Central Admin', %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (now, now, now, now)
        )

        # ----------------------------------------------------------------------
        # 1. Update Originating Facility GH99927 (Purnea Hospital) Coordinates
        # ----------------------------------------------------------------------
        print("\n[STEP 1] Updating Purnea Hospital (GH99927) coordinates to accurate Purnia geolocation...")
        cur.execute(
            """
            UPDATE hospitals 
            SET latitude = 25.7771,
                longitude = 87.4753,
                district = 'Purnia',
                state = 'Bihar',
                city = 'Purnia',
                approval_status = 'APPROVED',
                emergency_24x7 = 'Yes',
                accepts_referral = 'Yes',
                updated_at = %s
            WHERE hospital_id = 'GH99927';
            """,
            (now,)
        )
        if cur.rowcount > 0:
            print("  ✓ GH99927 updated successfully to (25.7771, 87.4753) [Purnia, Bihar].")
        else:
            print("  ! GH99927 not found in database; inserting default Purnea Hospital...")
            cur.execute(
                """
                INSERT INTO hospitals (
                    hospital_id, name, state, district, city, latitude, longitude,
                    total_beds, occupied_beds, available_beds,
                    icu_beds, occupied_icu_beds, available_icu_beds,
                    emergency_beds, occupied_emergency_beds, available_emergency_beds,
                    emergency_24x7, accepts_referral, ambulance, oxygen_support, ventilator, blood_bank,
                    cardiology, neurology, nephrology, pulmonology, orthopedics, general_medicine, general_surgery,
                    trauma_unit, burn_unit, ct_scan, mri, xray, ultrasound, ecg, dialysis,
                    blood_test, cbc, troponin_test, dengue_ns1_test, malaria_test, blood_glucose_test,
                    hba1c_test, kidney_function_test, pulmonary_function_test, blood_culture, lactate_test, stool_test,
                    approval_status, is_grandfathered, approved_at, created_at, updated_at
                ) VALUES (
                    'GH99927', 'Purnea Hospital', 'Bihar', 'Purnia', 'Purnia', 25.7771, 87.4753,
                    150, 40, 110,
                    20, 5, 15,
                    15, 3, 12,
                    'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes',
                    'Yes', 'No', 'No', 'Yes', 'Yes', 'Yes', 'Yes',
                    'Yes', 'No', 'Yes', 'No', 'Yes', 'Yes', 'Yes', 'No',
                    'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes',
                    'Yes', 'Yes', 'No', 'Yes', 'No', 'Yes',
                    'APPROVED', true, %s, %s, %s
                );
                """,
                (now, now, now)
            )
            print("  ✓ GH99927 inserted with Purnia coordinates.")

        # Ensure user gh99927 exists and has password Hospital@123
        cur.execute(
            """
            INSERT INTO users (
                user_id, username, password_hash, name, role_id, hospital_id, state, district, is_active, created_at, updated_at
            ) VALUES (
                'U_gh99927', 'gh99927', %s, 'Purnea Hospital Administrator', 'HOSPITAL', 'GH99927', 'Bihar', 'Purnia', true, %s, %s
            ) ON CONFLICT (username) DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                is_active = true,
                hospital_id = 'GH99927',
                state = 'Bihar',
                district = 'Purnia',
                updated_at = EXCLUDED.updated_at;
            """,
            (default_pwd_hash, now, now)
        )
        print("  ✓ User gh99927 password set to Hospital@123.")

        # ----------------------------------------------------------------------
        # 2. Seed Multi-District Hospitals
        # ----------------------------------------------------------------------
        hospitals_data = build_hospitals_data()
        print(f"\n[STEP 2] Seeding {len(hospitals_data)} realistic regional and national hospitals...")

        hosp_insert_query = """
        INSERT INTO hospitals (
            hospital_id, name, state, district, city, latitude, longitude,
            total_beds, occupied_beds, available_beds,
            icu_beds, occupied_icu_beds, available_icu_beds,
            emergency_beds, occupied_emergency_beds, available_emergency_beds,
            emergency_24x7, accepts_referral, ambulance, oxygen_support, ventilator, blood_bank,
            cardiology, neurology, nephrology, pulmonology, orthopedics, general_medicine, general_surgery,
            trauma_unit, burn_unit, ct_scan, mri, xray, ultrasound, ecg, dialysis,
            blood_test, cbc, troponin_test, dengue_ns1_test, malaria_test, blood_glucose_test,
            hba1c_test, kidney_function_test, pulmonary_function_test, blood_culture, lactate_test, stool_test,
            approval_status, is_grandfathered, approved_at, created_at, updated_at
        ) VALUES (
            %(hospital_id)s, %(name)s, %(state)s, %(district)s, %(city)s, %(latitude)s, %(longitude)s,
            %(total_beds)s, %(occupied_beds)s, %(available_beds)s,
            %(icu_beds)s, %(occupied_icu_beds)s, %(available_icu_beds)s,
            %(emergency_beds)s, %(occupied_emergency_beds)s, %(available_emergency_beds)s,
            'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes',
            %(cardiology)s, %(neurology)s, %(nephrology)s, %(pulmonology)s, %(orthopedics)s, %(general_medicine)s, %(general_surgery)s,
            %(trauma_unit)s, %(burn_unit)s, %(ct_scan)s, %(mri)s, %(xray)s, %(ultrasound)s, %(ecg)s, %(dialysis)s,
            %(blood_test)s, %(cbc)s, %(troponin_test)s, %(dengue_ns1_test)s, %(malaria_test)s, %(blood_glucose_test)s,
            %(hba1c_test)s, %(kidney_function_test)s, %(pulmonary_function_test)s, %(blood_culture)s, %(lactate_test)s, %(stool_test)s,
            'APPROVED', true, %(approved_at)s, %(created_at)s, %(updated_at)s
        ) ON CONFLICT (hospital_id) DO UPDATE SET
            name = EXCLUDED.name,
            state = EXCLUDED.state,
            district = EXCLUDED.district,
            city = EXCLUDED.city,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude,
            total_beds = EXCLUDED.total_beds,
            available_beds = EXCLUDED.available_beds,
            icu_beds = EXCLUDED.icu_beds,
            available_icu_beds = EXCLUDED.available_icu_beds,
            emergency_beds = EXCLUDED.emergency_beds,
            available_emergency_beds = EXCLUDED.available_emergency_beds,
            emergency_24x7 = 'Yes',
            accepts_referral = 'Yes',
            approval_status = 'APPROVED',
            cardiology = EXCLUDED.cardiology,
            neurology = EXCLUDED.neurology,
            nephrology = EXCLUDED.nephrology,
            pulmonology = EXCLUDED.pulmonology,
            orthopedics = EXCLUDED.orthopedics,
            general_medicine = EXCLUDED.general_medicine,
            general_surgery = EXCLUDED.general_surgery,
            trauma_unit = EXCLUDED.trauma_unit,
            burn_unit = EXCLUDED.burn_unit,
            ct_scan = EXCLUDED.ct_scan,
            mri = EXCLUDED.mri,
            xray = EXCLUDED.xray,
            ultrasound = EXCLUDED.ultrasound,
            ecg = EXCLUDED.ecg,
            dialysis = EXCLUDED.dialysis,
            updated_at = EXCLUDED.updated_at;
        """

        user_insert_query = """
        INSERT INTO users (
            user_id, username, password_hash, name, role_id, hospital_id, state, district, is_active, email, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, 'HOSPITAL', %s, %s, %s, true, %s, %s, %s
        ) ON CONFLICT (username) DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            hospital_id = EXCLUDED.hospital_id,
            state = EXCLUDED.state,
            district = EXCLUDED.district,
            is_active = true,
            updated_at = EXCLUDED.updated_at;
        """

        credentials_records = [
            {
                "state": "Bihar",
                "district": "Purnia",
                "hospital_id": "GH99927",
                "name": "Purnea Hospital",
                "tier": "DISTRICT",
                "username": "gh99927",
                "password": DEFAULT_PASSWORD,
            }
        ]

        for h in hospitals_data:
            # Set default occupied counts
            h["occupied_beds"] = max(0, h["total_beds"] - h["available_beds"])
            h["occupied_icu_beds"] = max(0, h["icu_beds"] - h["available_icu_beds"])
            h["occupied_emergency_beds"] = max(0, h["emergency_beds"] - h["available_emergency_beds"])
            h["approved_at"] = now
            h["created_at"] = now
            h["updated_at"] = now

            cur.execute(hosp_insert_query, h)

            # Provision User
            username = h["hospital_id"].lower()
            user_id = f"U_{username}"
            user_name = f"{h['name']} Admin"
            email = f"{username}@hospital.sih.gov.in"

            cur.execute(
                user_insert_query,
                (user_id, username, default_pwd_hash, user_name, h["hospital_id"], h["state"], h["district"], email, now, now)
            )

            credentials_records.append({
                "state": h["state"],
                "district": h["district"],
                "hospital_id": h["hospital_id"],
                "name": h["name"],
                "tier": h.get("tier", "DISTRICT"),
                "username": username,
                "password": DEFAULT_PASSWORD,
            })

        # ----------------------------------------------------------------------
        # 3. Seed Beds Inventory Rows
        # ----------------------------------------------------------------------
        print("\n[STEP 3] Populating bed rows for live reservation tracking...")
        all_hosp_ids = [h["hospital_id"] for h in hospitals_data] + ["GH99927"]
        cur.execute("DELETE FROM beds WHERE hospital_id = ANY(%s);", (all_hosp_ids,))

        bed_rows = []
        for h in hospitals_data:
            hid = h["hospital_id"]
            # Available General beds
            for i in range(1, min(h["available_beds"], 25) + 1):
                bed_rows.append((f"{hid}-GEN-{i:03d}", hid, "GENERAL", "AVAILABLE", now, now))
            # Available ICU beds
            for i in range(1, min(h["available_icu_beds"], 12) + 1):
                bed_rows.append((f"{hid}-ICU-{i:03d}", hid, "ICU", "AVAILABLE", now, now))
            # Available Emergency beds
            for i in range(1, min(h["available_emergency_beds"], 8) + 1):
                bed_rows.append((f"{hid}-EMG-{i:03d}", hid, "EMERGENCY", "AVAILABLE", now, now))

        # Add beds for GH99927
        for i in range(1, 21):
            bed_rows.append((f"GH99927-GEN-{i:03d}", "GH99927", "GENERAL", "AVAILABLE", now, now))
        for i in range(1, 11):
            bed_rows.append((f"GH99927-ICU-{i:03d}", "GH99927", "ICU", "AVAILABLE", now, now))

        execute_values(
            cur,
            """
            INSERT INTO beds (bed_number, hospital_id, bed_type, status, created_at, updated_at)
            VALUES %s
            ON CONFLICT DO NOTHING;
            """,
            bed_rows
        )
        print(f"  ✓ Inserted {len(bed_rows)} operational beds across network.")

        conn.commit()
        print("\n[SUCCESS] All regional hospitals, users, and bed inventories committed successfully.")

        # ----------------------------------------------------------------------
        # 4. Generate SEEDED_HOSPITAL_CREDENTIALS.md
        # ----------------------------------------------------------------------
        print("\n[STEP 4] Writing credentials reference to SEEDED_HOSPITAL_CREDENTIALS.md...")
        cred_file_path = BASE_DIR / "SEEDED_HOSPITAL_CREDENTIALS.md"
        with open(cred_file_path, "w", encoding="utf-8") as f:
            f.write("# SIH Hospital AI — Seeded Hospital Login Credentials\n\n")
            f.write("**Target Database:** `sih_hospital_local_preview`\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("**Default Password for all seeded accounts:** `Hospital@123`\n\n")
            f.write("Use any of the accounts below at the Hospital Department Login (`/portal/hospital/login`) to test clinical intake, patient transfer, and incoming referral admission.\n\n")

            # Group by State, then District
            states_grouped = {}
            for c in credentials_records:
                states_grouped.setdefault(c["state"], {}).setdefault(c["district"], []).append(c)

            # Bihar First
            ordered_states = ["Bihar"] + sorted([s for s in states_grouped.keys() if s != "Bihar"])

            for st in ordered_states:
                districts_dict = states_grouped[st]
                f.write(f"## State: {st}\n\n")
                f.write("| District | Hospital ID | Hospital Name | Tier | Username | Password |\n")
                f.write("| :--- | :--- | :--- | :--- | :--- | :--- |\n")
                for dist in sorted(districts_dict.keys()):
                    for h in districts_dict[dist]:
                        f.write(f"| {h['district']} | `{h['hospital_id']}` | {h['name']} | {h['tier']} | `{h['username']}` | `{h['password']}` |\n")
                f.write("\n---\n\n")

        print(f"  ✓ Credentials written to: {cred_file_path}")

    except Exception as exc:
        conn.rollback()
        print(f"\n[ERROR] Seeding transaction failed: {exc}", file=sys.stderr)
        raise exc
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    seed_database()
