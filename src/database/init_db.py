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

from src.database.seed_network import seed_clean_network_data, SEED_VERSION_MARKER

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
    One-time idempotent baseline reference network data seed for SWASTHYA-SAMANVAY.
    Guarantees zero email/Mailjet calls and idempotent version checking via _seed_metadata.
    """
    logger.info("Verifying and seeding baseline reference data...")
    seed_clean_network_data(engine)


def _ensure_sqlite_hospital_columns(engine):
    """Ensure legacy SQLite hospitals table has all columns matching PgHospital."""
    if engine.dialect.name == "sqlite":
        with engine.connect() as conn:
            try:
                res = conn.execute(text("PRAGMA table_info(hospitals);")).fetchall()
                existing_cols = {r[1] for r in res}
                missing = [
                    ("occupied_icu_beds", "INTEGER DEFAULT 0"),
                    ("occupied_emergency_beds", "INTEGER DEFAULT 0"),
                    ("approval_status", "VARCHAR(30) DEFAULT 'APPROVED'"),
                    ("is_grandfathered", "BOOLEAN DEFAULT 1"),
                    ("approved_at", "DATETIME"),
                    ("application_id", "VARCHAR(64)"),
                    ("updated_at", "DATETIME"),
                ]
                for col_name, col_def in missing:
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE hospitals ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception as ex:
                logger.debug("SQLite column ensure notice: %s", ex)


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
        _ensure_sqlite_hospital_columns(engine)

        # 3. If using SQLite fallback engine separately, also ensure tables exist on it
        if not is_postgres() and engine != sqlite_engine:
            try:
                PgBase.metadata.create_all(bind=sqlite_engine)
                SqliteBase.metadata.create_all(bind=sqlite_engine)
                _ensure_sqlite_hospital_columns(sqlite_engine)
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
