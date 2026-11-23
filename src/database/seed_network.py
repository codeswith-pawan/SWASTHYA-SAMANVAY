"""
Clean Network Seeding & Idempotent Database Reset
SWASTHYA SAMANVAY — AI-Powered Smart Hospital Referral System

Enforces:
1. Zero Mailjet / email_service calls during seeding.
2. Idempotent version marker 'seed_v2_clean_network' in _seed_metadata.
3. 4 System Roles: CENTRAL_ADMIN, STATE_ADMIN, DISTRICT_ADMIN, HOSPITAL.
4. Administrative Reviewers:
   - Central Admin: central.admin@swasthya.gov.in / Central@2026
   - 5 State Reviewers (Bihar, Punjab, Delhi, Maharashtra, Karnataka)
   - 6 District Reviewers (Purnea, Patna, Amritsar, New Delhi, Mumbai, Bengaluru Urban)
5. 25 Approved Hospitals with beds, live inventory, and active credentials:
   - 10 in Purnea, Bihar (purnea.hosp1@swasthya.gov.in .. purnea.hosp10@swasthya.gov.in / Hospital@2026)
   - 3 in Patna, Bihar (patna.hosp1..3 / Hospital@2026)
   - 3 in Amritsar, Punjab (amritsar.hosp1..3 / Hospital@2026)
   - 3 in New Delhi, Delhi (delhi.hosp1..3 / Hospital@2026)
   - 3 in Mumbai, Maharashtra (mumbai.hosp1..3 / Hospital@2026)
   - 3 in Bengaluru Urban, Karnataka (bengaluru.hosp1..3 / Hospital@2026)
"""

import json
import logging
import os
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.auth.auth_store import hash_password
from src.database.pg_models import (
    PgBase,
    Role,
    Hospital,
    User,
    Bed,
    Patient,
    HospitalVisit,
    Referral,
    BedReservation,
    RegistrationApplication,
    RegistrationDocument,
    ApprovalHistory,
    VerificationToken,
    AccountActivationToken,
    RegistrationEmailOutbox,
)
from src.prediction.reservation_store import load_bed_inventory, save_bed_inventory

logger = logging.getLogger("seed_network")

SEED_VERSION_MARKER = "seed_v2_clean_network"

REVIEWER_ACCOUNTS = [
    # Central Reviewer
    {
        "user_id": "USR_CENTRAL_01",
        "username": "central.admin@swasthya.gov.in",
        "email": "central.admin@swasthya.gov.in",
        "name": "Central Health Authority Reviewer",
        "role_id": "CENTRAL_ADMIN",
        "password": "Central@2026",
        "state": None,
        "district": None,
    },
    # State Reviewers
    {
        "user_id": "USR_STATE_BIHAR",
        "username": "state.bihar@swasthya.gov.in",
        "email": "state.bihar@swasthya.gov.in",
        "name": "Bihar State Health Directorate",
        "role_id": "STATE_ADMIN",
        "password": "StateBihar@2026",
        "state": "Bihar",
        "district": None,
    },
    {
        "user_id": "USR_STATE_PUNJAB",
        "username": "state.punjab@swasthya.gov.in",
        "email": "state.punjab@swasthya.gov.in",
        "name": "Punjab State Health Directorate",
        "role_id": "STATE_ADMIN",
        "password": "StatePunjab@2026",
        "state": "Punjab",
        "district": None,
    },
    {
        "user_id": "USR_STATE_DELHI",
        "username": "state.delhi@swasthya.gov.in",
        "email": "state.delhi@swasthya.gov.in",
        "name": "Delhi State Health Directorate",
        "role_id": "STATE_ADMIN",
        "password": "StateDelhi@2026",
        "state": "Delhi",
        "district": None,
    },
    {
        "user_id": "USR_STATE_MAHA",
        "username": "state.maharashtra@swasthya.gov.in",
        "email": "state.maharashtra@swasthya.gov.in",
        "name": "Maharashtra State Health Directorate",
        "role_id": "STATE_ADMIN",
        "password": "StateMaha@2026",
        "state": "Maharashtra",
        "district": None,
    },
    {
        "user_id": "USR_STATE_KAR",
        "username": "state.karnataka@swasthya.gov.in",
        "email": "state.karnataka@swasthya.gov.in",
        "name": "Karnataka State Health Directorate",
        "role_id": "STATE_ADMIN",
        "password": "StateKar@2026",
        "state": "Karnataka",
        "district": None,
    },
    # District Reviewers
    {
        "user_id": "USR_DIST_PURNEA",
        "username": "district.purnea@swasthya.gov.in",
        "email": "district.purnea@swasthya.gov.in",
        "name": "Purnea District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistPurnea@2026",
        "state": "Bihar",
        "district": "Purnea",
    },
    {
        "user_id": "USR_DIST_PATNA",
        "username": "district.patna@swasthya.gov.in",
        "email": "district.patna@swasthya.gov.in",
        "name": "Patna District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistPatna@2026",
        "state": "Bihar",
        "district": "Patna",
    },
    {
        "user_id": "USR_DIST_AMRITSAR",
        "username": "district.amritsar@swasthya.gov.in",
        "email": "district.amritsar@swasthya.gov.in",
        "name": "Amritsar District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistAmritsar@2026",
        "state": "Punjab",
        "district": "Amritsar",
    },
    {
        "user_id": "USR_DIST_DELHI",
        "username": "district.newdelhi@swasthya.gov.in",
        "email": "district.newdelhi@swasthya.gov.in",
        "name": "New Delhi District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistDelhi@2026",
        "state": "Delhi",
        "district": "New Delhi",
    },
    {
        "user_id": "USR_DIST_MUMBAI",
        "username": "district.mumbai@swasthya.gov.in",
        "email": "district.mumbai@swasthya.gov.in",
        "name": "Mumbai District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistMumbai@2026",
        "state": "Maharashtra",
        "district": "Mumbai",
    },
    {
        "user_id": "USR_DIST_BLR",
        "username": "district.bengaluru@swasthya.gov.in",
        "email": "district.bengaluru@swasthya.gov.in",
        "name": "Bengaluru Urban District Health Office",
        "role_id": "DISTRICT_ADMIN",
        "password": "DistBlr@2026",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
    },
]

HOSPITAL_NETWORK = [
    # 10 Approved Hospitals in Purnea, Bihar
    {
        "hospital_id": "HOSP_PURNEA_01",
        "name": "Sadar Hospital Purnea",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7785,
        "longitude": 87.4760,
        "total_beds": 150,
        "available_beds": 100,
        "occupied_beds": 50,
        "icu_beds": 30,
        "available_icu_beds": 20,
        "occupied_icu_beds": 10,
        "emergency_beds": 20,
        "available_emergency_beds": 15,
        "occupied_emergency_beds": 5,
        "login_email": "purnea.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_02",
        "name": "Max7 Hospital Purnea",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7742,
        "longitude": 87.4715,
        "total_beds": 100,
        "available_beds": 60,
        "occupied_beds": 40,
        "icu_beds": 25,
        "available_icu_beds": 15,
        "occupied_icu_beds": 10,
        "emergency_beds": 15,
        "available_emergency_beds": 10,
        "occupied_emergency_beds": 5,
        "login_email": "purnea.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_03",
        "name": "Galaxy Heart & Trauma Center Purnea",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7801,
        "longitude": 87.4810,
        "total_beds": 80,
        "available_beds": 45,
        "occupied_beds": 35,
        "icu_beds": 25,
        "available_icu_beds": 18,
        "occupied_icu_beds": 7,
        "emergency_beds": 10,
        "available_emergency_beds": 8,
        "occupied_emergency_beds": 2,
        "login_email": "purnea.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_04",
        "name": "Purnea Medical College & Hospital",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7820,
        "longitude": 87.4850,
        "total_beds": 300,
        "available_beds": 200,
        "occupied_beds": 100,
        "icu_beds": 60,
        "available_icu_beds": 40,
        "occupied_icu_beds": 20,
        "emergency_beds": 40,
        "available_emergency_beds": 30,
        "occupied_emergency_beds": 10,
        "login_email": "purnea.hosp4@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_05",
        "name": "Kosi Lifeline Multispeciality",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7710,
        "longitude": 87.4680,
        "total_beds": 70,
        "available_beds": 45,
        "occupied_beds": 25,
        "icu_beds": 15,
        "available_icu_beds": 10,
        "occupied_icu_beds": 5,
        "emergency_beds": 10,
        "available_emergency_beds": 7,
        "occupied_emergency_beds": 3,
        "login_email": "purnea.hosp5@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_06",
        "name": "Seemanchal Neuro & Ortho Care",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7755,
        "longitude": 87.4795,
        "total_beds": 60,
        "available_beds": 40,
        "occupied_beds": 20,
        "icu_beds": 12,
        "available_icu_beds": 8,
        "occupied_icu_beds": 4,
        "emergency_beds": 8,
        "available_emergency_beds": 6,
        "occupied_emergency_beds": 2,
        "login_email": "purnea.hosp6@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_07",
        "name": "Mithila Child & Maternity Hospital",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7790,
        "longitude": 87.4730,
        "total_beds": 50,
        "available_beds": 35,
        "occupied_beds": 15,
        "icu_beds": 10,
        "available_icu_beds": 6,
        "occupied_icu_beds": 4,
        "emergency_beds": 5,
        "available_emergency_beds": 4,
        "occupied_emergency_beds": 1,
        "login_email": "purnea.hosp7@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_08",
        "name": "Purnea City Critical Care",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7730,
        "longitude": 87.4770,
        "total_beds": 60,
        "available_beds": 35,
        "occupied_beds": 25,
        "icu_beds": 15,
        "available_icu_beds": 10,
        "occupied_icu_beds": 5,
        "emergency_beds": 10,
        "available_emergency_beds": 8,
        "occupied_emergency_beds": 2,
        "login_email": "purnea.hosp8@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_09",
        "name": "Apollo Clinic Purnea",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7760,
        "longitude": 87.4830,
        "total_beds": 40,
        "available_beds": 25,
        "occupied_beds": 15,
        "icu_beds": 10,
        "available_icu_beds": 7,
        "occupied_icu_beds": 3,
        "emergency_beds": 5,
        "available_emergency_beds": 4,
        "occupied_emergency_beds": 1,
        "login_email": "purnea.hosp9@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PURNEA_10",
        "name": "Green Valley Surgical Center",
        "state": "Bihar",
        "district": "Purnea",
        "city": "Purnea",
        "latitude": 25.7815,
        "longitude": 87.4705,
        "total_beds": 50,
        "available_beds": 35,
        "occupied_beds": 15,
        "icu_beds": 10,
        "available_icu_beds": 6,
        "occupied_icu_beds": 4,
        "emergency_beds": 5,
        "available_emergency_beds": 4,
        "occupied_emergency_beds": 1,
        "login_email": "purnea.hosp10@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    # 3 in Patna, Bihar
    {
        "hospital_id": "HOSP_PATNA_01",
        "name": "AIIMS Patna",
        "state": "Bihar",
        "district": "Patna",
        "city": "Patna",
        "latitude": 25.5615,
        "longitude": 85.0478,
        "total_beds": 500,
        "available_beds": 350,
        "occupied_beds": 150,
        "icu_beds": 100,
        "available_icu_beds": 60,
        "occupied_icu_beds": 40,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "patna.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PATNA_02",
        "name": "PMCH Patna",
        "state": "Bihar",
        "district": "Patna",
        "city": "Patna",
        "latitude": 25.6207,
        "longitude": 85.1588,
        "total_beds": 600,
        "available_beds": 450,
        "occupied_beds": 150,
        "icu_beds": 100,
        "available_icu_beds": 50,
        "occupied_icu_beds": 50,
        "emergency_beds": 50,
        "available_emergency_beds": 30,
        "occupied_emergency_beds": 20,
        "login_email": "patna.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_PATNA_03",
        "name": "Paras HMRI Hospital Patna",
        "state": "Bihar",
        "district": "Patna",
        "city": "Patna",
        "latitude": 25.6080,
        "longitude": 85.0910,
        "total_beds": 250,
        "available_beds": 160,
        "occupied_beds": 90,
        "icu_beds": 60,
        "available_icu_beds": 35,
        "occupied_icu_beds": 25,
        "emergency_beds": 30,
        "available_emergency_beds": 20,
        "occupied_emergency_beds": 10,
        "login_email": "patna.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    # 3 in Amritsar, Punjab
    {
        "hospital_id": "HOSP_AMRITSAR_01",
        "name": "Sri Guru Ram Das Hospital Amritsar",
        "state": "Punjab",
        "district": "Amritsar",
        "city": "Amritsar",
        "latitude": 31.6380,
        "longitude": 74.8750,
        "total_beds": 400,
        "available_beds": 280,
        "occupied_beds": 120,
        "icu_beds": 80,
        "available_icu_beds": 50,
        "occupied_icu_beds": 30,
        "emergency_beds": 40,
        "available_emergency_beds": 25,
        "occupied_emergency_beds": 15,
        "login_email": "amritsar.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_AMRITSAR_02",
        "name": "Civil Hospital Amritsar",
        "state": "Punjab",
        "district": "Amritsar",
        "city": "Amritsar",
        "latitude": 31.6290,
        "longitude": 74.8680,
        "total_beds": 200,
        "available_beds": 140,
        "occupied_beds": 60,
        "icu_beds": 40,
        "available_icu_beds": 25,
        "occupied_icu_beds": 15,
        "emergency_beds": 20,
        "available_emergency_beds": 15,
        "occupied_emergency_beds": 5,
        "login_email": "amritsar.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_AMRITSAR_03",
        "name": "Fortis Escorts Hospital Amritsar",
        "state": "Punjab",
        "district": "Amritsar",
        "city": "Amritsar",
        "latitude": 31.6510,
        "longitude": 74.8820,
        "total_beds": 250,
        "available_beds": 160,
        "occupied_beds": 90,
        "icu_beds": 60,
        "available_icu_beds": 35,
        "occupied_icu_beds": 25,
        "emergency_beds": 30,
        "available_emergency_beds": 20,
        "occupied_emergency_beds": 10,
        "login_email": "amritsar.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    # 3 in New Delhi, Delhi
    {
        "hospital_id": "HOSP_DELHI_01",
        "name": "AIIMS New Delhi",
        "state": "Delhi",
        "district": "New Delhi",
        "city": "New Delhi",
        "latitude": 28.5672,
        "longitude": 77.2100,
        "total_beds": 800,
        "available_beds": 550,
        "occupied_beds": 250,
        "icu_beds": 180,
        "available_icu_beds": 100,
        "occupied_icu_beds": 80,
        "emergency_beds": 70,
        "available_emergency_beds": 45,
        "occupied_emergency_beds": 25,
        "login_email": "delhi.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_DELHI_02",
        "name": "Safdarjung Hospital Delhi",
        "state": "Delhi",
        "district": "New Delhi",
        "city": "New Delhi",
        "latitude": 28.5700,
        "longitude": 77.2080,
        "total_beds": 700,
        "available_beds": 500,
        "occupied_beds": 200,
        "icu_beds": 140,
        "available_icu_beds": 80,
        "occupied_icu_beds": 60,
        "emergency_beds": 60,
        "available_emergency_beds": 40,
        "occupied_emergency_beds": 20,
        "login_email": "delhi.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_DELHI_03",
        "name": "Sir Ganga Ram Hospital Delhi",
        "state": "Delhi",
        "district": "New Delhi",
        "city": "New Delhi",
        "latitude": 28.6385,
        "longitude": 77.1895,
        "total_beds": 500,
        "available_beds": 350,
        "occupied_beds": 150,
        "icu_beds": 100,
        "available_icu_beds": 60,
        "occupied_icu_beds": 40,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "delhi.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    # 3 in Mumbai, Maharashtra
    {
        "hospital_id": "HOSP_MUMBAI_01",
        "name": "KEM Hospital Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "city": "Mumbai",
        "latitude": 19.0025,
        "longitude": 72.8425,
        "total_beds": 700,
        "available_beds": 500,
        "occupied_beds": 200,
        "icu_beds": 140,
        "available_icu_beds": 80,
        "occupied_icu_beds": 60,
        "emergency_beds": 60,
        "available_emergency_beds": 40,
        "occupied_emergency_beds": 20,
        "login_email": "mumbai.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_MUMBAI_02",
        "name": "Lilavati Hospital Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "city": "Mumbai",
        "latitude": 19.0515,
        "longitude": 72.8290,
        "total_beds": 350,
        "available_beds": 220,
        "occupied_beds": 130,
        "icu_beds": 80,
        "available_icu_beds": 50,
        "occupied_icu_beds": 30,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "mumbai.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_MUMBAI_03",
        "name": "Kokilaben Dhirubhai Ambani Hospital Mumbai",
        "state": "Maharashtra",
        "district": "Mumbai",
        "city": "Mumbai",
        "latitude": 19.1310,
        "longitude": 72.8250,
        "total_beds": 500,
        "available_beds": 340,
        "occupied_beds": 160,
        "icu_beds": 110,
        "available_icu_beds": 70,
        "occupied_icu_beds": 40,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "mumbai.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    # 3 in Bengaluru Urban, Karnataka
    {
        "hospital_id": "HOSP_BLR_01",
        "name": "Victoria Hospital Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "latitude": 12.9635,
        "longitude": 77.5750,
        "total_beds": 550,
        "available_beds": 400,
        "occupied_beds": 150,
        "icu_beds": 100,
        "available_icu_beds": 65,
        "occupied_icu_beds": 35,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "bengaluru.hosp1@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_BLR_02",
        "name": "Manipal Hospital Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "latitude": 12.9580,
        "longitude": 77.6490,
        "total_beds": 450,
        "available_beds": 300,
        "occupied_beds": 150,
        "icu_beds": 100,
        "available_icu_beds": 60,
        "occupied_icu_beds": 40,
        "emergency_beds": 50,
        "available_emergency_beds": 35,
        "occupied_emergency_beds": 15,
        "login_email": "bengaluru.hosp2@swasthya.gov.in",
        "password": "Hospital@2026",
    },
    {
        "hospital_id": "HOSP_BLR_03",
        "name": "Narayana Health City Bengaluru",
        "state": "Karnataka",
        "district": "Bengaluru Urban",
        "city": "Bengaluru",
        "latitude": 12.8120,
        "longitude": 77.6920,
        "total_beds": 600,
        "available_beds": 420,
        "occupied_beds": 180,
        "icu_beds": 120,
        "available_icu_beds": 75,
        "occupied_icu_beds": 45,
        "emergency_beds": 60,
        "available_emergency_beds": 40,
        "occupied_emergency_beds": 20,
        "login_email": "bengaluru.hosp3@swasthya.gov.in",
        "password": "Hospital@2026",
    },
]


def seed_clean_network_data(engine, force_reset: bool = False):
    """
    Perform idempotent reset and seeding.
    Guarantees ZERO calls to email_service or external SMTP.
    """
    if engine is None:
        from src.database.db_manager import get_engine
        engine = get_engine()

    # Ensure table schemas exist before attempting any operations
    PgBase.metadata.create_all(bind=engine)

    # 1. Check metadata marker table
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS _seed_metadata (
                version VARCHAR(64) PRIMARY KEY,
                applied_at TIMESTAMP NOT NULL
            );
        """))
        conn.commit()

        if not force_reset:
            res = conn.execute(
                text("SELECT version FROM _seed_metadata WHERE version = :ver"),
                {"ver": SEED_VERSION_MARKER},
            ).fetchone()
            if res:
                logger.info("Seed marker '%s' already exists. Skipping startup seed.", SEED_VERSION_MARKER)
                return

    logger.info("Applying one-time clean network database reset and seeding '%s'...", SEED_VERSION_MARKER)

    is_pg = (engine.dialect.name == "postgresql")
    now = datetime.now(timezone.utc)

    # 2. Database reset
    if is_pg:
        with engine.connect() as conn:
            try:
                conn.execute(text("""
                    TRUNCATE TABLE
                        referrals,
                        bed_reservations,
                        beds,
                        hospital_visits,
                        patients,
                        registration_email_outbox,
                        account_activation_tokens,
                        verification_tokens,
                        approval_history,
                        registration_documents,
                        registration_applications,
                        users,
                        hospitals,
                        roles
                    RESTART IDENTITY CASCADE;
                """))
                conn.commit()
                logger.info("PostgreSQL tables successfully truncated with CASCADE.")
            except Exception as e:
                logger.warning("PostgreSQL cascade truncate notice (falling back): %s", e)
                conn.rollback()

    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        # For SQLite fallback or any leftover records
        models_to_clear = [
            Referral,
            BedReservation,
            Bed,
            HospitalVisit,
            Patient,
            RegistrationEmailOutbox,
            AccountActivationToken,
            VerificationToken,
            ApprovalHistory,
            RegistrationDocument,
            RegistrationApplication,
            User,
            Hospital,
            Role,
        ]
        for m in models_to_clear:
            try:
                session.query(m).delete()
            except Exception:
                pass
        session.flush()

        # 3. Seed Roles
        roles = [
            Role(id="CENTRAL_ADMIN", description="Central / National Health Administrator", created_at=now),
            Role(id="STATE_ADMIN", description="State Health Administrator", created_at=now),
            Role(id="DISTRICT_ADMIN", description="District Health Administrator", created_at=now),
            Role(id="HOSPITAL", description="Hospital Operational Administrator", created_at=now),
        ]
        for r in roles:
            session.merge(r)
        session.flush()

        # 4. Seed Reviewer Users
        for rev in REVIEWER_ACCOUNTS:
            u = User(
                user_id=rev["user_id"],
                username=rev["username"],
                email=rev["email"],
                name=rev["name"],
                role_id=rev["role_id"],
                state=rev["state"],
                district=rev["district"],
                password_hash=hash_password(rev["password"]),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.merge(u)
        session.flush()

        # 5. Seed Hospitals & Bed inventory
        inventory_data = {}
        try:
            inventory_data = load_bed_inventory()
        except Exception:
            inventory_data = {}

        for h in HOSPITAL_NETWORK:
            hosp = Hospital(
                hospital_id=h["hospital_id"],
                name=h["name"],
                state=h["state"],
                district=h["district"],
                city=h["city"],
                latitude=h["latitude"],
                longitude=h["longitude"],
                total_beds=h["total_beds"],
                occupied_beds=h["occupied_beds"],
                available_beds=h["available_beds"],
                icu_beds=h["icu_beds"],
                available_icu_beds=h["available_icu_beds"],
                occupied_icu_beds=h["occupied_icu_beds"],
                emergency_beds=h["emergency_beds"],
                available_emergency_beds=h["available_emergency_beds"],
                occupied_emergency_beds=h["occupied_emergency_beds"],
                emergency_24x7="Yes",
                accepts_referral="Yes",
                ambulance="Yes",
                oxygen_support="Yes",
                ventilator="Yes",
                blood_bank="Yes",
                general_medicine="Yes",
                general_surgery="Yes",
                cardiology="Yes",
                neurology="Yes",
                nephrology="Yes",
                pulmonology="Yes",
                orthopedics="Yes",
                trauma_unit="Yes",
                burn_unit="Yes",
                ct_scan="Yes",
                mri="Yes",
                xray="Yes",
                ultrasound="Yes",
                ecg="Yes",
                dialysis="Yes",
                blood_test="Yes",
                cbc="Yes",
                troponin_test="Yes",
                dengue_ns1_test="Yes",
                malaria_test="Yes",
                blood_glucose_test="Yes",
                hba1c_test="Yes",
                kidney_function_test="Yes",
                pulmonary_function_test="Yes",
                blood_culture="Yes",
                lactate_test="Yes",
                stool_test="Yes",
                approval_status="APPROVED",
                is_grandfathered=True,
                approved_at=now,
                created_at=now,
                updated_at=now,
            )
            session.merge(hosp)

            # Seed Hospital User Login
            hosp_user = User(
                user_id=f"USR_{h['hospital_id']}",
                username=h["login_email"],
                email=h["login_email"],
                name=f"{h['name']} Operational Admin",
                role_id="HOSPITAL",
                hospital_id=h["hospital_id"],
                state=h["state"],
                district=h["district"],
                password_hash=hash_password(h["password"]),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.merge(hosp_user)

            # Seed physical beds in Bed table
            for i in range(1, 6):
                session.merge(Bed(
                    hospital_id=h["hospital_id"],
                    bed_number=f"GEN_{i:03d}",
                    bed_type="GENERAL",
                    status="AVAILABLE",
                    created_at=now,
                    updated_at=now,
                ))
            for i in range(1, 3):
                session.merge(Bed(
                    hospital_id=h["hospital_id"],
                    bed_number=f"ICU_{i:03d}",
                    bed_type="ICU",
                    status="AVAILABLE",
                    created_at=now,
                    updated_at=now,
                ))
            session.merge(Bed(
                hospital_id=h["hospital_id"],
                bed_number="EMERG_001",
                bed_type="EMERGENCY",
                status="AVAILABLE",
                created_at=now,
                updated_at=now,
            ))

            # Live bed inventory map
            inventory_data[h["hospital_id"]] = {
                "hospital_id": h["hospital_id"],
                "available_beds": h["available_beds"],
                "available_icu_beds": h["available_icu_beds"],
                "available_emergency_beds": h["available_emergency_beds"],
                "beds": {
                    "GENERAL_001": "AVAILABLE",
                    "GENERAL_002": "AVAILABLE",
                    "GENERAL_003": "AVAILABLE",
                    "GENERAL_004": "AVAILABLE",
                    "GENERAL_005": "AVAILABLE",
                    "ICU_001": "AVAILABLE",
                    "ICU_002": "AVAILABLE",
                    "EMERGENCY_001": "AVAILABLE",
                },
            }

        session.commit()

        # Save bed inventory JSON
        try:
            save_bed_inventory(inventory_data)
        except Exception as inv_err:
            logger.warning("Could not persist bed_inventory.json: %s", inv_err)

    # 6. Record version marker in _seed_metadata
    with engine.connect() as conn:
        try:
            conn.execute(
                text("INSERT INTO _seed_metadata (version, applied_at) VALUES (:ver, :ts) ON CONFLICT (version) DO NOTHING"),
                {"ver": SEED_VERSION_MARKER, "ts": now},
            )
            conn.commit()
        except Exception:
            try:
                conn.execute(
                    text("INSERT OR IGNORE INTO _seed_metadata (version, applied_at) VALUES (:ver, :ts)"),
                    {"ver": SEED_VERSION_MARKER, "ts": now},
                )
                conn.commit()
            except Exception as meta_err:
                logger.warning("Seed metadata record notice: %s", meta_err)

    logger.info("Successfully seeded network data (version: %s) with 25 hospitals and 12 administrative reviewers.", SEED_VERSION_MARKER)
