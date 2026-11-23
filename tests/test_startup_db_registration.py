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


def test_seed_creates_central_state_district_and_hospital_accounts():
    """Verify that startup seeding populates all 4 roles, administrative reviewers, and hospitals cleanly."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_database(engine)

    with engine.connect() as conn:
        # Check Roles
        roles = [r[0] for r in conn.execute(text("SELECT id FROM roles")).fetchall()]
        for expected_role in ["CENTRAL_ADMIN", "STATE_ADMIN", "DISTRICT_ADMIN", "HOSPITAL"]:
            assert expected_role in roles, f"Role {expected_role} missing!"

        # Check Central, State, District Reviewers
        user_emails = [u[0] for u in conn.execute(text("SELECT email FROM users")).fetchall()]
        assert "central.admin@swasthya.gov.in" in user_emails
        assert "state.bihar@swasthya.gov.in" in user_emails
        assert "state.punjab@swasthya.gov.in" in user_emails
        assert "district.purnea@swasthya.gov.in" in user_emails
        assert "district.patna@swasthya.gov.in" in user_emails
        assert "district.amritsar@swasthya.gov.in" in user_emails

        # Check Hospitals (10 in Purnea, 15 multi-city = 25 total)
        hosp_cnt = conn.execute(text("SELECT count(*) FROM hospitals")).scalar()
        assert hosp_cnt == 25, f"Expected 25 hospitals, found {hosp_cnt}"

        # Check Purnea Hospitals
        purnea_cnt = conn.execute(
            text("SELECT count(*) FROM hospitals WHERE LOWER(district) = 'purnea'")
        ).scalar()
        assert purnea_cnt == 10, f"Expected 10 Purnea hospitals, found {purnea_cnt}"


def test_reviewer_and_hospital_logins_succeed_with_seeded_credentials():
    """Verify that seeded administrative reviewers and hospital accounts authenticate cleanly with HTTP 200."""
    from src.api.main import app

    with TestClient(app) as client:
        accounts = [
            ("central.admin@swasthya.gov.in", "Central@2026", "CENTRAL_ADMIN"),
            ("state.bihar@swasthya.gov.in", "StateBihar@2026", "STATE_ADMIN"),
            ("district.purnea@swasthya.gov.in", "DistPurnea@2026", "DISTRICT_ADMIN"),
            ("purnea.hosp1@swasthya.gov.in", "Hospital@2026", "HOSPITAL"),
        ]

        for username, password, expected_role in accounts:
            response = client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
            assert response.status_code == 200, (
                f"Expected 200 OK for {username}, got {response.status_code}: {response.text}"
            )
            data = response.json()
            assert data["user"]["role"] == expected_role


def test_seeding_is_idempotent_and_invokes_zero_emails():
    """Verify that multiple seed invocations are idempotent and make zero email provider calls."""
    from unittest.mock import patch
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    with patch("src.services.email_service.get_email_provider") as mock_get_provider:
        # First run seeds the database
        seed_baseline_reference_data(engine)
        # Second run should be a no-op due to _seed_metadata marker
        seed_baseline_reference_data(engine)

        # Zero email provider calls
        mock_get_provider.assert_not_called()

    with engine.connect() as conn:
        marker = conn.execute(
            text("SELECT version FROM _seed_metadata WHERE version = 'seed_v2_clean_network'")
        ).fetchone()
        assert marker is not None, "Marker seed_v2_clean_network was not recorded in _seed_metadata!"


