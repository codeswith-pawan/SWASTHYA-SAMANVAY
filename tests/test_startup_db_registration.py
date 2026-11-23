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


def test_baseline_reviewer_accounts_seeded_on_empty_database():
    """Verify that default district, state, and central reviewer accounts are seeded on database initialization."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)

    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT email, role_id, state, district, is_active FROM users WHERE email IS NOT NULL")
        ).fetchall()
        user_map = {r[0]: r for r in result}

    expected_reviewers = {
        "district.purnea@swasthya.gov.in": ("DISTRICT_ADMIN", "Bihar", "Purnea"),
        "state.bihar@swasthya.gov.in": ("STATE_ADMIN", "Bihar", None),
        "central.admin@swasthya.gov.in": ("CENTRAL_ADMIN", None, None),
    }

    for email, (exp_role, exp_state, exp_district) in expected_reviewers.items():
        assert email in user_map, f"Reviewer user '{email}' was not seeded into database!"
        row = user_map[email]
        assert row[1] == exp_role, f"Expected role {exp_role} for {email}, got {row[1]}"
        assert row[2] == exp_state, f"Expected state {exp_state} for {email}, got {row[2]}"
        assert row[3] == exp_district, f"Expected district {exp_district} for {email}, got {row[3]}"
        assert bool(row[4]) is True, f"Expected user {email} to be active"

    # Verify idempotency: running seed_baseline_reference_data again does not duplicate or raise
    seed_baseline_reference_data(engine)
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM users WHERE email IN ('district.purnea@swasthya.gov.in', 'state.bihar@swasthya.gov.in', 'central.admin@swasthya.gov.in')")
        ).scalar()
        assert count == 3, f"Expected exactly 3 reviewer users after second seed run, found {count}"


def test_reviewer_accounts_login_via_api_auth_login():
    """
    Verify that after init_database(), all 3 default reviewer accounts can log in
    via POST /api/auth/login with HTTP 200 and receive valid Bearer tokens and role claims.
    """
    from src.api.main import app

    init_database()

    with TestClient(app) as client:
        accounts = [
            ("district.purnea@swasthya.gov.in", "District@123", "DISTRICT_ADMIN", "Bihar", "Purnea"),
            ("state.bihar@swasthya.gov.in", "State@123", "STATE_ADMIN", "Bihar", None),
            ("central.admin@swasthya.gov.in", "Central@123", "CENTRAL_ADMIN", None, None),
        ]

        for email, password, expected_role, expected_state, expected_district in accounts:
            response = client.post(
                "/api/auth/login",
                json={"username": email, "password": password},
            )
            assert response.status_code == 200, (
                f"POST /api/auth/login failed for {email}: status={response.status_code}, response={response.text}"
            )
            data = response.json()
            assert data["success"] is True
            assert "access_token" in data and len(data["access_token"]) > 20
            assert data["token_type"] == "bearer"

            user_obj = data["user"]
            assert user_obj["role"] == expected_role, (
                f"Role mismatch for {email}: expected {expected_role}, got {user_obj.get('role')}"
            )
            if expected_state:
                assert user_obj["state"] == expected_state
            if expected_district:
                assert user_obj["district"] == expected_district

