"""
Pydantic Request and Response Schemas for Registration System APIs
AI Powered Smart Hospital Referral System - Phase 1 Task 1D
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, model_validator


# ============================================================
# APPLICANT AUTHENTICATION SCHEMAS
# ============================================================

class RequestOTPRequest(BaseModel):
    contact_target: str = Field(..., description="Email address or phone number")
    channel: str = Field(default="EMAIL", description="Delivery channel: 'EMAIL' or 'SMS'")
    purpose: str = Field(
        default="PORTAL_ACCESS_OTP",
        pattern=r"^(REGISTRATION_OTP|LOGIN_OTP|PASSWORD_RESET_OTP|PORTAL_ACCESS_OTP)$",
        description="OTP purpose"
    )
    application_number: Optional[str] = Field(default=None, description="Optional application number if retrieving an existing application")


class RequestOTPResponse(BaseModel):
    token_id: str
    contact_target: str
    channel: str
    resend_available_in_seconds: int
    expires_in_seconds: int
    message: str


class VerifyOTPRequest(BaseModel):
    token_id: str
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification OTP")
    purpose: str = Field(
        default="PORTAL_ACCESS_OTP",
        pattern=r"^(REGISTRATION_OTP|LOGIN_OTP|PASSWORD_RESET_OTP|PORTAL_ACCESS_OTP)$",
        description="OTP purpose to verify against"
    )
    application_number: Optional[str] = Field(default=None, description="Application number to access after verification")


class VerifyOTPResponse(BaseModel):
    verified: bool
    contact_target: str
    application_number: Optional[str] = None
    applicant_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
    message: str


# ============================================================
# APPLICATION CREATION SCHEMAS
# ============================================================

class CreateStateApplicationRequest(BaseModel):
    applicant_name: str = Field(..., min_length=3, max_length=255)
    applicant_email: str = Field(..., min_length=5, max_length=255)
    applicant_phone: str = Field(..., min_length=10, max_length=30)
    state: str = Field(..., min_length=2, max_length=100)
    official_designation: Optional[str] = None
    nodal_officer_name: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None


class CreateDistrictApplicationRequest(BaseModel):
    applicant_name: str = Field(..., min_length=3, max_length=255)
    applicant_email: str = Field(..., min_length=5, max_length=255)
    applicant_phone: str = Field(..., min_length=10, max_length=30)
    state: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    official_designation: Optional[str] = None
    nodal_officer_name: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None


class CreateHospitalApplicationRequest(BaseModel):
    applicant_name: str = Field(..., min_length=3, max_length=255)
    applicant_email: str = Field(..., min_length=5, max_length=255)
    applicant_phone: str = Field(..., min_length=10, max_length=30)
    state: str = Field(..., min_length=2, max_length=100)
    district: str = Field(..., min_length=2, max_length=100)
    city: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    official_designation: Optional[str] = None
    nodal_officer_name: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None


class ApplicationCreationResponse(BaseModel):
    application_id: str
    application_number: str
    applicant_type: str
    applicant_name: str
    state: str
    district: Optional[str] = None
    status: str
    current_stage: str
    tracking_token: str
    applicant_token: str
    created_at: str
    message: str


# ============================================================
# DRAFT, SUBMIT & RESUBMIT SCHEMAS
# ============================================================

class UpdateDraftApplicationRequest(BaseModel):
    applicant_name: Optional[str] = None
    applicant_phone: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    official_designation: Optional[str] = None
    nodal_officer_name: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None


class SubmitApplicationRequest(BaseModel):
    remarks: Optional[str] = None


class SubmitApplicationResponse(BaseModel):
    application_id: str
    application_number: str
    status: str
    current_stage: str
    submitted_at: str
    tracking_token: str
    message: str


class ResubmitApplicationRequest(BaseModel):
    applicant_notes: str = Field(..., min_length=3, description="Notes describing corrections made")


class ResubmitApplicationResponse(BaseModel):
    application_id: str
    application_number: str
    status: str
    current_stage: str
    resubmission_version: int
    resubmitted_at: str
    message: str


# ============================================================
# DOCUMENT SCHEMAS
# ============================================================

class UploadDocumentMetadataRequest(BaseModel):
    document_type: str = Field(
        ...,
        pattern=r"^(CLINICAL_LICENSE|FIRE_SAFETY_NOC|POLLUTION_CONTROL_NOC|MEDICAL_COUNCIL_AFFILIATION|GOVERNMENT_ORDER|IDENTITY_PROOF|OTHER)$",
        description="Allowed types: 'CLINICAL_LICENSE', 'FIRE_SAFETY_NOC', 'POLLUTION_CONTROL_NOC', "
                    "'MEDICAL_COUNCIL_AFFILIATION', 'GOVERNMENT_ORDER', 'IDENTITY_PROOF', 'OTHER'"
    )
    original_filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_\-\. ]+$",
        description="Display filename without path separators or traversal sequences"
    )
    mime_type: str = Field(
        ...,
        pattern=r"^(application/pdf|image/jpeg|image/png)$",
        description="Allowed MIME types: application/pdf, image/jpeg, image/png"
    )
    file_size_bytes: int = Field(
        ...,
        gt=0,
        le=26214400,
        description="File size in bytes (maximum 25MB = 26,214,400 bytes)"
    )
    storage_key: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Optional client storage key hint; server always generates authoritative storage key"
    )
    checksum_sha256: str = Field(
        ...,
        pattern=r"^[a-f0-9]{64}$",
        description="Hexadecimal SHA-256 checksum (exactly 64 lowercase hex characters)"
    )


class DocumentMetadataResponse(BaseModel):
    document_id: str
    application_id: str
    document_type: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    verification_status: str
    reviewer_remarks: Optional[str] = None
    uploaded_at: str


# ============================================================
# APPLICANT & PUBLIC VIEW SCHEMAS
# ============================================================

class MilestoneResponse(BaseModel):
    stage: str
    action: str
    status: str
    timestamp: Optional[str] = None


class ApplicantApplicationViewResponse(BaseModel):
    application_id: str
    application_number: str
    applicant_type: str
    applicant_name: str
    applicant_email: str
    applicant_phone: str
    state: str
    district: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    pincode: Optional[str] = None
    official_designation: Optional[str] = None
    nodal_officer_name: Optional[str] = None
    status: str
    current_stage: str
    resubmission_version: int
    created_at: str
    submitted_at: Optional[str] = None
    resubmitted_at: Optional[str] = None
    rejection_reason: Optional[str] = None
    correction_notes: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None
    documents: List[DocumentMetadataResponse]
    milestones: List[MilestoneResponse]


class PublicTrackingResponse(BaseModel):
    application_number: str
    applicant_type: str
    applicant_name: str
    state: str
    district: Optional[str] = None
    status: str
    current_stage: str
    created_at: Optional[str] = None
    submitted_at: Optional[str] = None
    resubmission_version: int
    milestones: List[MilestoneResponse]


# ============================================================
# REVIEWER SCHEMAS
# ============================================================

class ReviewerApplicationSummary(BaseModel):
    application_id: str
    application_number: str
    applicant_type: str
    applicant_name: str
    applicant_email: str
    applicant_phone: str
    state: str
    district: Optional[str] = None
    status: str
    current_stage: str
    resubmission_version: int
    created_at: str
    submitted_at: Optional[str] = None
    documents_count: int
    pending_documents_count: int


class ReviewerApplicationListResponse(BaseModel):
    total: int
    applications: List[ReviewerApplicationSummary]


class VerifyDocumentRequest(BaseModel):
    verification_status: str = Field(..., description="Allowed: 'VERIFIED' or 'REJECTED'")
    reviewer_remarks: Optional[str] = None


class ReviewDecisionRequest(BaseModel):
    action: str = Field(..., description="Allowed: 'FORWARD', 'APPROVE', 'REJECT'")
    remarks: Optional[str] = None


class RequestCorrectionRequest(BaseModel):
    correction_notes: str = Field(..., min_length=5, description="Specific instructions for applicant correction")


class ReviewDecisionResponse(BaseModel):
    application_id: str
    application_number: str
    action: str
    new_status: str
    new_stage: str
    message: str
    provisioning_user_id: Optional[str] = None
    provisioning_username: Optional[str] = None


class ActivateAccountRequest(BaseModel):
    activation_token: Optional[str] = Field(None, description="One-time activation token")
    token: Optional[str] = Field(None, description="Alias for activation_token")
    password: str = Field(..., min_length=8, description="New secure password meeting complexity criteria")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")

    @model_validator(mode="before")
    @classmethod
    def populate_token_alias(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("activation_token") and data.get("token"):
                data["activation_token"] = data["token"]
        return data


class ActivateAccountResponse(BaseModel):
    user_id: str
    username: str
    name: str
    role_id: str
    hospital_id: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    activated_at: str
    message: str


class ResendActivationRequest(BaseModel):
    application_number: str = Field(..., description="Application reference number")
    applicant_email: str = Field(..., description="Applicant contact email")


class ResendActivationResponse(BaseModel):
    application_number: str
    applicant_email: str
    message: str


class PasswordResetRequest(BaseModel):
    email: str = Field(..., description="Registered account email address")


class PasswordResetResponse(BaseModel):
    message: str
    email_masked: Optional[str] = None


class PasswordResetConfirmRequest(BaseModel):
    reset_token: str = Field(..., min_length=16, description="One-time password reset token")
    password: str = Field(..., min_length=8, description="New secure password meeting complexity criteria")
    confirm_password: str = Field(..., min_length=8, description="Password confirmation")


class PasswordResetConfirmResponse(BaseModel):
    message: str
    username: str
    user_id: str


class OutboxProcessResponse(BaseModel):
    processed: int
    succeeded: int
    failed: int
    worker_id: str
