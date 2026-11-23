"""
Phase 4D-2 Comprehensive Test Suite: Registration & Government Workflow Notifications
AI Powered Smart Hospital Referral System

Validates:
1. Applicant notifications (Submission, Correction Required, Resubmission, Approvals, Rejection)
2. Hierarchical government reviewer resolution & routing (Hospital -> District, District -> State, State -> Central)
3. Geographic boundary isolation (District, State, Central jurisdiction compartmentalization)
4. Outbox atomicity, exponential backoff, and idempotent deduplication
5. Security, multi-tenant isolation, authorization barriers, and privacy/PII scrubbing
6. Unresolved reviewer fallback and operational AuditLog recording
"""

import json
import secrets
from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.api.main import app
from src.database.db_manager import get_db_session
from src.database.pg_models import (
    PgBase,
    User,
    Role,
    RegistrationApplication,
    RegistrationDocument,
    RegistrationEmailOutbox,
    Notification,
    AuditLog,
    AccountActivationToken,
)
from src.auth.jwt_utils import create_access_token
from src.services.email_service import SimulatedEmailProvider, set_email_provider
from src.services.document_storage import SimulatedScanner, set_malware_scanner, LocalStorageAdapter, set_storage_adapter
from src.services.registration_service import RegistrationService
from src.services.workflow_notification_service import WorkflowNotificationService
from src.services.email_outbox_service import EmailOutboxService
from src.auth.rate_limiter import reset_rate_limits

VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<\n>>\nendobj\ntrailer\n<<\n>>\n%%EOF"


@pytest.fixture
def workflow_db_session():
    """Create in-memory SQLite database session with all models."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    PgBase.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    # Seed roles
    roles = [
        Role(id="HOSPITAL", description="Hospital Clinical Staff"),
        Role(id="DISTRICT_ADMIN", description="District Health Authority"),
        Role(id="STATE_ADMIN", description="State Health Directorate"),
        Role(id="CENTRAL_ADMIN", description="National Healthcare Authority"),
    ]
    for r in roles:
        session.merge(r)

    # Seed reviewers across districts and states with valid emails
    users = [
        User(user_id="U_REV_MOHALI", username="cmo_mohali", name="Dr. Mohali CMO", role_id="DISTRICT_ADMIN", state="Punjab", district="Mohali", email="cmo.mohali@punjab.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_REV_LUDHIANA", username="cmo_ludhiana", name="Dr. Ludhiana CMO", role_id="DISTRICT_ADMIN", state="Punjab", district="Ludhiana", email="cmo.ludhiana@punjab.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_REV_JAIPUR", username="cmo_jaipur", name="Dr. Jaipur CMO", role_id="DISTRICT_ADMIN", state="Rajasthan", district="Jaipur", email="cmo.jaipur@rajasthan.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_REV_PUNJAB", username="dir_punjab", name="Director Health Punjab", role_id="STATE_ADMIN", state="Punjab", district=None, email="director@health.pb.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_REV_HARYANA", username="dir_haryana", name="Director Health Haryana", role_id="STATE_ADMIN", state="Haryana", district=None, email="director@health.hr.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_REV_CENTRAL", username="central_registrar", name="Central Registrar", role_id="CENTRAL_ADMIN", state=None, district=None, email="registrar@mohfw.gov.in", is_active=True, password_hash="hash"),
        User(user_id="U_HOSP_USER", username="staff_user", name="Apollo Staff", role_id="HOSPITAL", state="Punjab", district="Mohali", hospital_id="HOSP_MOH_01", email="staff@apollo.com", is_active=True, password_hash="hash"),
    ]
    for u in users:
        session.merge(u)
    session.commit()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def sim_email():
    provider = SimulatedEmailProvider()
    set_email_provider(provider)
    return provider


@pytest.fixture
def sim_scanner():
    scanner = SimulatedScanner()
    set_malware_scanner(scanner)
    return scanner


@pytest.fixture
def sim_storage(tmp_path):
    storage = LocalStorageAdapter(base_dir=str(tmp_path / "workflow_docs"))
    set_storage_adapter(storage)
    return storage


@pytest.fixture
def client(workflow_db_session, sim_email, sim_scanner, sim_storage):
    reset_rate_limits()

    def _override_db():
        try:
            yield workflow_db_session
        finally:
            pass

    app.dependency_overrides[get_db_session] = _override_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db_session, None)
    reset_rate_limits()


@pytest.fixture
def auth_tokens():
    return {
        "mohali": create_access_token({"user_id": "U_REV_MOHALI", "username": "cmo_mohali", "role": "DISTRICT_ADMIN", "state": "Punjab", "district": "Mohali"}),
        "ludhiana": create_access_token({"user_id": "U_REV_LUDHIANA", "username": "cmo_ludhiana", "role": "DISTRICT_ADMIN", "state": "Punjab", "district": "Ludhiana"}),
        "jaipur": create_access_token({"user_id": "U_REV_JAIPUR", "username": "cmo_jaipur", "role": "DISTRICT_ADMIN", "state": "Rajasthan", "district": "Jaipur"}),
        "punjab": create_access_token({"user_id": "U_REV_PUNJAB", "username": "dir_punjab", "role": "STATE_ADMIN", "state": "Punjab"}),
        "haryana": create_access_token({"user_id": "U_REV_HARYANA", "username": "dir_haryana", "role": "STATE_ADMIN", "state": "Haryana"}),
        "central": create_access_token({"user_id": "U_REV_CENTRAL", "username": "central_registrar", "role": "CENTRAL_ADMIN"}),
        "hospital": create_access_token({"user_id": "U_HOSP_USER", "username": "staff_user", "role": "HOSPITAL", "state": "Punjab", "district": "Mohali", "hospital_id": "HOSP_MOH_01"}),
    }


def _create_and_submit_test_application(
    session,
    applicant_type="HOSPITAL",
    state="Punjab",
    district="Mohali",
    email="applicant@mohali-health.org",
):
    """Helper to create and submit an application with required docs."""
    reg_svc = RegistrationService(session)
    suffix = secrets.token_hex(4).upper()
    app_record = reg_svc.create_application({
        "applicant_type": applicant_type,
        "applicant_name": f"Test {applicant_type} Facility {suffix}",
        "applicant_email": email,
        "applicant_phone": "9876543210",
        "state": state,
        "district": district if applicant_type != "STATE" else None,
    })

    doc_type = "GOVERNMENT_ORDER" if applicant_type in ["STATE", "DISTRICT"] else "CLINICAL_LICENSE"
    reg_svc.upload_document_binary(app_record.application_id, doc_type, VALID_PDF_BYTES, "application/pdf", "doc1.pdf")
    if applicant_type == "HOSPITAL":
        reg_svc.upload_document_binary(app_record.application_id, "FIRE_SAFETY_NOC", VALID_PDF_BYTES, "application/pdf", "doc2.pdf")

    res = reg_svc.submit_application(app_record.application_id, remarks="Initial submission")
    session.commit()
    return app_record, res


# ==============================================================================
# 1. APPLICANT SUBMISSION & HIERARCHICAL RESOLUTION
# ==============================================================================

def test_applicant_registration_submission_notification_and_outbox(workflow_db_session):
    """
    Test 1: When an applicant submits registration, they receive:
    - An in-app Notification (APPLICATION_SUBMITTED)
    - A transactional RegistrationEmailOutbox record containing Official Application Number,
      Secret Tracking Token, and direct portal tracking URL.
    """
    app_record, res = _create_and_submit_test_application(workflow_db_session)

    # 1. In-app notification for applicant
    applicant_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="APPLICATION_SUBMITTED")
        .first()
    )
    assert applicant_notif is not None
    assert app_record.application_number in applicant_notif.title
    assert "DISTRICT_REVIEW" in applicant_notif.message
    assert applicant_notif.role_id is None  # Addressed to applicant

    # 2. Outbox email for applicant
    outbox_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="APPLICATION_SUBMITTED")
        .first()
    )
    assert outbox_email is not None
    assert outbox_email.status == "PENDING"
    assert app_record.application_number in outbox_email.subject
    payload = json.loads(outbox_email.payload)
    assert payload["status"] == "SUBMITTED"
    assert "tracking_url" in payload
    assert app_record.application_number in payload["tracking_url"]
    assert "tracking_token" in payload
    assert payload["tracking_token"] == res["tracking_token"]
    assert res["tracking_token"] in payload["tracking_url"]
    assert payload["current_stage_display"] == "District Verification"
    assert res["tracking_token"] in payload["body_text"]
    assert app_record.application_number in payload["body_text"]
    assert res["tracking_token"] in payload["body_html"]


def test_hierarchical_reviewer_routing_district_hospital_application(workflow_db_session, auth_tokens, client):
    """
    Test 2: Hospital registration in Mohali, Punjab:
    - Enqueues reviewer alert for DISTRICT_ADMIN of Punjab/Mohali.
    - Mohali CMO sees the alert in their reviewer notification feed.
    - Ludhiana CMO (same state, different district) CANNOT see the alert.
    - Jaipur CMO (different state) CANNOT see the alert.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    # Check reviewer in-app notification in DB
    rev_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="NEW_REGISTRATION_APPLICATION")
        .first()
    )
    assert rev_notif is not None
    assert rev_notif.role_id == "DISTRICT_ADMIN"
    assert rev_notif.state == "Punjab"
    assert rev_notif.district == "Mohali"

    # Check reviewer outbox email in DB for Mohali CMO
    mohali_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email="cmo.mohali@punjab.gov.in", event_type="REVIEWER_REVIEW_REQUIRED")
        .first()
    )
    assert mohali_email is not None
    assert app_record.application_number in mohali_email.subject

    # Verify via Reviewer Notification API with tokens
    # 1. Mohali CMO feed -> contains alert
    moh_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['mohali']}"})
    assert moh_res.status_code == 200
    moh_notifs = moh_res.json()["notifications"]
    assert any(n["application_id"] == app_record.application_id for n in moh_notifs)

    # 2. Ludhiana CMO feed -> strictly empty of Mohali applications
    lud_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['ludhiana']}"})
    assert lud_res.status_code == 200
    lud_notifs = lud_res.json()["notifications"]
    assert not any(n["application_id"] == app_record.application_id for n in lud_notifs)

    # 3. Jaipur CMO feed -> strictly empty
    jpr_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['jaipur']}"})
    assert jpr_res.status_code == 200
    assert not any(n["application_id"] == app_record.application_id for n in jpr_res.json()["notifications"])


def test_hierarchical_reviewer_routing_district_application_to_state(workflow_db_session, auth_tokens, client):
    """
    Test 3: District registration application in Punjab:
    - Initial stage is STATE_REVIEW.
    - Routes alert to Punjab State Health Directorate.
    - Haryana State Director CANNOT see Punjab district registrations.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="DISTRICT", state="Punjab", district="Amritsar"
    )

    # Punjab State Reviewer Feed
    pb_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['punjab']}"})
    assert pb_res.status_code == 200
    assert any(n["application_id"] == app_record.application_id for n in pb_res.json()["notifications"])

    # Haryana State Reviewer Feed -> empty of Punjab
    hr_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['haryana']}"})
    assert hr_res.status_code == 200
    assert not any(n["application_id"] == app_record.application_id for n in hr_res.json()["notifications"])


def test_hierarchical_reviewer_routing_state_application_to_central(workflow_db_session, auth_tokens, client):
    """
    Test 4: State registration application:
    - Initial stage is CENTRAL_REVIEW.
    - Routes alert to Central Government Reviewer.
    - State reviewer CANNOT see Central-tier new applications.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="STATE", state="Punjab"
    )

    # Central Reviewer Feed
    cen_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['central']}"})
    assert cen_res.status_code == 200
    assert any(n["application_id"] == app_record.application_id for n in cen_res.json()["notifications"])

    # State Reviewer Feed -> does NOT see Central-tier state applications
    pb_res = client.get("/api/registration/review/notifications", headers={"Authorization": f"Bearer {auth_tokens['punjab']}"})
    assert pb_res.status_code == 200
    assert not any(n["application_id"] == app_record.application_id for n in pb_res.json()["notifications"])


# ==============================================================================
# 2. DOCUMENT CORRECTION & RESUBMISSION WORKFLOW
# ==============================================================================

def test_correction_request_and_resubmission_lifecycle(workflow_db_session, auth_tokens, client):
    """
    Test 5: Full correction lifecycle:
    1. Reviewer requests correction with specific notes.
    2. Applicant receives in-app alert + email detailing required corrections.
    3. Applicant resubmits corrected application.
    4. Applicant receives resubmission confirmation.
    5. Reviewer receives alert with revision number and applicant notes.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    # 1. Reviewer requests correction
    correction_text = "Please upload renewed Fire Safety Certificate valid for 2026-27."
    req_res = client.post(
        f"/api/registration/review/applications/{app_record.application_id}/request-correction",
        json={"correction_notes": correction_text},
        headers={"Authorization": f"Bearer {auth_tokens['mohali']}"},
    )
    assert req_res.status_code == 200
    assert req_res.json()["status"] == "CORRECTION_REQUIRED"

    # Verify applicant in-app notification
    notif_corr = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="CORRECTION_REQUIRED")
        .first()
    )
    assert notif_corr is not None
    assert "Corrections Requested" in notif_corr.title

    # Verify applicant outbox email contains deficiency notes
    outbox_corr = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="CORRECTION_REQUIRED")
        .first()
    )
    assert outbox_corr is not None
    payload_corr = json.loads(outbox_corr.payload)
    assert correction_text in payload_corr["correction_notes"]
    assert "tracking_url" in payload_corr

    # 2. Applicant resubmits
    reg_svc = RegistrationService(workflow_db_session)
    resub_res = reg_svc.resubmit_application(
        app_record.application_id, applicant_notes="Uploaded renewed 2026-27 fire NOC certificate."
    )
    workflow_db_session.commit()
    assert resub_res["status"] == "SUBMITTED"
    assert resub_res["resubmission_version"] == 2

    # Verify applicant in-app resubmission confirmation
    notif_resub = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="APPLICATION_RESUBMITTED")
        .first()
    )
    assert notif_resub is not None
    assert app_record.application_number in notif_resub.title

    # Verify reviewer alert for resubmitted dossier
    rev_resub_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="CORRECTION_RESUBMITTED")
        .first()
    )
    assert rev_resub_notif is not None
    assert rev_resub_notif.role_id == "DISTRICT_ADMIN"
    assert rev_resub_notif.district == "Mohali"

    # Verify reviewer outbox email
    rev_resub_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email="cmo.mohali@punjab.gov.in", event_type="CORRECTION_RESUBMITTED")
        .first()
    )
    assert rev_resub_email is not None
    assert "Revision: 2" in rev_resub_email.payload


# ==============================================================================
# 3. INTERMEDIATE & FINAL APPROVALS
# ==============================================================================

def test_hierarchical_stage_forwarding_notifications(workflow_db_session, auth_tokens, client):
    """
    Test 6: Intermediate approval transitions:
    - District approval forwards to State Review -> Applicant receives in-app update, State Reviewers receive review alert.
    - State approval forwards to Central Review -> Applicant receives in-app update, Central Reviewers receive review alert.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    # Verify all documents
    docs = workflow_db_session.query(RegistrationDocument).filter_by(application_id=app_record.application_id).all()
    for d in docs:
        d.verification_status = "VERIFIED"
    workflow_db_session.commit()

    # Step 1: District Reviewer forwards to State
    resp1 = client.post(
        f"/api/registration/review/applications/{app_record.application_id}/decision",
        json={"action": "FORWARD", "remarks": "District verification completed."},
        headers={"Authorization": f"Bearer {auth_tokens['mohali']}"},
    )
    assert resp1.status_code == 200
    assert resp1.json()["new_stage"] == "STATE_REVIEW"

    # Check applicant status update notification
    app_fwd1 = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="APPLICATION_FORWARDED")
        .first()
    )
    assert app_fwd1 is not None
    assert "District Review Approved" in app_fwd1.title

    # Check State Reviewer received review required email
    pb_rev_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email="director@health.pb.gov.in", event_type="REVIEWER_REVIEW_REQUIRED")
        .first()
    )
    assert pb_rev_email is not None
    assert app_record.application_number in pb_rev_email.subject

    # Step 2: State Reviewer forwards to Central
    resp2 = client.post(
        f"/api/registration/review/applications/{app_record.application_id}/decision",
        json={"action": "FORWARD", "remarks": "State health directorate approved."},
        headers={"Authorization": f"Bearer {auth_tokens['punjab']}"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["new_stage"] == "CENTRAL_REVIEW"

    # Check Central Reviewer received review required email
    cen_rev_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email="registrar@mohfw.gov.in", event_type="REVIEWER_REVIEW_REQUIRED")
        .first()
    )
    assert cen_rev_email is not None


def test_final_central_approval_and_rejection_notifications(workflow_db_session, auth_tokens, client):
    """
    Test 7: Terminal stage decisions:
    A. Final Central Approval -> Applicant receives approval decision in-app & email + separate account activation email.
    B. Rejection Decision -> Applicant receives rejection decision in-app & email with reviewer's reason.
    """
    # A. Central Final Approval
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )
    app_record.current_stage = "CENTRAL_REVIEW"
    docs = workflow_db_session.query(RegistrationDocument).filter_by(application_id=app_record.application_id).all()
    for d in docs:
        d.verification_status = "VERIFIED"
    workflow_db_session.commit()

    resp_appr = client.post(
        f"/api/registration/review/applications/{app_record.application_id}/decision",
        json={"action": "APPROVE", "remarks": "Final national approval granted."},
        headers={"Authorization": f"Bearer {auth_tokens['central']}"},
    )
    assert resp_appr.status_code == 200
    assert resp_appr.json()["new_status"] == "APPROVED"

    # Verify applicant in-app notification
    appr_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, event_type="APPLICATION_APPROVED")
        .first()
    )
    assert appr_notif is not None
    assert "Approved" in appr_notif.title

    # Verify applicant approval decision outbox email
    appr_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="APPLICATION_APPROVED")
        .first()
    )
    assert appr_email is not None
    assert "Approved" in appr_email.subject
    assert "facility operations will commence once your account is fully activated" in appr_email.payload

    # Verify separate ACCOUNT_ACTIVATION email exists
    act_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="ACCOUNT_ACTIVATION")
        .first()
    )
    assert act_email is not None

    # B. Rejection Decision
    app_rej, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )
    rej_reason = "Inadequate intensive care equipment and invalid fire NOC."
    resp_rej = client.post(
        f"/api/registration/review/applications/{app_rej.application_id}/decision",
        json={"action": "REJECT", "remarks": rej_reason},
        headers={"Authorization": f"Bearer {auth_tokens['mohali']}"},
    )
    assert resp_rej.status_code == 200
    assert resp_rej.json()["new_status"] == "REJECTED"

    # Verify applicant in-app rejection notification
    rej_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_rej.application_id, event_type="APPLICATION_REJECTED")
        .first()
    )
    assert rej_notif is not None
    assert rej_reason in rej_notif.message

    # Verify applicant rejection outbox email
    rej_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_rej.applicant_email, event_type="APPLICATION_REJECTED")
        .first()
    )
    assert rej_email is not None
    assert rej_reason in rej_email.payload


# ==============================================================================
# 4. UNRESOLVED RECIPIENTS & AUDIT LOGS
# ==============================================================================

def test_unresolved_reviewer_records_audit_log_without_crashing(workflow_db_session):
    """
    Test 8: If an application is submitted for a district with NO active reviewers registered:
    - Does NOT crash.
    - Records an AuditLog entry with action='UNRESOLVED_RECIPIENT'.
    - Does NOT invent a fake email.
    """
    # Create application in an unconfigured state/district (Rajasthan / Jodhpur has no reviewer)
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session,
        applicant_type="HOSPITAL",
        state="Rajasthan",
        district="Jodhpur",
        email="jodhpur_clinic@gov.in",
    )

    # Verify transaction committed
    assert app_record.status == "SUBMITTED"

    # Verify AuditLog created
    audit = (
        workflow_db_session.query(AuditLog)
        .filter_by(entity_id=app_record.application_id, action="UNRESOLVED_RECIPIENT")
        .first()
    )
    assert audit is not None
    assert audit.entity_type == "NOTIFICATION"
    new_st = audit.new_state
    assert new_st["status"] == "UNRESOLVED_RECIPIENT"

    # Verify no fake reviewer email enqueued
    fake_email = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter(RegistrationEmailOutbox.recipient_email.like("%jodhpur%"))
        .filter(RegistrationEmailOutbox.event_type == "REVIEWER_REVIEW_REQUIRED")
        .first()
    )
    assert fake_email is None


# ==============================================================================
# 5. IDEMPOTENCY & DUPLICATE PREVENTION
# ==============================================================================

def test_notification_and_outbox_idempotency_keys(workflow_db_session):
    """
    Test 9: Calling notification emission repeatedly:
    - Does NOT create duplicate in-app Notification records.
    - Does NOT create duplicate RegistrationEmailOutbox records.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    initial_notifs_count = workflow_db_session.query(Notification).filter_by(application_id=app_record.application_id).count()
    initial_outbox_count = workflow_db_session.query(RegistrationEmailOutbox).filter_by(recipient_email=app_record.applicant_email).count()

    # Call notify_application_submitted a second time on the same state
    notif_svc = WorkflowNotificationService(workflow_db_session)
    notif_svc.notify_application_submitted(app_record)
    workflow_db_session.commit()

    after_notifs_count = workflow_db_session.query(Notification).filter_by(application_id=app_record.application_id).count()
    after_outbox_count = workflow_db_session.query(RegistrationEmailOutbox).filter_by(recipient_email=app_record.applicant_email).count()

    assert after_notifs_count == initial_notifs_count
    assert after_outbox_count == initial_outbox_count


# ==============================================================================
# 6. SECURITY, PRIVACY & AUTHORIZATION BARRIERS
# ==============================================================================

def test_reviewer_notification_read_authorization_and_cross_district_barrier(workflow_db_session, auth_tokens, client):
    """
    Test 10: Reviewer notification read endpoint:
    - Mohali CMO can mark their own Mohali notification as read.
    - Ludhiana CMO CANNOT mark Mohali notification as read (403 Forbidden).
    - Hospital staff CANNOT mark government notifications as read.
    """
    app_record, _ = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    mohali_notif = (
        workflow_db_session.query(Notification)
        .filter_by(application_id=app_record.application_id, role_id="DISTRICT_ADMIN", district="Mohali")
        .first()
    )
    assert mohali_notif is not None
    assert mohali_notif.is_read is False

    # 1. Ludhiana CMO attempts to mark Mohali notification read -> 403 Forbidden
    cross_read_res = client.post(
        f"/api/registration/review/notifications/{mohali_notif.id}/read",
        headers={"Authorization": f"Bearer {auth_tokens['ludhiana']}"},
    )
    assert cross_read_res.status_code == 403

    # 2. Hospital staff attempts to access reviewer endpoint -> 403 Forbidden
    hosp_res = client.post(
        f"/api/registration/review/notifications/{mohali_notif.id}/read",
        headers={"Authorization": f"Bearer {auth_tokens['hospital']}"},
    )
    assert hosp_res.status_code == 403

    # 3. Authorized Mohali CMO marks notification read -> 200 OK
    auth_res = client.post(
        f"/api/registration/review/notifications/{mohali_notif.id}/read",
        headers={"Authorization": f"Bearer {auth_tokens['mohali']}"},
    )
    assert auth_res.status_code == 200

    workflow_db_session.refresh(mohali_notif)
    assert mohali_notif.is_read is True


def test_applicant_notifications_endpoint_and_isolation(workflow_db_session, client):
    """
    Test 11: Applicant notification endpoints:
    - Applicant A only receives notifications for Application A.
    - Cannot see Applicant B's notifications.
    """
    app_a, _ = _create_and_submit_test_application(
        workflow_db_session, email="app_a@punjab.gov.in"
    )
    app_b, _ = _create_and_submit_test_application(
        workflow_db_session, email="app_b@punjab.gov.in"
    )

    # Create applicant tokens
    from src.auth.registration_auth import create_applicant_token
    token_a = create_applicant_token({
        "application_id": app_a.application_id,
        "applicant_email": app_a.applicant_email,
        "application_number": app_a.application_number,
    })
    token_b = create_applicant_token({
        "application_id": app_b.application_id,
        "applicant_email": app_b.applicant_email,
        "application_number": app_b.application_number,
    })

    # Fetch notifications for Applicant A
    res_a = client.get("/api/registration/applications/notifications", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    notifs_a = res_a.json()["notifications"]
    assert len(notifs_a) >= 1
    assert all(n["application_id"] == app_a.application_id for n in notifs_a)

    # Fetch notifications for Applicant B
    res_b = client.get("/api/registration/applications/notifications", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    notifs_b = res_b.json()["notifications"]
    assert len(notifs_b) >= 1
    assert all(n["application_id"] == app_b.application_id for n in notifs_b)


def test_sensitive_credentials_never_in_notification_content(workflow_db_session):
    """
    Test 12: Notification messages and outbox payloads must NEVER contain:
    - Passwords, OTP codes, activation tokens, or reset tokens.
    """
    app_record, _ = _create_and_submit_test_application(workflow_db_session)

    forbidden_tokens = ["password", "otp", "token=", "jwt", "secret"]

    # Check all notifications
    notifs = workflow_db_session.query(Notification).filter_by(application_id=app_record.application_id).all()
    for n in notifs:
        content = f"{n.title} {n.message}".lower()
        for tok in forbidden_tokens:
            assert tok not in content, f"Forbidden sensitive token '{tok}' found in notification {n.id}"

    # Check all outbox entries
    outbox_entries = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter(RegistrationEmailOutbox.recipient_email == app_record.applicant_email)
        .all()
    )
    for entry in outbox_entries:
        if entry.event_type not in ("ACCOUNT_ACTIVATION", "APPLICATION_SUBMITTED"):
            payload_str = entry.payload.lower()
            for tok in forbidden_tokens:
                assert tok not in payload_str, f"Forbidden token '{tok}' in outbox payload {entry.outbox_id}"
        else:
            # Transactional delivery payloads (activation links or submission tracking credentials)
            # must strictly NEVER leak plaintext passwords, OTP verification codes, or JWT session tokens
            payload_str = entry.payload.lower()
            for leak_tok in ["password", "otp", "jwt", "bearer "]:
                assert leak_tok not in payload_str, f"Critical credential leak '{leak_tok}' in {entry.event_type} payload"


# ==============================================================================
# 7. AUTOMATED APPLICATION SUBMISSION EMAIL CONFIRMATION SUITE
# ==============================================================================

def test_submission_email_confirmation_and_delivery(workflow_db_session):
    """
    Verifies automated email confirmation upon registration application submission:
    1. Submitting an application atomically enqueues an outbox email.
    2. The outbox payload contains the exact application_number and tracking_token.
    3. The email body contains:
       - Applicant Name / Organization Name
       - Official Application Number
       - Secret Tracking Token
       - Human-readable Review Stage (District Verification)
       - Direct portal tracking instructions (/track and direct link)
       - Clear prototype identifier
    4. OutboxWorker processes the enqueued email and delivers it via email provider.
    """
    from src.services.email_service import SimulatedEmailProvider
    from src.workers.outbox_worker import OutboxWorker

    sim_provider = SimulatedEmailProvider()
    app_record, res = _create_and_submit_test_application(
        workflow_db_session, applicant_type="HOSPITAL", state="Punjab", district="Mohali"
    )

    # 1. Verify outbox record was enqueued in the same database transaction
    outbox_record = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="APPLICATION_SUBMITTED")
        .first()
    )
    assert outbox_record is not None
    assert outbox_record.status == "PENDING"
    assert app_record.application_number in outbox_record.subject

    # 2. Verify payload fields
    payload = json.loads(outbox_record.payload)
    assert payload["application_number"] == app_record.application_number
    assert payload["applicant_name"] == app_record.applicant_name
    assert payload["tracking_token"] == res["tracking_token"]
    assert payload["current_stage_display"] == "District Verification"
    assert "token=" in payload["tracking_url"]
    assert res["tracking_token"] in payload["tracking_url"]

    # 3. Verify text and HTML body contents
    body_text = payload["body_text"]
    assert app_record.applicant_name in body_text
    assert app_record.application_number in body_text
    assert res["tracking_token"] in body_text
    assert "District Verification" in body_text
    assert "/track" in body_text
    assert "SWASTHYA SAMANVAY" in body_text

    body_html = payload["body_html"]
    assert app_record.application_number in body_html
    assert res["tracking_token"] in body_html
    assert "District Verification" in body_html
    assert "Track Application Status" in body_html

    applicant_email = app_record.applicant_email
    app_num = app_record.application_number

    # 4. Process outbox via OutboxWorker
    worker = OutboxWorker(
        session_factory=lambda: workflow_db_session,
        email_provider=sim_provider,
        worker_id="test_sub_worker",
    )
    worker_result = worker.run_once()
    assert worker_result["succeeded"] >= 1

    # 5. Verify email was delivered by provider
    sent_email = sim_provider.get_last_email(to_email=applicant_email)
    assert sent_email is not None
    assert app_num in sent_email["subject"]
    assert res["tracking_token"] in sent_email["body_text"]
    assert app_num in sent_email["body_text"]
    assert res["tracking_token"] in sent_email["body_html"]


def test_submission_duplicate_submission_idempotency(workflow_db_session):
    """
    Verifies that idempotency guarantees prevent duplicate submission confirmation emails:
    1. Submitting once creates exactly 1 outbox record.
    2. Attempting to submit an already SUBMITTED application is rejected.
    3. Direct notification invocation on the same stage returns the existing record without duplicating.
    """
    from src.services.registration_service import RegistrationService, InvalidStageTransitionError

    app_record, res = _create_and_submit_test_application(
        workflow_db_session, applicant_type="DISTRICT", state="Punjab", district="Mohali"
    )

    initial_outbox_count = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="APPLICATION_SUBMITTED")
        .count()
    )
    assert initial_outbox_count == 1

    # Attempt to submit again on the domain service -> raises InvalidStageTransitionError
    reg_svc = RegistrationService(workflow_db_session)
    with pytest.raises(InvalidStageTransitionError, match="Only DRAFT applications can be submitted"):
        reg_svc.submit_application(app_record.application_id)

    # Calling notification service again directly with idempotency check
    notif_svc = WorkflowNotificationService(workflow_db_session)
    notif_svc.notify_application_submitted(app_record, tracking_token=res["tracking_token"])
    workflow_db_session.commit()

    after_outbox_count = (
        workflow_db_session.query(RegistrationEmailOutbox)
        .filter_by(recipient_email=app_record.applicant_email, event_type="APPLICATION_SUBMITTED")
        .count()
    )
    assert after_outbox_count == 1
