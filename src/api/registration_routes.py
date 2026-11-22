"""
Registration System API Endpoints & Router
AI Powered Smart Hospital Referral System - Phase 1 Task 1D

Provides FastAPI routes for:
- Part A: Applicant authentication (OTP request, OTP verify, session tokens, logout)
- Part B: Applicant lifecycle (create State/District/Hospital application, update draft, upload documents, submit, resubmit)
- Part C: Secure public tracking
- Part D: Hierarchical reviewer workflows (assigned applications, document verification, stage decisions, correction requests)
"""

import os
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Request, Header, Query, status, UploadFile, File, Form, Response, BackgroundTasks
from sqlalchemy.orm import Session

from src.database.db_manager import get_db_session
from src.database.pg_models import (
    RegistrationApplication,
    RegistrationDocument,
    ApprovalHistory,
)
from src.services.registration_service import RegistrationService
from src.services.otp_service import OTPService
from src.services.document_storage import (
    MalwareDetectedError,
    MalwareScanServiceUnavailableError,
    MalwareScanError,
    DocumentStorageError,
)
from src.services.account_provisioning_service import (
    AccountProvisioningService,
    ActivationTokenError,
    PasswordComplexityError,
    ProvisioningError,
)
from src.services.email_service import EmailDeliveryError
from src.auth.registration_auth import (
    create_applicant_token,
    require_applicant_user,
    require_reviewer_user,
    get_caller_user_context,
)
from src.auth.rate_limiter import check_rate_limit, record_failure, revoke_token
from src.services.registration_exceptions import (
    RegistrationServiceError,
    ValidationError,
    InvalidHierarchyError,
    DuplicateApplicationError,
    ApplicationNotFoundError,
    DocumentError,
    UnauthorizedReviewerError,
    GeographicAccessError,
    SelfApprovalError,
    InvalidStageTransitionError,
    IneligibleForApprovalError,
    TrackingTokenError,
)
from src.api.registration_schemas import (
    RequestOTPRequest,
    RequestOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    CreateStateApplicationRequest,
    CreateDistrictApplicationRequest,
    CreateHospitalApplicationRequest,
    ApplicationCreationResponse,
    UpdateDraftApplicationRequest,
    SubmitApplicationRequest,
    SubmitApplicationResponse,
    ResubmitApplicationRequest,
    ResubmitApplicationResponse,
    UploadDocumentMetadataRequest,
    DocumentMetadataResponse,
    ApplicantApplicationViewResponse,
    PublicTrackingResponse,
    MilestoneResponse,
    ReviewerApplicationSummary,
    ReviewerApplicationListResponse,
    VerifyDocumentRequest,
    ReviewDecisionRequest,
    RequestCorrectionRequest,
    ReviewDecisionResponse,
    ActivateAccountRequest,
    ActivateAccountResponse,
    ResendActivationRequest,
    ResendActivationResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PasswordResetConfirmRequest,
    PasswordResetConfirmResponse,
    OutboxProcessResponse,
)

logger = logging.getLogger("registration_api")
router = APIRouter(prefix="/api/registration", tags=["Registration"])


def _map_exception(exc: Exception) -> HTTPException:
    """Map domain exceptions to appropriate HTTP status codes."""
    logger.exception("Registration API Exception: %s", exc)
    if isinstance(exc, (ValidationError, PasswordComplexityError, MalwareDetectedError)):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    elif isinstance(exc, MalwareScanServiceUnavailableError):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    elif isinstance(exc, MalwareScanError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))
    elif isinstance(exc, ApplicationNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    elif isinstance(exc, DuplicateApplicationError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    elif isinstance(exc, (UnauthorizedReviewerError, GeographicAccessError, SelfApprovalError)):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    elif isinstance(exc, TrackingTokenError):
        # Uniform 404 response eliminates application number enumeration oracles
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    elif isinstance(exc, (ActivationTokenError, ProvisioningError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    elif isinstance(exc, DocumentStorageError):
        return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    elif isinstance(exc, (InvalidStageTransitionError, DocumentError, IneligibleForApprovalError, InvalidHierarchyError)):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    elif isinstance(exc, RegistrationServiceError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


def _get_client_ip(request: Request) -> str:
    """
    Extract client IP safely.
    Honors X-Forwarded-For ONLY when SIH_TRUST_PROXY is explicitly enabled.
    Otherwise defaults to direct connection IP (request.client.host).
    """
    trust_proxy = os.getenv("SIH_TRUST_PROXY", "false").lower().strip() in ("1", "true", "yes")
    direct_ip = request.client.host if request and request.client else "127.0.0.1"

    if trust_proxy and request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            client_candidate = forwarded.split(",")[0].strip()
            if client_candidate:
                return client_candidate
    return direct_ip


# Rate limiting configurations (configurable via environment variables)
OTP_IP_MAX_ATTEMPTS = int(os.getenv("SIH_OTP_IP_MAX_ATTEMPTS", "15"))
OTP_IP_WINDOW = int(os.getenv("SIH_OTP_IP_WINDOW_SECONDS", "300"))
OTP_TARGET_MAX_ATTEMPTS = int(os.getenv("SIH_OTP_TARGET_MAX_ATTEMPTS", "5"))
OTP_TARGET_WINDOW = int(os.getenv("SIH_OTP_TARGET_WINDOW_SECONDS", "300"))

APP_CREATE_MAX_ATTEMPTS = int(os.getenv("SIH_APP_CREATE_MAX_ATTEMPTS", "10"))
APP_CREATE_WINDOW = int(os.getenv("SIH_APP_CREATE_WINDOW_SECONDS", "300"))

TRACK_MAX_ATTEMPTS = int(os.getenv("SIH_TRACK_MAX_ATTEMPTS", "30"))
TRACK_WINDOW = int(os.getenv("SIH_TRACK_WINDOW_SECONDS", "60"))


# ============================================================
# PART A: APPLICANT AUTHENTICATION ENDPOINTS
# ============================================================

@router.post("/auth/otp/request", response_model=RequestOTPResponse)
def request_applicant_otp(
    payload: RequestOTPRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Request a 6-digit OTP for applicant authentication or portal access.
    Dual-key rate-limited per client IP and normalized contact target before OTP generation.
    """
    client_ip = _get_client_ip(request)
    target = payload.contact_target.strip().lower()

    # 1. Independent IP-level rate limit (blocks OTP spray across multiple emails from single IP)
    check_rate_limit(f"otp_req_ip:{client_ip}", max_attempts=OTP_IP_MAX_ATTEMPTS, window_seconds=OTP_IP_WINDOW)
    record_failure(f"otp_req_ip:{client_ip}", window_seconds=OTP_IP_WINDOW)

    # 2. Independent target-level rate limit (blocks targeted flooding of a specific email/phone)
    check_rate_limit(f"otp_req_tgt:{target}", max_attempts=OTP_TARGET_MAX_ATTEMPTS, window_seconds=OTP_TARGET_WINDOW)
    record_failure(f"otp_req_tgt:{target}", window_seconds=OTP_TARGET_WINDOW)

    # If application_number is specified, verify that the contact target matches the application
    if payload.application_number:
        app = (
            db.query(RegistrationApplication)
            .filter_by(application_number=payload.application_number.strip())
            .first()
        )
        if not app:
            raise HTTPException(status_code=404, detail="Application number not found.")

        if target != app.applicant_email.lower() and target != app.applicant_phone:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contact target does not match the designated applicant for this application.",
            )

    otp_service = OTPService(db)
    try:
        result = otp_service.request_otp(
            contact_target=target,
            channel=payload.channel,
            purpose=payload.purpose,
            application_number=payload.application_number,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return RequestOTPResponse(
        token_id=result["token_id"],
        contact_target=result["contact_target"],
        channel=result["channel"],
        resend_available_in_seconds=result["resend_available_in_seconds"],
        expires_in_seconds=result["expires_in_seconds"],
        message="OTP successfully generated and dispatched.",
    )


@router.post("/auth/otp/verify", response_model=VerifyOTPResponse)
def verify_applicant_otp(
    payload: VerifyOTPRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Verify OTP and issue a separate, restricted APPLICANT JWT session token.
    Rate-limited to prevent brute-force attacks.
    Enforces strict application-to-token binding.
    """
    client_ip = _get_client_ip(request)
    rate_key = f"otp_verify:{client_ip}:{payload.token_id}"
    check_rate_limit(rate_key, max_attempts=10, window_seconds=300)

    app = None
    if payload.application_number:
        app = (
            db.query(RegistrationApplication)
            .filter_by(application_number=payload.application_number.strip())
            .first()
        )
        if not app:
            raise HTTPException(status_code=404, detail="Application number not found.")

    otp_service = OTPService(db)
    try:
        contact_target = otp_service.verify_otp(
            token_id=payload.token_id,
            otp=payload.otp,
            purpose=payload.purpose,
            expected_application_id=app.application_id if app else None,
        )
        db.commit()
    except ValidationError as e:
        record_failure(rate_key, window_seconds=300)
        db.commit()
        raise _map_exception(e)
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    applicant_token = None
    if app:
        target = contact_target.strip().lower()
        if target != app.applicant_email.lower() and target != app.applicant_phone:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Contact target does not match the designated applicant for this application.",
            )

        applicant_token = create_applicant_token({
            "application_number": app.application_number,
            "application_id": app.application_id,
            "applicant_type": app.applicant_type,
            "applicant_email": app.applicant_email,
            "state": app.state,
            "district": app.district,
        })

    return VerifyOTPResponse(
        verified=True,
        contact_target=contact_target,
        application_number=app.application_number if app else None,
        applicant_token=applicant_token,
        token_type="bearer" if applicant_token else None,
        message="OTP verified successfully.",
    )


@router.post("/auth/logout")
def applicant_logout(
    authorization: str | None = Header(default=None),
    applicant: dict = Depends(require_applicant_user),
):
    """
    Revoke current applicant session token using the distributed blocklist.
    """
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]
            revoke_token(token, exp_timestamp=applicant.get("exp"))

    return {"message": "Applicant session successfully logged out and token invalidated."}


@router.post("/auth/activate", response_model=ActivateAccountResponse)
def activate_account(
    payload: ActivateAccountRequest,
    db: Session = Depends(get_db_session),
):
    """
    Activate provisioned operational account with secure password creation:
    - Cryptographically validates single-use activation token.
    - Verifies token expiration and revocation.
    - Enforces password complexity (min 8 chars, uppercase, lowercase, digit, special).
    - Atomically consumes token, sets PBKDF2-HMAC-SHA256 password hash, and enables account.
    """
    service = AccountProvisioningService(db)
    try:
        res = service.activate_account(
            raw_activation_token=payload.activation_token,
            password=payload.password,
            confirm_password=payload.confirm_password,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return ActivateAccountResponse(**res)


@router.post("/auth/activation/resend", response_model=ResendActivationResponse)
def resend_activation_link(
    payload: ResendActivationRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Resend account activation invitation link:
    - Dual-key rate-limited per client IP and email.
    - Revokes any existing unconsumed tokens and issues a fresh 72-hour token.
    - Dispatches email AFTER database commit.
    """
    client_ip = _get_client_ip(request)
    target_email = payload.applicant_email.strip().lower()

    check_rate_limit(f"act_resend_ip:{client_ip}", max_attempts=5, window_seconds=300)
    record_failure(f"act_resend_ip:{client_ip}", window_seconds=300)
    check_rate_limit(f"act_resend_tgt:{target_email}", max_attempts=3, window_seconds=300)
    record_failure(f"act_resend_tgt:{target_email}", window_seconds=300)

    service = AccountProvisioningService(db)
    try:
        res = service.resend_activation_token(
            applicant_email=payload.applicant_email,
            application_number=payload.application_number,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    # Post-commit email dispatch
    try:
        service.dispatch_activation_email(res)
    except Exception as e:
        logger.error("Failed to dispatch activation email after commit: %s", e)

    return ResendActivationResponse(
        application_number=res["application_number"],
        applicant_email=res["applicant_email"],
        message="A fresh activation link has been sent to the applicant email address.",
    )


@router.post("/auth/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Initiate password recovery for operational accounts.
    Rate limited per IP.
    Returns generic response to prevent account/username enumeration.
    Enqueues reset event in transactional outbox.
    """
    client_ip = _get_client_ip(request)
    check_rate_limit(f"pwd_reset_req:{client_ip}", max_attempts=5, window_seconds=300)
    record_failure(f"pwd_reset_req:{client_ip}", window_seconds=300)

    service = AccountProvisioningService(db)
    try:
        result = service.request_password_reset(email=payload.email)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return PasswordResetResponse(**result)


@router.post("/auth/password-reset/confirm", response_model=PasswordResetConfirmResponse)
def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """
    Confirm password reset with one-time cryptographic token:
    - Enforces password complexity (min 8 chars, uppercase, lowercase, digit, special).
    - Constant-time verification of token hash.
    - Single-use consumption (replay blocked).
    - Hashes password using PBKDF2-HMAC-SHA256 (100k iterations).
    """
    client_ip = _get_client_ip(request)
    check_rate_limit(f"pwd_reset_conf:{client_ip}", max_attempts=10, window_seconds=300)

    service = AccountProvisioningService(db)
    try:
        result = service.confirm_password_reset(
            raw_reset_token=payload.reset_token,
            password=payload.password,
            confirm_password=payload.confirm_password,
        )
        db.commit()
    except Exception as e:
        record_failure(f"pwd_reset_conf:{client_ip}", window_seconds=300)
        db.rollback()
        raise _map_exception(e)

    return PasswordResetConfirmResponse(**result)


@router.post("/outbox/process", response_model=OutboxProcessResponse)
def process_outbox_queue(
    batch_size: int = 10,
    db: Session = Depends(get_db_session),
    caller: dict = Depends(require_reviewer_user),
):
    """
    Process transactional email outbox queue (requires reviewer/admin credentials).
    """
    from src.services.email_outbox_service import EmailOutboxService
    outbox_svc = EmailOutboxService(db)
    try:
        result = outbox_svc.process_outbox(batch_size=batch_size, worker_id=caller.get("user_id"))
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return OutboxProcessResponse(**result)


# ============================================================
# PART B: APPLICANT REGISTRATION & LIFECYCLE ENDPOINTS
# ============================================================

@router.post("/applications/state", response_model=ApplicationCreationResponse)
def create_state_application(
    payload: CreateStateApplicationRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Register a new State Directorate application in DRAFT status."""
    client_ip = _get_client_ip(request)
    check_rate_limit(f"app_create:{client_ip}", max_attempts=APP_CREATE_MAX_ATTEMPTS, window_seconds=APP_CREATE_WINDOW)
    record_failure(f"app_create:{client_ip}", window_seconds=APP_CREATE_WINDOW)

    service = RegistrationService(db)
    data = payload.model_dump()
    data["applicant_type"] = "STATE"

    try:
        app = service.create_application(data)
        token_model, raw_secret = service.create_tracking_token(app.application_id)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    applicant_token = create_applicant_token({
        "application_number": app.application_number,
        "application_id": app.application_id,
        "applicant_type": app.applicant_type,
        "applicant_email": app.applicant_email,
        "state": app.state,
        "district": app.district,
    })

    return ApplicationCreationResponse(
        application_id=app.application_id,
        application_number=app.application_number,
        applicant_type=app.applicant_type,
        applicant_name=app.applicant_name,
        state=app.state,
        district=app.district,
        status=app.status,
        current_stage=app.current_stage,
        tracking_token=raw_secret,
        applicant_token=applicant_token,
        created_at=app.created_at.isoformat(),
        message="State registration application created successfully in DRAFT status.",
    )


@router.post("/applications/district", response_model=ApplicationCreationResponse)
def create_district_application(
    payload: CreateDistrictApplicationRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Register a new District Health Society application in DRAFT status."""
    client_ip = _get_client_ip(request)
    check_rate_limit(f"app_create:{client_ip}", max_attempts=APP_CREATE_MAX_ATTEMPTS, window_seconds=APP_CREATE_WINDOW)
    record_failure(f"app_create:{client_ip}", window_seconds=APP_CREATE_WINDOW)

    service = RegistrationService(db)
    data = payload.model_dump()
    data["applicant_type"] = "DISTRICT"

    try:
        app = service.create_application(data)
        token_model, raw_secret = service.create_tracking_token(app.application_id)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    applicant_token = create_applicant_token({
        "application_number": app.application_number,
        "application_id": app.application_id,
        "applicant_type": app.applicant_type,
        "applicant_email": app.applicant_email,
        "state": app.state,
        "district": app.district,
    })

    return ApplicationCreationResponse(
        application_id=app.application_id,
        application_number=app.application_number,
        applicant_type=app.applicant_type,
        applicant_name=app.applicant_name,
        state=app.state,
        district=app.district,
        status=app.status,
        current_stage=app.current_stage,
        tracking_token=raw_secret,
        applicant_token=applicant_token,
        created_at=app.created_at.isoformat(),
        message="District registration application created successfully in DRAFT status.",
    )


@router.post("/applications/hospital", response_model=ApplicationCreationResponse)
def create_hospital_application(
    payload: CreateHospitalApplicationRequest,
    request: Request,
    db: Session = Depends(get_db_session),
):
    """Register a new Hospital facility application in DRAFT status."""
    client_ip = _get_client_ip(request)
    check_rate_limit(f"app_create:{client_ip}", max_attempts=APP_CREATE_MAX_ATTEMPTS, window_seconds=APP_CREATE_WINDOW)
    record_failure(f"app_create:{client_ip}", window_seconds=APP_CREATE_WINDOW)

    service = RegistrationService(db)
    data = payload.model_dump()
    data["applicant_type"] = "HOSPITAL"

    try:
        app = service.create_application(data)
        token_model, raw_secret = service.create_tracking_token(app.application_id)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    applicant_token = create_applicant_token({
        "application_number": app.application_number,
        "application_id": app.application_id,
        "applicant_type": app.applicant_type,
        "applicant_email": app.applicant_email,
        "state": app.state,
        "district": app.district,
    })

    return ApplicationCreationResponse(
        application_id=app.application_id,
        application_number=app.application_number,
        applicant_type=app.applicant_type,
        applicant_name=app.applicant_name,
        state=app.state,
        district=app.district,
        status=app.status,
        current_stage=app.current_stage,
        tracking_token=raw_secret,
        applicant_token=applicant_token,
        created_at=app.created_at.isoformat(),
        message="Hospital registration application created successfully in DRAFT status.",
    )


@router.get("/applications/me", response_model=ApplicantApplicationViewResponse)
def get_applicant_own_application(
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    View applicant's own application details, uploaded documents, and status milestones.
    Enforces strict applicant ownership.
    """
    app = (
        db.query(RegistrationApplication)
        .filter_by(application_id=applicant["application_id"])
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    docs = []
    for d in app.documents:
        docs.append(DocumentMetadataResponse(
            document_id=d.document_id,
            application_id=d.application_id,
            document_type=d.document_type,
            original_filename=d.original_filename,
            mime_type=d.mime_type,
            file_size_bytes=d.file_size_bytes,
            verification_status=d.verification_status,
            reviewer_remarks=d.reviewer_remarks,
            uploaded_at=d.uploaded_at.isoformat(),
        ))

    milestones = []
    for h in app.history:
        milestones.append({
            "stage": h.review_tier,
            "action": h.action,
            "status": h.new_status,
            "timestamp": h.created_at.isoformat() if h.created_at else None,
        })

    return ApplicantApplicationViewResponse(
        application_id=app.application_id,
        application_number=app.application_number,
        applicant_type=app.applicant_type,
        applicant_name=app.applicant_name,
        applicant_email=app.applicant_email,
        applicant_phone=app.applicant_phone,
        state=app.state,
        district=app.district,
        city=app.city,
        address=app.address,
        pincode=app.pincode,
        official_designation=app.official_designation,
        nodal_officer_name=app.nodal_officer_name,
        status=app.status,
        current_stage=app.current_stage,
        resubmission_version=app.resubmission_version,
        created_at=app.created_at.isoformat(),
        submitted_at=app.submitted_at.isoformat() if app.submitted_at else None,
        resubmitted_at=app.resubmitted_at.isoformat() if app.resubmitted_at else None,
        rejection_reason=app.rejection_reason,
        correction_notes=app.correction_notes,
        profile_data=app.profile_data,
        documents=docs,
        milestones=milestones,
    )


@router.put("/applications/draft")
def update_draft_application(
    payload: UpdateDraftApplicationRequest,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Save or update details of an application while in DRAFT status.
    Enforces ownership and disallows editing submitted applications.
    """
    service = RegistrationService(db)
    updates = payload.model_dump(exclude_unset=True)

    try:
        app = service.update_draft_application(applicant["application_id"], updates)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return {
        "application_id": app.application_id,
        "application_number": app.application_number,
        "status": app.status,
        "last_updated_at": app.last_updated_at.isoformat(),
        "message": "Draft application updated successfully.",
    }


@router.post("/applications/documents", response_model=DocumentMetadataResponse)
def upload_document_metadata(
    payload: UploadDocumentMetadataRequest,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Upload and associate registration document metadata with the applicant's application.
    Enforces ownership and document type constraints.
    """
    service = RegistrationService(db)

    try:
        doc = service.add_document_metadata(
            application_id=applicant["application_id"],
            document_type=payload.document_type,
            original_filename=payload.original_filename,
            mime_type=payload.mime_type,
            file_size_bytes=payload.file_size_bytes,
            storage_key=payload.storage_key,
            checksum_sha256=payload.checksum_sha256,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return DocumentMetadataResponse(
        document_id=doc.document_id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        verification_status=doc.verification_status,
        reviewer_remarks=doc.reviewer_remarks,
        uploaded_at=doc.uploaded_at.isoformat(),
    )


@router.post("/applications/documents/upload", response_model=DocumentMetadataResponse)
async def upload_document_multipart(
    document_type: str = Form(..., description="Document type: CLINICAL_LICENSE, FIRE_SAFETY_NOC, etc."),
    file: UploadFile = File(..., description="Document binary payload (PDF, JPEG, PNG, max 25MB)"),
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Secure multipart document binary upload:
    - Maximum 25 MB file size limit enforced.
    - Magic-byte verification for PDF, JPEG, PNG (never trusts client MIME alone).
    - Antivirus malware scan (ClamAV / simulated scanner).
    - Computes SHA-256 and derives server-authoritative storage key.
    - Automatically updates / replaces existing document of this type if in DRAFT or CORRECTION_REQUIRED.
    """
    service = RegistrationService(db)
    try:
        file_bytes = await file.read()
        doc = service.upload_document_binary(
            application_id=applicant["application_id"],
            document_type=document_type,
            file_bytes=file_bytes,
            declared_mime=file.content_type,
            original_filename=file.filename,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return DocumentMetadataResponse(
        document_id=doc.document_id,
        application_id=doc.application_id,
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        mime_type=doc.mime_type,
        file_size_bytes=doc.file_size_bytes,
        verification_status=doc.verification_status,
        reviewer_remarks=doc.reviewer_remarks,
        uploaded_at=doc.uploaded_at.isoformat(),
    )


@router.get("/applications/documents/{document_id}/download")
def download_document(
    document_id: str,
    caller: dict = Depends(get_caller_user_context),
    db: Session = Depends(get_db_session),
):
    """
    Secure document download endpoint:
    - Verifies caller authorization (applicant ownership or reviewer jurisdiction).
    - Streams binary payload with verified MIME type and Content-Disposition.
    - Never exposes raw storage paths or unrestricted public URLs.
    """
    service = RegistrationService(db)
    try:
        file_bytes, filename, mime_type = service.get_document_for_download(
            document_id=document_id,
            user_context=caller,
        )
    except Exception as e:
        raise _map_exception(e)

    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/applications/documents/{document_id}")
def delete_document(
    document_id: str,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Safely delete document blob and database record.
    Permitted only for applicant while application is in DRAFT or CORRECTION_REQUIRED.
    """
    service = RegistrationService(db)
    try:
        service.delete_document(document_id, applicant)
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return {"message": "Document successfully deleted.", "document_id": document_id}


def _safe_post_commit_outbox_drain(bind_engine):
    """
    Opportunistic post-commit background worker trigger.
    Executes asynchronously in FastAPI background tasks AFTER the HTTP response is returned.
    If an external OutboxWorker daemon is running, SKIP LOCKED prevents duplicate delivery.
    If no worker daemon is running, this ensures prompt dispatch without delaying or failing the HTTP response.
    """
    try:
        from sqlalchemy.orm import sessionmaker
        SessionLocal = sessionmaker(bind=bind_engine, autocommit=False, autoflush=False)
        with SessionLocal() as bg_session:
            from src.services.email_outbox_service import EmailOutboxService
            outbox_svc = EmailOutboxService(bg_session)
            outbox_svc.process_outbox(batch_size=5, worker_id="api_post_commit_drain")
            bg_session.commit()
    except Exception as exc:
        logger.debug("Opportunistic background outbox drain completed or deferred: %s", exc)


@router.post("/applications/submit", response_model=SubmitApplicationResponse)
def submit_application(
    payload: SubmitApplicationRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Submit a DRAFT application into the review pipeline:
    - Verifies all mandatory documents are uploaded.
    - Transitions status from DRAFT to SUBMITTED.
    - Sets stage to appropriate tier (DISTRICT_REVIEW / STATE_REVIEW / CENTRAL_REVIEW).
    - Emits SUBMIT approval history record.
    - Returns tracking token for public tracking.
    """
    client_ip = _get_client_ip(request)
    service = RegistrationService(db)

    try:
        res = service.submit_application(
            application_id=applicant["application_id"],
            remarks=payload.remarks,
            client_ip=client_ip,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    # Safe opportunistic post-commit background outbox drain
    try:
        db_engine = db.get_bind()
        background_tasks.add_task(_safe_post_commit_outbox_drain, db_engine)
    except Exception as bg_err:
        logger.debug("Failed to schedule background outbox drain: %s", bg_err)

    submitted_at_str = res["submitted_at"] if isinstance(res.get("submitted_at"), str) else (
        res["submitted_at"].isoformat() if res.get("submitted_at") else ""
    )
    return SubmitApplicationResponse(
        application_id=res["application_id"],
        application_number=res["application_number"],
        status=res["status"],
        current_stage=res["current_stage"],
        submitted_at=submitted_at_str,
        tracking_token=res["tracking_token"],
        message="Application submitted successfully into review pipeline.",
    )


@router.post("/applications/resubmit", response_model=ResubmitApplicationResponse)
def resubmit_corrected_application(
    payload: ResubmitApplicationRequest,
    request: Request,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Resubmit an application following a CORRECTION_REQUIRED decision:
    - Preserves the original submitted_at timestamp.
    - Sets resubmitted_at to current timestamp.
    - Increments resubmission_version.
    - Returns status to SUBMITTED for re-evaluation by the assigned reviewer tier.
    """
    client_ip = _get_client_ip(request)
    service = RegistrationService(db)

    try:
        res = service.resubmit_application(
            application_id=applicant["application_id"],
            applicant_notes=payload.applicant_notes,
            client_ip=client_ip,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    resubmitted_at_str = res["resubmitted_at"] if isinstance(res.get("resubmitted_at"), str) else (
        res["resubmitted_at"].isoformat() if res.get("resubmitted_at") else ""
    )
    return ResubmitApplicationResponse(
        application_id=res["application_id"],
        application_number=res.get("application_number", applicant.get("application_number", "")),
        status=res["status"],
        current_stage=res["current_stage"],
        resubmission_version=res["resubmission_version"],
        resubmitted_at=resubmitted_at_str,
        message="Application resubmitted successfully for review.",
    )


# ============================================================
# PART C: SECURE PUBLIC TRACKING ENDPOINT
# ============================================================

@router.get("/public/track/{application_number}", response_model=PublicTrackingResponse)
@router.get("/track/{application_number}", response_model=PublicTrackingResponse)
def track_application_public(
    application_number: str,
    tracking_token: str = Query(..., min_length=16, description="Mandatory secret tracking token"),
    request: Request = None,
    db: Session = Depends(get_db_session),
):
    """
    Secure public tracking endpoint. Exposes ONLY safe milestone and status metadata.
    Mandatory tracking_token verification eliminates public application enumeration.
    Rate-limited per client IP to prevent denial of service and automated brute forcing.
    """
    if request:
        client_ip = _get_client_ip(request)
        check_rate_limit(f"track:{client_ip}", max_attempts=TRACK_MAX_ATTEMPTS, window_seconds=TRACK_WINDOW)
        record_failure(f"track:{client_ip}", window_seconds=TRACK_WINDOW)

    service = RegistrationService(db)

    try:
        tracking_data = service.track_application_public(
            application_number=application_number,
            tracking_token=tracking_token,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    milestones = [
        MilestoneResponse(
            stage=m["stage"],
            action=m["action"],
            status=m["status"],
            timestamp=m["timestamp"],
        )
        for m in tracking_data["milestones"]
    ]

    return PublicTrackingResponse(
        application_number=tracking_data["application_number"],
        applicant_type=tracking_data["applicant_type"],
        applicant_name=tracking_data["applicant_name"],
        state=tracking_data["state"],
        district=tracking_data["district"],
        status=tracking_data["status"],
        current_stage=tracking_data["current_stage"],
        created_at=tracking_data["created_at"],
        submitted_at=tracking_data["submitted_at"],
        resubmission_version=tracking_data["resubmission_version"],
        milestones=milestones,
    )


# ============================================================
# PART D: REVIEWER WORKFLOW ENDPOINTS
# ============================================================

@router.get("/review/applications", response_model=ReviewerApplicationListResponse)
def list_reviewer_applications(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    stage_filter: Optional[str] = Query(default=None, alias="stage"),
    applicant_type_filter: Optional[str] = Query(default=None, alias="applicant_type"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    View assigned/pending applications filtered strictly by reviewer's geographic jurisdiction and role:
    - DISTRICT_ADMIN: only applications in reviewer's state and district. Default stage: DISTRICT_REVIEW.
    - STATE_ADMIN: only applications in reviewer's state. Default stage: STATE_REVIEW.
    - CENTRAL_ADMIN: national applications. Default stage: CENTRAL_REVIEW.
    """
    role = reviewer["role"]
    query = db.query(RegistrationApplication)

    # Enforce geographic scoping
    if role == "DISTRICT_ADMIN":
        query = query.filter(
            RegistrationApplication.state == reviewer["state"],
            RegistrationApplication.district == reviewer["district"],
        )
        if not stage_filter:
            stage_filter = "DISTRICT_REVIEW"
    elif role == "STATE_ADMIN":
        query = query.filter(
            RegistrationApplication.state == reviewer["state"],
        )
        if not stage_filter:
            stage_filter = "STATE_REVIEW"
    elif role == "CENTRAL_ADMIN":
        if not stage_filter:
            stage_filter = "CENTRAL_REVIEW"

    if stage_filter:
        query = query.filter(RegistrationApplication.current_stage == stage_filter)

    if status_filter:
        query = query.filter(RegistrationApplication.status == status_filter)

    if applicant_type_filter:
        query = query.filter(RegistrationApplication.applicant_type == applicant_type_filter)

    total = query.count()
    records = query.order_by(RegistrationApplication.created_at.desc()).offset(offset).limit(limit).all()

    items = []
    for r in records:
        docs_count = len(r.documents)
        pending_docs = sum(1 for d in r.documents if d.verification_status == "PENDING")
        items.append(ReviewerApplicationSummary(
            application_id=r.application_id,
            application_number=r.application_number,
            applicant_type=r.applicant_type,
            applicant_name=r.applicant_name,
            applicant_email=r.applicant_email,
            applicant_phone=r.applicant_phone,
            state=r.state,
            district=r.district,
            status=r.status,
            current_stage=r.current_stage,
            resubmission_version=r.resubmission_version,
            created_at=r.created_at.isoformat(),
            submitted_at=r.submitted_at.isoformat() if r.submitted_at else None,
            documents_count=docs_count,
            pending_documents_count=pending_docs,
        ))

    return ReviewerApplicationListResponse(total=total, applications=items)


@router.get("/review/applications/{application_id}")
def get_reviewer_application_detail(
    application_id: str,
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    View complete application details, documents, and audit trail.
    Enforces geographic access boundaries based on reviewer's jurisdiction.
    """
    app = (
        db.query(RegistrationApplication)
        .filter(
            (RegistrationApplication.application_id == application_id)
            | (RegistrationApplication.application_number == application_id)
        )
        .first()
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    role = reviewer["role"]
    if role == "DISTRICT_ADMIN":
        if app.state != reviewer.get("state") or app.district != reviewer.get("district"):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Application is outside your district jurisdiction ({reviewer.get('district')}, {reviewer.get('state')}).",
            )
    elif role == "STATE_ADMIN":
        if app.state != reviewer.get("state"):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Application is outside your state jurisdiction ({reviewer.get('state')}).",
            )

    docs = []
    for d in app.documents:
        docs.append({
            "document_id": d.document_id,
            "document_type": d.document_type,
            "original_filename": d.original_filename,
            "file_size_bytes": d.file_size_bytes,
            "checksum_sha256": d.checksum_sha256,
            "verification_status": d.verification_status,
            "reviewer_remarks": d.reviewer_remarks,
            "uploaded_at": d.uploaded_at.isoformat(),
        })

    history = []
    for h in app.history:
        history.append({
            "action": h.action,
            "review_tier": h.review_tier,
            "previous_status": h.previous_status,
            "new_status": h.new_status,
            "reviewer_user_id": h.reviewer_user_id,
            "remarks": h.remarks,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        })

    return {
        "application_id": app.application_id,
        "application_number": app.application_number,
        "applicant_type": app.applicant_type,
        "applicant_name": app.applicant_name,
        "applicant_email": app.applicant_email,
        "applicant_phone": app.applicant_phone,
        "state": app.state,
        "district": app.district,
        "city": app.city,
        "address": app.address,
        "pincode": app.pincode,
        "official_designation": app.official_designation,
        "nodal_officer_name": app.nodal_officer_name,
        "status": app.status,
        "current_stage": app.current_stage,
        "resubmission_version": app.resubmission_version,
        "profile_data": app.profile_data,
        "correction_notes": app.correction_notes,
        "rejection_reason": app.rejection_reason,
        "created_at": app.created_at.isoformat(),
        "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
        "documents": docs,
        "history": history,
    }


@router.post("/review/documents/{document_id}/verify")
def verify_document(
    document_id: str,
    payload: VerifyDocumentRequest,
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Verify or reject a submitted registration document.
    Enforces that reviewer has geographic jurisdiction over the document's parent application.
    """
    service = RegistrationService(db)

    try:
        doc = service.verify_document(
            document_id=document_id,
            reviewer_user=reviewer,
            verification_status=payload.verification_status,
            reviewer_remarks=payload.reviewer_remarks,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return {
        "document_id": doc.document_id,
        "application_id": doc.application_id,
        "verification_status": doc.verification_status,
        "reviewer_remarks": doc.reviewer_remarks,
        "message": f"Document status updated to '{doc.verification_status}'.",
    }


@router.post("/review/applications/{application_id}/decision", response_model=ReviewDecisionResponse)
def execute_review_decision(
    application_id: str,
    payload: ReviewDecisionRequest,
    request: Request,
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Execute stage transition decision (FORWARD, APPROVE, REJECT).
    Enforces reviewer role, current stage alignment, geographic boundary, and self-approval prevention.
    """
    client_ip = _get_client_ip(request)
    service = RegistrationService(db)

    try:
        res = service.review_application(
            application_id=application_id,
            reviewer_user=reviewer,
            action=payload.action,
            remarks=payload.remarks,
            client_ip=client_ip,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    # Post-commit activation email dispatch if operational account was provisioned
    provisioning = res.get("provisioning")
    if provisioning:
        try:
            prov_svc = AccountProvisioningService(db)
            prov_svc.dispatch_activation_email(provisioning)
        except Exception as email_err:
            logger.error("Failed to dispatch activation email after approval commit: %s", email_err)

    return ReviewDecisionResponse(
        application_id=res["application_id"],
        application_number=res["application_number"],
        action=res["action"],
        new_status=res["new_status"],
        new_stage=res["new_stage"],
        message=f"Decision '{payload.action}' successfully executed.",
        provisioning_user_id=provisioning.get("user_id") if provisioning else None,
        provisioning_username=provisioning.get("username") if provisioning else None,
    )


@router.post("/review/applications/{application_id}/request-correction")
def request_application_correction(
    application_id: str,
    payload: RequestCorrectionRequest,
    request: Request,
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Request applicant corrections on an application.
    Moves status and stage to CORRECTION_REQUIRED, emits REQUEST_CORRECTION history entry,
    and records specific correction instructions.
    """
    client_ip = _get_client_ip(request)
    service = RegistrationService(db)

    try:
        app_res = service.request_correction(
            application_id=application_id,
            reviewer_user=reviewer,
            correction_notes=payload.correction_notes,
            client_ip=client_ip,
        )
        db.commit()
    except Exception as e:
        db.rollback()
        raise _map_exception(e)

    return {
        "application_id": app_res["application_id"],
        "application_number": app_res["application_number"],
        "status": app_res["status"],
        "current_stage": app_res["current_stage"],
        "correction_notes": app_res["correction_notes"],
        "message": "Correction request successfully issued to applicant.",
    }


# ============================================================
# PHASE 4D-2: WORKFLOW NOTIFICATIONS ENDPOINTS
# ============================================================

@router.get("/review/notifications")
def get_reviewer_notifications_endpoint(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Retrieve in-app notifications for the authenticated reviewer.
    Strictly isolated by reviewer jurisdiction (District, State, or Central).
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    return repo.get_reviewer_notifications(reviewer, unread_only=unread_only, limit=limit)


@router.post("/review/notifications/{notification_id}/read")
def mark_reviewer_notification_read_endpoint(
    notification_id: int,
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Mark a reviewer notification as read.
    Validates that the reviewer belongs to the notification's jurisdiction.
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    success = repo.mark_reviewer_notification_as_read(notification_id, reviewer)
    if not success:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized to update this notification or notification not found.",
        )
    return {"success": True}


@router.post("/review/notifications/read-all")
def mark_all_reviewer_notifications_read_endpoint(
    reviewer: dict = Depends(require_reviewer_user),
    db: Session = Depends(get_db_session),
):
    """
    Mark all unread notifications within the reviewer's jurisdiction as read.
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    count = repo.mark_all_reviewer_notifications_read(reviewer)
    return {"success": True, "marked_count": count}


@router.get("/applications/notifications")
def get_applicant_notifications_endpoint(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Retrieve in-app notifications for the authenticated applicant's application dossier.
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    return repo.get_applicant_notifications(
        applicant["application_id"], unread_only=unread_only, limit=limit
    )


@router.post("/applications/notifications/{notification_id}/read")
def mark_applicant_notification_read_endpoint(
    notification_id: int,
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Mark an applicant notification as read.
    Enforces isolation: applicant can only mark their own notifications.
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    success = repo.mark_applicant_notification_as_read(
        notification_id, applicant["application_id"]
    )
    if not success:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized or notification not found.",
        )
    return {"success": True}


@router.post("/applications/notifications/read-all")
def mark_all_applicant_notifications_read_endpoint(
    applicant: dict = Depends(require_applicant_user),
    db: Session = Depends(get_db_session),
):
    """
    Mark all unread notifications for the authenticated applicant as read.
    """
    from src.database.pg_repository import PgReferralRepository
    repo = PgReferralRepository(db)
    count = repo.mark_all_applicant_notifications_read(applicant["application_id"])
    return {"success": True, "marked_count": count}

