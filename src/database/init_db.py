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
    Ensure essential baseline roles exist in the database.
    Uses idempotent operations (ON CONFLICT DO NOTHING / INSERT OR IGNORE).
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
