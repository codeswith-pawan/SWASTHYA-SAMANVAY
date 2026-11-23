"""
Unit and Integration Tests for Automatic Database Initialization & Model Registration
AI-Powered Smart Hospital Referral System — SWASTHYA SAMANVAY
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from src.database.init_db import init_database, seed_baseline_reference_data
from src.database.pg_models import PgBase, VerificationToken, Role
from src.db import Base, get_engine, init_database as db_init
from src.models import (
    VerificationToken as ModelVerificationToken,
    Role as ModelRole,
    Hospital,
    User,
    Bed,
    Referral,
    BedReservation,
)


def test_init_database_creates_all_tables_including_verification_tokens():
    """Verify that init_database creates verification_tokens and all 19 ORM tables on a fresh engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Run initialization
    init_database(engine)
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    # Assert verification_tokens exists
    assert "verification_tokens" in table_names, (
        f"verification_tokens MUST be created on database initialization. Found: {table_names}"
    )
    
    # Assert critical relational tables exist
    expected_tables = [
        "roles",
        "hospitals",
        "users",
        "patients",
        "hospital_visits",
        "beds",
        "referrals",
        "bed_reservations",
        "audit_logs",
        "notifications",
        "registration_applications",
        "registration_documents",
        "approval_history",
        "verification_tokens",
        "application_tracking_tokens",
        "account_activation_tokens",
        "registration_email_outbox",
        "password_reset_tokens",
        "worker_heartbeats",
    ]
    for tbl in expected_tables:
        assert tbl in table_names, f"Expected table '{tbl}' was not created in database!"


def test_baseline_roles_seeded_on_empty_database():
    """Verify that core reference roles are auto-seeded on initialization."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT id FROM roles ORDER BY id")).fetchall()
        role_ids = {r[0] for r in result}
        
    expected_roles = {"HOSPITAL", "DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"}
    assert expected_roles.issubset(role_ids), f"Expected roles {expected_roles} but found {role_ids}"


def test_src_models_and_src_db_module_exports():
    """Verify that src.models and src.db correctly export all required classes."""
    assert ModelVerificationToken is VerificationToken
    assert ModelRole is Role
    assert issubclass(VerificationToken, Base)
    assert issubclass(Hospital, Base)
    assert issubclass(User, Base)
    assert issubclass(Bed, Base)
    assert issubclass(Referral, Base)
    assert issubclass(BedReservation, Base)
    assert callable(db_init)


def test_fastapi_lifespan_startup_initializes_database():
    """Verify that FastAPI application lifespan runs init_database on startup without error."""
    from src.api.main import app
    with TestClient(app) as client:
        resp = client.get("/health/live")
        assert resp.status_code == 200
