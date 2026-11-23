"""
Database initialization and automatic table creation module.
AI-Powered Smart Hospital Referral System — SWASTHYA SAMANVAY

Ensures that all SQLAlchemy ORM models (across PostgreSQL PgBase and SQLite Base)
are explicitly registered and created on application startup, guaranteeing that
critical relational tables like `verification_tokens` and baseline reference roles
exist on fresh deployments (e.g., Render, Neon, Supabase) without requiring manual migrations.
"""

from datetime import datetime, timezone
import logging
from sqlalchemy import text, inspect

from src.database.database import Base as SqliteBase, engine as sqlite_engine
from src.database.db_manager import get_engine, is_postgres
from src.database.pg_models import (
    PgBase,
    Role,
    Hospital,
    User,
    Patient,
    HospitalVisit,
    Bed,
    Referral,
    BedReservation,
    AuditLog,
    Notification,
    RegistrationApplication,
    RegistrationDocument,
    ApprovalHistory,
    VerificationToken,
    ApplicationTrackingToken,
    AccountActivationToken,
    RegistrationEmailOutbox,
    PasswordResetToken,
    WorkerHeartbeat,
)
from src.database import models, pg_models  # noqa: F401

logger = logging.getLogger("db_init")

# Unified Base alias pointing to the full relational DeclarativeBase
Base = PgBase

__all__ = [
    "Base",
    "PgBase",
    "SqliteBase",
    "Role",
    "Hospital",
    "User",
    "Patient",
    "HospitalVisit",
    "Bed",
    "Referral",
    "BedReservation",
    "AuditLog",
    "Notification",
    "RegistrationApplication",
    "RegistrationDocument",
    "ApprovalHistory",
    "VerificationToken",
    "ApplicationTrackingToken",
    "AccountActivationToken",
    "RegistrationEmailOutbox",
    "PasswordResetToken",
    "WorkerHeartbeat",
    "init_database",
    "seed_baseline_reference_data",
]


def seed_baseline_reference_data(engine=None):
    """
    Ensure essential baseline roles and default reviewer accounts exist in the database.
    Uses idempotent operations (checks existence before insertion).
    """
    if engine is None:
        engine = get_engine()

    roles = [
        ("HOSPITAL", "Hospital Staff"),
        ("DISTRICT_ADMIN", "District Admin"),
        ("STATE_ADMIN", "State Admin"),
        ("CENTRAL_ADMIN", "Central Admin"),
    ]

    is_pg = getattr(engine.dialect, "name", "") == "postgresql" or is_postgres()
    now_val = datetime.now(timezone.utc)

    # 1. Seed Roles
    try:
        with engine.begin() as conn:
            for role_id, description in roles:
                if is_pg:
                    conn.execute(
                        text(
                            "INSERT INTO roles (id, description, created_at) "
                            "VALUES (:id, :desc, :created_at) "
                            "ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": role_id, "desc": description, "created_at": now_val},
                    )
                else:
                    conn.execute(
                        text(
                            "INSERT OR IGNORE INTO roles (id, description, created_at) "
                            "VALUES (:id, :desc, :created_at)"
                        ),
                        {"id": role_id, "desc": description, "created_at": now_val.isoformat()},
                    )
        logger.info("Baseline reference roles verified/seeded successfully.")
    except Exception as ex:
        logger.warning("Could not auto-seed baseline reference roles: %s", ex)

    # 2. Seed Default Reviewer Accounts
    # - District Reviewer (Purnea, Bihar): email=district.purnea@swasthya.gov.in, password=District@123, role=DISTRICT_ADMIN, state=Bihar, district=Purnea
    # - State Reviewer (Bihar): email=state.bihar@swasthya.gov.in, password=State@123, role=STATE_ADMIN, state=Bihar
    # - Central Reviewer (National): email=central.admin@swasthya.gov.in, password=Central@123, role=CENTRAL_ADMIN
    from src.auth.auth_store import hash_password

    reviewer_accounts = [
        {
            "user_id": "USR_REV_DIST_PURNEA",
            "username": "district.purnea@swasthya.gov.in",
            "email": "district.purnea@swasthya.gov.in",
            "password": "District@123",
            "role": "DISTRICT_ADMIN",
            "name": "District Reviewer (Purnea, Bihar)",
            "state": "Bihar",
            "district": "Purnea",
            "designation": "District Reviewing Officer",
        },
        {
            "user_id": "USR_REV_STATE_BIHAR",
            "username": "state.bihar@swasthya.gov.in",
            "email": "state.bihar@swasthya.gov.in",
            "password": "State@123",
            "role": "STATE_ADMIN",
            "name": "State Reviewer (Bihar)",
            "state": "Bihar",
            "district": None,
            "designation": "State Health Administrator",
        },
        {
            "user_id": "USR_REV_CENTRAL_ADMIN",
            "username": "central.admin@swasthya.gov.in",
            "email": "central.admin@swasthya.gov.in",
            "password": "Central@123",
            "role": "CENTRAL_ADMIN",
            "name": "Central Reviewer (National)",
            "state": None,
            "district": None,
            "designation": "Central Health Reviewer",
        },
    ]

    try:
        with engine.begin() as conn:
            for rev in reviewer_accounts:
                # Idempotently check if email or username already exists
                check_query = text(
                    "SELECT user_id FROM users WHERE lower(email) = lower(:email) OR lower(username) = lower(:username)"
                )
                existing = conn.execute(
                    check_query,
                    {"email": rev["email"], "username": rev["username"]},
                ).fetchone()
                if not existing:
                    insert_query = text(
                        """
                        INSERT INTO users (
                            user_id, username, password_hash, name, role_id,
                            hospital_id, state, district, is_active, email,
                            designation, created_at, updated_at
                        ) VALUES (
                            :user_id, :username, :password_hash, :name, :role_id,
                            :hospital_id, :state, :district, :is_active, :email,
                            :designation, :created_at, :updated_at
                        )
                        """
                    )
                    conn.execute(
                        insert_query,
                        {
                            "user_id": rev["user_id"],
                            "username": rev["username"],
                            "password_hash": hash_password(rev["password"]),
                            "name": rev["name"],
                            "role_id": rev["role"],
                            "hospital_id": None,
                            "state": rev["state"],
                            "district": rev["district"],
                            "is_active": True,
                            "email": rev["email"],
                            "designation": rev["designation"],
                            "created_at": now_val if is_pg else now_val.isoformat(),
                            "updated_at": now_val if is_pg else now_val.isoformat(),
                        },
                    )
                    logger.info("Auto-seeded default reviewer user: %s (%s)", rev["email"], rev["role"])
        logger.info("Baseline reviewer accounts verified/seeded successfully.")
    except Exception as ex:
        logger.warning("Could not auto-seed baseline reviewer accounts: %s", ex)


def init_database(engine=None):
    """
    Explicitly create all tables on the active database engine (PostgreSQL or SQLite fallback)
    and ensure baseline reference records exist.
    """
    if engine is None:
        engine = get_engine()

    logger.info("Initializing database schema and registering all ORM models...")

    try:
        # 1. Create all production tables from PgBase (including verification_tokens)
        PgBase.metadata.create_all(bind=engine)

        # 2. Also ensure SqliteBase tables exist for backwards compatibility
        SqliteBase.metadata.create_all(bind=engine)

        # 3. If using SQLite fallback engine separately, also ensure tables exist on it
        if not is_postgres() and engine != sqlite_engine:
            try:
                PgBase.metadata.create_all(bind=sqlite_engine)
                SqliteBase.metadata.create_all(bind=sqlite_engine)
            except Exception as ex:
                logger.debug("Non-critical SQLite engine init notice: %s", ex)

        # 4. Seed baseline reference roles
        seed_baseline_reference_data(engine)

        logger.info("Database initialized successfully. Registered %d tables.", len(PgBase.metadata.tables))
    except Exception as e:
        logger.error("Failed to initialize database tables: %s", e)
        raise


if __name__ == "__main__":
    init_database()
