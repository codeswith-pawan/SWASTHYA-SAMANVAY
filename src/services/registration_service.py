"""
Hierarchical Registration Business Logic and Service Layer
AI Powered Smart Hospital Referral System - Phase 1 Task 1C

Implements the multi-tier administrative onboarding pipeline for States, Districts,
and Hospitals, enforcing cryptographic reference generation, parent-child administrative
hierarchy, duplicate prevention, document verification, append-only audit trail,
stage progression, safe public tracking, and final approval eligibility.
"""

import os
import re
import uuid
import secrets
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("registration_service")

from src.database.pg_models import (
    RegistrationApplication,
    RegistrationDocument,
    ApprovalHistory,
    ApplicationTrackingToken,
    VerificationToken,
    AccountActivationToken,
    Hospital,
    User,
)
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
from src.services.document_storage import (
    verify_file_content,
    generate_storage_key,
    get_storage_adapter,
    get_malware_scanner,
    BaseStorageAdapter,
    BaseMalwareScanner,
)

# Canonical Recognized Administrative Hierarchy (Indian States & Districts)
CANONICAL_DIVISIONS: Dict[str, List[str]] = {
    "Bihar": ["Begusarai", "Bhagalpur", "Darbhanga", "Gaya", "Munger", "Muzaffarpur", "Patna", "Purnia"],
    "Delhi": ["East Delhi", "New Delhi", "North Delhi", "South Delhi", "West Delhi"],
    "Gujarat": ["Ahmedabad", "Gandhinagar", "Rajkot", "Surat", "Vadodara"],
    "Karnataka": ["Belagavi", "Bengaluru", "Hubballi", "Mangaluru", "Mysuru"],
    "Maharashtra": ["Aurangabad", "Mumbai", "Nagpur", "Nashik", "Pune", "Thane"],
    "Punjab": ["Amritsar", "Bathinda", "Hoshiarpur", "Jalandhar", "Ludhiana", "Mohali", "Patiala"],
    "Rajasthan": ["Ajmer", "Bikaner", "Jaipur", "Jodhpur", "Kota", "Udaipur"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Salem", "Tiruchirappalli"],
    "Uttar Pradesh": ["Agra", "Gorakhpur", "Kanpur", "Lucknow", "Meerut", "Noida", "Prayagraj", "Varanasi"],
    "West Bengal": ["Asansol", "Durgapur", "Howrah", "Kolkata", "Siliguri"],
    "Haryana": ["Ambala", "Faridabad", "Gurugram", "Hisar", "Panipat", "Rohtak"],
    "Kerala": ["Ernakulam", "Kozhikode", "Malappuram", "Thiruvananthapuram", "Thrissur"],
    "Madhya Pradesh": ["Bhopal", "Gwalior", "Indore", "Jabalpur", "Ujjain"],
    "Odisha": ["Bhubaneswar", "Cuttack", "Puri", "Rourkela", "Sambalpur"],
    "Telangana": ["Hyderabad", "Karimnagar", "Khammam", "Nizamabad", "Warangal"],
    "Andhra Pradesh": ["Guntur", "Kurnool", "Nellore", "Tirupati", "Vijayawada", "Visakhapatnam"],
}

# Reverse mapping: lowercase district -> lowercase state
_DISTRICT_TO_STATE: Dict[str, str] = {
    dist.lower(): state.lower()
    for state, dists in CANONICAL_DIVISIONS.items()
    for dist in dists
}

ACTIVE_STATUSES = ("DRAFT", "SUBMITTED", "UNDER_REVIEW", "CORRECTION_REQUIRED")
MANDATORY_HOSPITAL_DOCS = ("CLINICAL_LICENSE", "FIRE_SAFETY_NOC")
MANDATORY_DISTRICT_DOCS = ("GOVERNMENT_ORDER",)
MANDATORY_STATE_DOCS = ("GOVERNMENT_ORDER",)


class RegistrationService:
    """
    Production-grade service implementing hierarchical registration workflow,
    multi-tier approvals, audit trails, and security controls.
    """

    def __init__(self, session: Session):
        self.session = session

    # ============================================================
    # 1. HIERARCHY & DETAIL VALIDATION
    # ============================================================

    def validate_parent_child_hierarchy(
        self,
        applicant_type: str,
        state: Optional[str],
        district: Optional[str] = None,
    ) -> None:
        """
        Validate parent-child administrative hierarchy:
        - State must be recognized or registered.
        - District must belong to a valid State.
        - Hospital must specify both a valid State and a valid District belonging to that State.
        """
        if not state or not state.strip():
            raise InvalidHierarchyError("State is mandatory and cannot be empty.")

        clean_state = state.strip()
        state_match = None
        for canonical_state in CANONICAL_DIVISIONS:
            if canonical_state.lower() == clean_state.lower():
                state_match = canonical_state
                break

        # If not in canonical static list, check if an approved State application exists in DB
        if not state_match:
            existing_state_app = (
                self.session.query(RegistrationApplication)
                .filter(
                    RegistrationApplication.applicant_type == "STATE",
                    func.lower(RegistrationApplication.state) == clean_state.lower(),
                    RegistrationApplication.status == "APPROVED",
                )
                .first()
            )
            if existing_state_app:
                state_match = existing_state_app.state

        if not state_match:
            raise InvalidHierarchyError(f"State '{clean_state}' is not a recognized or registered state.")

        # District and Hospital require district verification
        if applicant_type in ("DISTRICT", "HOSPITAL"):
            if not district or not district.strip():
                raise InvalidHierarchyError(f"District is mandatory for {applicant_type} registration.")

            clean_district = district.strip()
            # Verify district belongs to the specified state
            known_state_for_dist = _DISTRICT_TO_STATE.get(clean_district.lower())
            if known_state_for_dist and known_state_for_dist != state_match.lower():
                correct_state = next(s for s in CANONICAL_DIVISIONS if s.lower() == known_state_for_dist)
                raise InvalidHierarchyError(
                    f"District '{clean_district}' belongs to State '{correct_state}', not '{state_match}'."
                )

            # Check if district belongs to the canonical list for this state
            canonical_districts = [d.lower() for d in CANONICAL_DIVISIONS.get(state_match, [])]
            if canonical_districts and clean_district.lower() not in canonical_districts:
                # Also allow if an existing hospital or district is recorded in DB for this state
                existing_db_district = (
                    self.session.query(Hospital)
                    .filter(
                        func.lower(Hospital.state) == state_match.lower(),
                        func.lower(Hospital.district) == clean_district.lower(),
                    )
                    .first()
                )
                if not existing_db_district:
                    raise InvalidHierarchyError(
                        f"District '{clean_district}' is not recognized under State '{state_match}'."
                    )

    def validate_registration_details(self, data: Dict[str, Any]) -> None:
        """Validate structure and format of application fields."""
        applicant_type = data.get("applicant_type")
        if applicant_type not in ("STATE", "DISTRICT", "HOSPITAL"):
            raise ValidationError(f"Invalid applicant_type '{applicant_type}'. Must be STATE, DISTRICT, or HOSPITAL.")

        applicant_name = (data.get("applicant_name") or "").strip()
        if not applicant_name or len(applicant_name) < 3:
            raise ValidationError("applicant_name is required and must be at least 3 characters.")

        applicant_email = (data.get("applicant_email") or "").strip()
        email_regex = r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$"
        if not applicant_email or not re.match(email_regex, applicant_email):
            raise ValidationError(f"Invalid applicant_email '{applicant_email}'.")

        applicant_phone = (data.get("applicant_phone") or "").strip()
        phone_digits = re.sub(r"[^\d]", "", applicant_phone)
        if len(phone_digits) < 10:
            raise ValidationError("applicant_phone must contain at least 10 digits.")

        state = data.get("state")
        district = data.get("district")
        self.validate_parent_child_hierarchy(applicant_type, state, district)

    # ============================================================
    # 2. APPLICATION IDENTIFIERS & DUPLICATE PREVENTION
    # ============================================================

    def generate_application_number(self, applicant_type: str) -> str:
        """
        Generate a cryptographically secure, non-guessable, collision-resistant reference number.
        Format: APP-<YYYYMMDD>-<TYPE>-<RANDOM_HEX> (e.g. APP-20261103-HOSP-7F3A92C1)
        """
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        type_prefix = {
            "STATE": "ST",
            "DISTRICT": "DIST",
            "HOSPITAL": "HOSP",
        }.get(applicant_type, "APP")

        for _ in range(10):
            token_entropy = secrets.token_hex(4).upper()  # 4 bytes = 8 hex chars (4.29 billion possibilities)
            candidate = f"APP-{date_str}-{type_prefix}-{token_entropy}"
            exists = (
                self.session.query(RegistrationApplication.application_number)
                .filter(RegistrationApplication.application_number == candidate)
                .first()
            )
            if not exists:
                return candidate

        raise RegistrationServiceError("Failed to generate unique application number after maximum retries.")

    def check_duplicate_active_application(
        self,
        applicant_type: str,
        state: str,
        district: Optional[str] = None,
        applicant_name: Optional[str] = None,
        applicant_email: Optional[str] = None,
    ) -> None:
        """
        Prevent duplicate active applications for the same administrative entity.
        Canonical Entity Identifiers:
        - STATE: LOWER(TRIM(state))
        - DISTRICT: (LOWER(TRIM(state)), LOWER(TRIM(district)))
        - HOSPITAL: LOWER(TRIM(applicant_email))
        Active statuses: DRAFT, SUBMITTED, UNDER_REVIEW, CORRECTION_REQUIRED.
        Applications that are REJECTED or APPROVED do not prevent new applications.
        """
        clean_state = state.strip().lower()

        if applicant_type == "STATE":
            existing = (
                self.session.query(RegistrationApplication)
                .filter(
                    RegistrationApplication.applicant_type == "STATE",
                    func.lower(func.trim(RegistrationApplication.state)) == clean_state,
                    RegistrationApplication.status.in_(ACTIVE_STATUSES),
                )
                .first()
            )
            if existing:
                raise DuplicateApplicationError(
                    f"An active registration application ({existing.application_number}) "
                    f"already exists for State '{state}'."
                )

        elif applicant_type == "DISTRICT":
            clean_district = (district or "").strip().lower()
            existing = (
                self.session.query(RegistrationApplication)
                .filter(
                    RegistrationApplication.applicant_type == "DISTRICT",
                    func.lower(func.trim(RegistrationApplication.state)) == clean_state,
                    func.lower(func.trim(RegistrationApplication.district)) == clean_district,
                    RegistrationApplication.status.in_(ACTIVE_STATUSES),
                )
                .first()
            )
            if existing:
                raise DuplicateApplicationError(
                    f"An active registration application ({existing.application_number}) "
                    f"already exists for District '{district}' in State '{state}'."
                )

        elif applicant_type == "HOSPITAL":
            clean_email = (applicant_email or "").strip().lower()

            existing = (
                self.session.query(RegistrationApplication)
                .filter(
                    RegistrationApplication.applicant_type == "HOSPITAL",
                    func.lower(func.trim(RegistrationApplication.applicant_email)) == clean_email,
                    RegistrationApplication.status.in_(ACTIVE_STATUSES),
                )
                .first()
            )
            if existing:
                raise DuplicateApplicationError(
                    f"An active hospital application ({existing.application_number}) "
                    f"already exists for email '{applicant_email}'."
                )

    # ============================================================
    # 3. APPLICATION CREATION & SUBMISSION
    # ============================================================

    def create_application(self, data: Dict[str, Any]) -> RegistrationApplication:
        """
        Create a new registration application in DRAFT status.
        Validates details, administrative hierarchy, and duplicate active applications.
        Enforces both application-level pre-checks and database-level unique constraints.
        """
        self.validate_registration_details(data)

        applicant_type = data["applicant_type"]
        state = data["state"].strip()
        district = data.get("district", "").strip() if data.get("district") else None
        applicant_name = data["applicant_name"].strip()
        applicant_email = data["applicant_email"].strip().lower()
        applicant_phone = data["applicant_phone"].strip()

        # Check for active duplicates
        self.check_duplicate_active_application(
            applicant_type=applicant_type,
            state=state,
            district=district,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
        )

        app_id = f"APP_{secrets.token_hex(16)}"
        app_num = self.generate_application_number(applicant_type)

        profile_data = dict(data.get("profile_data") or {})
        profile_keys = [
            "total_beds", "available_beds", "icu_beds", "available_icu_beds",
            "emergency_beds", "available_emergency_beds", "latitude", "longitude",
            "emergency_24x7", "accepts_referral", "city"
        ]
        for k in profile_keys:
            if k in data and k not in profile_data:
                profile_data[k] = data[k]

        application = RegistrationApplication(
            application_id=app_id,
            application_number=app_num,
            applicant_type=applicant_type,
            applicant_name=applicant_name,
            applicant_email=applicant_email,
            applicant_phone=applicant_phone,
            state=state,
            district=district,
            city=data.get("city"),
            address=data.get("address"),
            pincode=data.get("pincode"),
            official_designation=data.get("official_designation"),
            nodal_officer_name=data.get("nodal_officer_name"),
            parent_state=state if applicant_type != "STATE" else None,
            parent_district=district if applicant_type == "HOSPITAL" else None,
            profile_data=profile_data if profile_data else None,
            current_stage="DRAFT",
            status="DRAFT",
            resubmission_version=1,
        )

        self.session.add(application)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()

            # Extract exact PostgreSQL constraint name from driver diagnostic or SQLite error text
            constraint_name = None
            if hasattr(exc, "orig") and exc.orig is not None:
                diag = getattr(exc.orig, "diag", None)
                if diag and getattr(diag, "constraint_name", None):
                    constraint_name = diag.constraint_name
                else:
                    orig_str = str(exc.orig)
                    for target in ("uq_reg_app_active_state", "uq_reg_app_active_district", "uq_reg_app_active_hospital_email"):
                        if target in orig_str:
                            constraint_name = target
                            break

            # Only violations of the three intended partial unique indexes become DuplicateApplicationError
            if constraint_name == "uq_reg_app_active_state":
                raise DuplicateApplicationError(
                    f"An active registration application already exists for State '{state}'."
                ) from exc
            elif constraint_name == "uq_reg_app_active_district":
                raise DuplicateApplicationError(
                    f"An active registration application already exists for District '{district}' in State '{state}'."
                ) from exc
            elif constraint_name == "uq_reg_app_active_hospital_email":
                raise DuplicateApplicationError(
                    f"An active hospital application already exists for email '{applicant_email}'."
                ) from exc
            else:
                # Unexpected integrity violations (e.g. Foreign Key, NOT NULL, CHECK constraints)
                # must NOT be misreported as duplicates. Re-raise original database exception.
                raise exc

        return application

    def update_draft_application(self, application_id: str, updates: Dict[str, Any]) -> RegistrationApplication:
        """
        Update an existing registration application while in DRAFT status.
        Only mutable fields (contact details, address, designation, profile data) can be updated.
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status != "DRAFT":
            raise InvalidStageTransitionError(
                f"Application is in status '{app.status}'. Only DRAFT applications can be updated."
            )

        # Update allowed fields
        if "applicant_name" in updates and updates["applicant_name"]:
            app.applicant_name = updates["applicant_name"].strip()

        if "applicant_phone" in updates and updates["applicant_phone"]:
            phone = updates["applicant_phone"].strip()
            digits = re.sub(r"\D", "", phone)
            if len(digits) < 10:
                raise ValidationError("applicant_phone must contain at least 10 digits.")
            app.applicant_phone = phone

        if "city" in updates:
            app.city = updates["city"].strip() if updates["city"] else None
        if "address" in updates:
            app.address = updates["address"].strip() if updates["address"] else None
        if "pincode" in updates:
            app.pincode = updates["pincode"].strip() if updates["pincode"] else None
        if "official_designation" in updates:
            app.official_designation = updates["official_designation"].strip() if updates["official_designation"] else None
        if "nodal_officer_name" in updates:
            app.nodal_officer_name = updates["nodal_officer_name"].strip() if updates["nodal_officer_name"] else None
        if "profile_data" in updates:
            app.profile_data = updates["profile_data"]

        app.last_updated_at = datetime.now(timezone.utc)
        self.session.flush()
        return app

    def create_tracking_token(self, application_id: str, days_valid: int = 90) -> Tuple[ApplicationTrackingToken, str]:
        """
        Generate a secure, reusable, time-bound public tracking token.
        Stores the SHA-256 hash in application_tracking_tokens and returns (token_model, raw_secret).
        """
        raw_secret = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()
        token_id = f"TRK_{secrets.token_hex(16)}"

        now = datetime.now(timezone.utc)
        token_model = ApplicationTrackingToken(
            tracking_token_id=token_id,
            application_id=application_id,
            token_hash=token_hash,
            is_revoked=False,
            expires_at=now + timedelta(days=days_valid),
            access_count=0,
        )
        self.session.add(token_model)
        self.session.flush()
        return token_model, raw_secret

    def submit_application(
        self,
        application_id: str,
        remarks: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Submit a DRAFT application into the review pipeline:
        - Validates mandatory uploaded documents.
        - Sets status to SUBMITTED.
        - Sets current_stage based on applicant_type:
            * HOSPITAL -> DISTRICT_REVIEW
            * DISTRICT -> STATE_REVIEW
            * STATE    -> CENTRAL_REVIEW
        - Emits append-only ApprovalHistory record with action='SUBMIT'.
        - Generates public tracking token.
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status != "DRAFT":
            raise InvalidStageTransitionError(
                f"Application is in status '{app.status}'. Only DRAFT applications can be submitted."
            )

        # Validate mandatory documents for the applicant type
        uploaded_doc_types = {doc.document_type for doc in app.documents}
        if app.applicant_type == "HOSPITAL":
            missing = [d for d in MANDATORY_HOSPITAL_DOCS if d not in uploaded_doc_types]
            if missing:
                raise DocumentError(f"Missing mandatory hospital documents: {', '.join(missing)}.")
        elif app.applicant_type == "DISTRICT":
            missing = [d for d in MANDATORY_DISTRICT_DOCS if d not in uploaded_doc_types]
            if missing:
                raise DocumentError(f"Missing mandatory district documents: {', '.join(missing)}.")
        elif app.applicant_type == "STATE":
            missing = [d for d in MANDATORY_STATE_DOCS if d not in uploaded_doc_types]
            if missing:
                raise DocumentError(f"Missing mandatory state documents: {', '.join(missing)}.")

        # Determine initial review stage based on hierarchy
        initial_stage = {
            "HOSPITAL": "DISTRICT_REVIEW",
            "DISTRICT": "STATE_REVIEW",
            "STATE": "CENTRAL_REVIEW",
        }[app.applicant_type]

        old_status = app.status
        app.status = "SUBMITTED"
        app.current_stage = initial_stage

        # Append-only audit history record
        history_entry = ApprovalHistory(
            application_id=app.application_id,
            reviewer_user_id=None,
            reviewer_role="APPLICANT",
            action="SUBMIT",
            review_tier="APPLICANT",
            previous_status=old_status,
            new_status="SUBMITTED",
            remarks=remarks or "Initial application submission by applicant",
            ip_address=client_ip,
        )
        self.session.add(history_entry)

        # Generate public tracking token
        _, raw_token = self.create_tracking_token(app.application_id)
        self.session.flush()

        # Phase 4D-2: Hierarchical in-app notifications and email outbox dispatch
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            workflow_notif_svc = WorkflowNotificationService(self.session)
            workflow_notif_svc.notify_application_submitted(app, tracking_token=raw_token, client_ip=client_ip)
        except Exception as notif_err:
            logger.error("Failed to generate workflow notifications for submission %s: %s", app.application_id, notif_err)

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "status": app.status,
            "current_stage": app.current_stage,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "tracking_token": raw_token,
        }

    # ============================================================
    # 4. DOCUMENT METADATA & VERIFICATION
    # ============================================================

    def add_document_metadata(
        self,
        application_id: str,
        document_type: str,
        original_filename: str,
        mime_type: str,
        file_size_bytes: int,
        storage_key: str,
        checksum_sha256: str,
    ) -> RegistrationDocument:
        """
        Store document metadata securely with cryptographic checksum and size checks.
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status in ("APPROVED", "REJECTED"):
            raise InvalidStageTransitionError(f"Cannot upload documents to an application in status '{app.status}'.")

        allowed_types = (
            "CLINICAL_LICENSE",
            "FIRE_SAFETY_NOC",
            "POLLUTION_CONTROL_NOC",
            "MEDICAL_COUNCIL_AFFILIATION",
            "GOVERNMENT_ORDER",
            "IDENTITY_PROOF",
            "OTHER",
        )
        if document_type not in allowed_types:
            raise DocumentError(f"Invalid document_type '{document_type}'. Allowed types: {', '.join(allowed_types)}.")

        # File size constraint: max 25MB (26,214,400 bytes)
        MAX_DOCUMENT_SIZE = 26_214_400
        if file_size_bytes <= 0:
            raise DocumentError("file_size_bytes must be greater than 0.")
        if file_size_bytes > MAX_DOCUMENT_SIZE:
            raise DocumentError(
                f"file_size_bytes ({file_size_bytes} bytes) exceeds maximum allowed size of 25MB ({MAX_DOCUMENT_SIZE} bytes)."
            )

        # MIME type whitelist validation
        allowed_mimes = ("application/pdf", "image/jpeg", "image/png")
        clean_mime = mime_type.strip().lower()
        if clean_mime not in allowed_mimes:
            raise DocumentError(
                f"Unsupported mime_type '{mime_type}'. Allowed types: {', '.join(allowed_mimes)}."
            )

        # Filename sanitization and path traversal prevention
        if not original_filename or not original_filename.strip():
            raise DocumentError("original_filename cannot be empty.")
        if "\x00" in original_filename:
            raise DocumentError("Filename contains invalid null byte.")
        if "/" in original_filename or "\\" in original_filename or ".." in original_filename:
            raise DocumentError("Filename must not contain path separators or directory traversal sequences.")

        clean_filename = os.path.basename(original_filename.strip())
        if not re.match(r"^[a-zA-Z0-9_\-\. ]+$", clean_filename) or clean_filename.startswith("."):
            raise DocumentError("Filename contains unsafe characters. Allowed: alphanumeric, underscore, hyphen, space, dot.")
        if len(clean_filename) > 255:
            raise DocumentError("original_filename exceeds maximum length of 255 characters.")

        # Checksum validation
        clean_checksum = checksum_sha256.strip().lower()
        if len(clean_checksum) != 64 or not re.match(r"^[0-9a-f]{64}$", clean_checksum):
            raise DocumentError("checksum_sha256 must be a valid 64-character lowercase hex string.")

        # Authoritative server-side storage key generation (immune to client-side path traversal)
        # NOTE: Phase 1 Task 1D registers document metadata; binary file stream upload, malware scanning,
        # and magic-number byte header verification occur at the object storage boundary (Phase 1 Task 1E/1F).
        safe_name_slug = clean_filename.replace(" ", "_")
        server_storage_key = f"documents/{application_id}/{secrets.token_hex(16)}_{safe_name_slug}"

        doc_id = f"DOC_{secrets.token_hex(16)}"
        doc = RegistrationDocument(
            document_id=doc_id,
            application_id=application_id,
            document_type=document_type,
            storage_key=server_storage_key,
            original_filename=clean_filename,
            mime_type=clean_mime,
            file_size_bytes=file_size_bytes,
            checksum_sha256=clean_checksum,
            verification_status="PENDING",
        )
        self.session.add(doc)
        self.session.flush()
        return doc

    def upload_document_binary(
        self,
        application_id: str,
        document_type: str,
        file_bytes: bytes,
        declared_mime: Optional[str] = None,
        original_filename: Optional[str] = None,
        storage_adapter: Optional[BaseStorageAdapter] = None,
        scanner: Optional[BaseMalwareScanner] = None,
    ) -> RegistrationDocument:
        """
        Secure multipart document binary upload (Phase 1 Task 1E):
        1. Enforces application is in editable status (DRAFT or CORRECTION_REQUIRED).
        2. Validates document type against allowed enum.
        3. Validates file content, enforces <= 25MB, checks magic bytes (PDF, JPEG, PNG).
        4. Scans for malware / viruses using ClamAV or simulated scanner.
        5. Computes SHA-256 checksum and generates authoritative storage key.
        6. Persists binary stream via storage adapter.
        7. Handles document replacement / versioning if document_type already exists.
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status not in ("DRAFT", "CORRECTION_REQUIRED"):
            raise InvalidStageTransitionError(
                f"Cannot upload documents for application in '{app.status}' status. Upload is only permitted in DRAFT or CORRECTION_REQUIRED."
            )

        allowed_types = (
            "CLINICAL_LICENSE",
            "FIRE_SAFETY_NOC",
            "POLLUTION_CONTROL_NOC",
            "MEDICAL_COUNCIL_AFFILIATION",
            "GOVERNMENT_ORDER",
            "IDENTITY_PROOF",
            "OTHER",
        )
        if document_type not in allowed_types:
            raise DocumentError(f"Invalid document_type '{document_type}'. Allowed types: {', '.join(allowed_types)}.")

        # Content validation, magic bytes, size limit, filename traversal check, checksum
        verified = verify_file_content(
            file_bytes=file_bytes,
            declared_mime=declared_mime,
            original_filename=original_filename,
        )

        # Antivirus scan
        active_scanner = scanner or get_malware_scanner()
        active_scanner.scan_bytes(file_bytes, verified["clean_filename"])

        # Storage persistence
        active_storage = storage_adapter or get_storage_adapter()
        server_storage_key = generate_storage_key(application_id, verified["clean_filename"])
        active_storage.put_object(server_storage_key, file_bytes, verified["verified_mime"])

        # Check for existing document of this type (Replacement / Versioning)
        # When replaced, the old document row and blob are deleted, generating a fresh document_id.
        # This guarantees that stale identifiers cannot be used to retrieve replaced documents.
        existing_doc = (
            self.session.query(RegistrationDocument)
            .filter_by(application_id=application_id, document_type=document_type)
            .first()
        )
        if existing_doc:
            # Delete old blob from storage
            try:
                active_storage.delete_object(existing_doc.storage_key)
            except Exception as e:
                logger.warning("Could not delete previous document blob '%s': %s", existing_doc.storage_key, e)

            self.session.delete(existing_doc)
            self.session.flush()

        # Create new document record with fresh document_id
        doc_id = f"DOC_{secrets.token_hex(16)}"
        doc = RegistrationDocument(
            document_id=doc_id,
            application_id=application_id,
            document_type=document_type,
            storage_key=server_storage_key,
            original_filename=verified["clean_filename"],
            mime_type=verified["verified_mime"],
            file_size_bytes=verified["file_size_bytes"],
            checksum_sha256=verified["checksum_sha256"],
            verification_status="PENDING",
            uploaded_at=datetime.now(timezone.utc),
        )
        self.session.add(doc)
        self.session.flush()
        return doc

    def get_document_for_download(
        self,
        document_id: str,
        user_context: Dict[str, Any],
        storage_adapter: Optional[BaseStorageAdapter] = None,
    ) -> Tuple[bytes, str, str]:
        """
        Secure retrieval of document binary:
        - Verifies document exists.
        - Enforces strict authorization:
          * APPLICANT: must be bound to the exact application.
          * REVIEWER: must have jurisdiction over the application at its current stage.
          * Unrelated users / hospital staff: safely rejected.
        - Returns (file_bytes, original_filename, mime_type).
        """
        doc = self.session.query(RegistrationDocument).filter_by(document_id=document_id).first()
        if not doc:
            raise DocumentError(f"Document '{document_id}' not found.")

        app = doc.application
        role = user_context.get("role") or user_context.get("role_id")

        if role == "APPLICANT":
            applicant_app_id = user_context.get("application_id")
            if not applicant_app_id or applicant_app_id != app.application_id:
                raise GeographicAccessError("Access denied: You can only access documents attached to your own application.")
        elif role in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            self._validate_reviewer_authority(user_context, app)
        else:
            raise UnauthorizedReviewerError("Unauthorized access to document.")

        active_storage = storage_adapter or get_storage_adapter()
        file_bytes = active_storage.get_object(doc.storage_key)
        return file_bytes, doc.original_filename, doc.mime_type

    def delete_document(
        self,
        document_id: str,
        applicant_context: Dict[str, Any],
        storage_adapter: Optional[BaseStorageAdapter] = None,
    ) -> bool:
        """
        Safely delete document blob and database record.
        Permitted only for applicant while application is in DRAFT or CORRECTION_REQUIRED.
        """
        doc = self.session.query(RegistrationDocument).filter_by(document_id=document_id).first()
        if not doc:
            raise DocumentError(f"Document '{document_id}' not found.")

        app = doc.application
        if applicant_context.get("application_id") != app.application_id:
            raise GeographicAccessError("Access denied: You can only delete documents from your own application.")

        if app.status not in ("DRAFT", "CORRECTION_REQUIRED"):
            raise InvalidStageTransitionError(
                f"Cannot delete document while application is in '{app.status}' status."
            )

        active_storage = storage_adapter or get_storage_adapter()
        try:
            active_storage.delete_object(doc.storage_key)
        except Exception as e:
            logger.warning("Could not delete storage blob '%s': %s", doc.storage_key, e)

        self.session.delete(doc)
        self.session.flush()
        return True

    def verify_document(
        self,
        document_id: str,
        reviewer_user: Dict[str, Any],
        verification_status: str,
        reviewer_remarks: Optional[str] = None,
    ) -> RegistrationDocument:
        """
        Record document verification status (VERIFIED or REJECTED) by an authorized reviewer.
        """
        if verification_status not in ("VERIFIED", "REJECTED"):
            raise DocumentError("verification_status must be either 'VERIFIED' or 'REJECTED'.")

        doc = self.session.query(RegistrationDocument).filter_by(document_id=document_id).first()
        if not doc:
            raise DocumentError(f"Document '{document_id}' not found.")

        app = doc.application
        self._validate_reviewer_authority(reviewer_user, app)

        doc.verification_status = verification_status
        doc.reviewer_id = reviewer_user.get("user_id")
        doc.reviewer_remarks = reviewer_remarks
        doc.reviewed_at = datetime.now(timezone.utc)
        self.session.flush()
        return doc

    # ============================================================
    # 5. REVIEW, FORWARDING, APPROVAL & REJECTION
    # ============================================================

    def _validate_reviewer_authority(self, reviewer: Dict[str, Any], app: RegistrationApplication) -> None:
        """
        Validate reviewer role, jurisdiction, and prevent self-approval.
        """
        if not reviewer or not reviewer.get("role"):
            raise UnauthorizedReviewerError("Reviewer credentials and role are required.")

        reviewer_role = reviewer["role"]
        reviewer_id = reviewer.get("user_id")

        # 1. Prevent self-approval with strict normalization across email, user_id, username, and nodal identity
        rev_email = (reviewer.get("email") or "").strip().lower()
        rev_id = str(reviewer_id or "").strip().lower()
        rev_username = str(reviewer.get("username") or "").strip().lower()
        app_email = (app.applicant_email or "").strip().lower()
        app_nodal = (app.nodal_officer_name or "").strip().lower()
        app_entity = (app.provisioned_entity_id or "").strip().lower()

        is_self_review = False
        if app_email and (rev_email == app_email or rev_id == app_email or rev_username == app_email):
            is_self_review = True
        elif app_nodal and (rev_id == app_nodal or rev_username == app_nodal or rev_email == app_nodal):
            is_self_review = True
        elif app_entity and (rev_id == app_entity or rev_username == app_entity):
            is_self_review = True

        if is_self_review:
            raise SelfApprovalError("Applicant cannot review or approve their own application.")

        # Hospital staff can NEVER review registration applications
        if reviewer_role == "HOSPITAL":
            raise UnauthorizedReviewerError("Hospital staff role is not permitted to review registration applications.")

        # 2. Stage authority check
        current_stage = app.current_stage

        if current_stage == "DISTRICT_REVIEW":
            if reviewer_role != "DISTRICT_ADMIN":
                raise UnauthorizedReviewerError(
                    f"Only DISTRICT_ADMIN can review at DISTRICT_REVIEW stage. Received role: '{reviewer_role}'."
                )
            # Geographic jurisdiction check
            rev_state = (reviewer.get("state") or "").lower()
            rev_district = (reviewer.get("district") or "").lower()
            if rev_state != (app.state or "").lower() or rev_district != (app.district or "").lower():
                raise GeographicAccessError(
                    f"District Admin ({reviewer.get('district')}, {reviewer.get('state')}) "
                    f"cannot review application in ({app.district}, {app.state})."
                )

        elif current_stage == "STATE_REVIEW":
            if reviewer_role != "STATE_ADMIN":
                raise UnauthorizedReviewerError(
                    f"Only STATE_ADMIN can review at STATE_REVIEW stage. Received role: '{reviewer_role}'."
                )
            rev_state = (reviewer.get("state") or "").lower()
            if rev_state != (app.state or "").lower():
                raise GeographicAccessError(
                    f"State Admin ({reviewer.get('state')}) cannot review application in State ({app.state})."
                )

        elif current_stage == "CENTRAL_REVIEW":
            if reviewer_role != "CENTRAL_ADMIN":
                raise UnauthorizedReviewerError(
                    f"Only CENTRAL_ADMIN can review at CENTRAL_REVIEW stage. Received role: '{reviewer_role}'."
                )

        else:
            raise InvalidStageTransitionError(
                f"Application is in terminal or non-reviewable stage '{current_stage}'."
            )

    def review_application(
        self,
        application_id: str,
        reviewer_user: Dict[str, Any],
        action: str,  # 'FORWARD', 'APPROVE', 'REJECT'
        remarks: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Advance an application along the administrative approval hierarchy or reject it:
        - Hospital: DISTRICT_REVIEW -> STATE_REVIEW -> CENTRAL_REVIEW -> APPROVED
        - District: STATE_REVIEW -> CENTRAL_REVIEW -> APPROVED
        - State:    CENTRAL_REVIEW -> APPROVED
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status in ("APPROVED", "REJECTED"):
            raise InvalidStageTransitionError(f"Cannot review application already in terminal status '{app.status}'.")

        self._validate_reviewer_authority(reviewer_user, app)

        old_status = app.status
        old_stage = app.current_stage
        reviewer_role = reviewer_user["role"]

        current_tier = {
            "DISTRICT_ADMIN": "DISTRICT",
            "STATE_ADMIN": "STATE",
            "CENTRAL_ADMIN": "CENTRAL",
        }.get(reviewer_role, "CENTRAL")

        if action == "REJECT":
            app.status = "REJECTED"
            app.current_stage = "REJECTED"
            app.rejection_reason = remarks or "Application rejected by reviewer."

            history_entry = ApprovalHistory(
                application_id=app.application_id,
                reviewer_user_id=reviewer_user.get("user_id"),
                reviewer_role=reviewer_role,
                action="REJECT",
                review_tier=current_tier,
                previous_status=old_status,
                new_status="REJECTED",
                remarks=remarks or "Application rejected.",
                ip_address=client_ip,
            )
            self.session.add(history_entry)
            self.session.flush()

            # Phase 4D-2: Applicant rejection notification & email dispatch
            try:
                from src.services.workflow_notification_service import WorkflowNotificationService
                workflow_notif_svc = WorkflowNotificationService(self.session)
                workflow_notif_svc.notify_application_rejected(
                    app, rejection_reason=app.rejection_reason, reviewer_user=reviewer_user, client_ip=client_ip
                )
            except Exception as notif_err:
                logger.error("Failed to generate rejection notifications for app %s: %s", app.application_id, notif_err)

            return {
                "application_id": app.application_id,
                "application_number": app.application_number,
                "status": "REJECTED",
                "current_stage": "REJECTED",
                "new_status": "REJECTED",
                "new_stage": "REJECTED",
                "action": "REJECT",
            }

        if action in ("FORWARD", "APPROVE"):
            provision_res = None
            # Progress based on current stage
            if old_stage == "DISTRICT_REVIEW":
                # District approval forwards to State Review
                app.status = "UNDER_REVIEW"
                app.current_stage = "STATE_REVIEW"
                recorded_action = "FORWARD"
                new_status = "UNDER_REVIEW"

            elif old_stage == "STATE_REVIEW":
                # State approval forwards to Central Review
                app.status = "UNDER_REVIEW"
                app.current_stage = "CENTRAL_REVIEW"
                recorded_action = "FORWARD"
                new_status = "UNDER_REVIEW"

            elif old_stage == "CENTRAL_REVIEW":
                # Final Central approval: must verify final eligibility
                is_eligible, issues = self.check_final_approval_eligibility(app.application_id)
                if not is_eligible:
                    raise IneligibleForApprovalError(
                        f"Application is ineligible for final approval: {'; '.join(issues)}"
                    )

                app.status = "APPROVED"
                app.current_stage = "APPROVED"
                app.final_approved_at = datetime.now(timezone.utc)
                recorded_action = "APPROVE"
                new_status = "APPROVED"

                # Trigger operational account provisioning within the same atomic transaction
                from src.services.account_provisioning_service import AccountProvisioningService
                provisioning_svc = AccountProvisioningService(self.session)
                provision_res = provisioning_svc.provision_account(
                    application_id=app.application_id,
                    reviewer_user=reviewer_user,
                    client_ip=client_ip,
                )

            else:
                provision_res = None
                raise InvalidStageTransitionError(f"Cannot forward application from stage '{old_stage}'.")

            history_entry = ApprovalHistory(
                application_id=app.application_id,
                reviewer_user_id=reviewer_user.get("user_id"),
                reviewer_role=reviewer_role,
                action=recorded_action,
                review_tier=current_tier,
                previous_status=old_status,
                new_status=new_status,
                remarks=remarks or f"Progressed from {old_stage} to {app.current_stage}",
                ip_address=client_ip,
            )
            self.session.add(history_entry)
            self.session.flush()

            # Phase 4D-2: Workflow notifications for stage forwarding or final approval
            try:
                from src.services.workflow_notification_service import WorkflowNotificationService
                workflow_notif_svc = WorkflowNotificationService(self.session)
                if recorded_action == "FORWARD":
                    workflow_notif_svc.notify_stage_forwarded(
                        app, previous_stage=old_stage, new_stage=app.current_stage, reviewer_user=reviewer_user, client_ip=client_ip
                    )
                elif recorded_action == "APPROVE":
                    workflow_notif_svc.notify_final_approval(
                        app, reviewer_user=reviewer_user, client_ip=client_ip
                    )
            except Exception as notif_err:
                logger.error("Failed to generate approval/forward notifications for app %s: %s", app.application_id, notif_err)

            resp_data = {
                "application_id": app.application_id,
                "application_number": app.application_number,
                "status": app.status,
                "current_stage": app.current_stage,
                "new_status": app.status,
                "new_stage": app.current_stage,
                "action": recorded_action,
                "final_approved_at": app.final_approved_at.isoformat() if app.final_approved_at else None,
            }
            if provision_res is not None:
                resp_data["provisioning"] = provision_res
            return resp_data

        raise ValidationError(f"Invalid action '{action}'. Must be FORWARD, APPROVE, or REJECT.")

    # ============================================================
    # 6. CORRECTION & RESUBMISSION WORKFLOW
    # ============================================================

    def request_correction(
        self,
        application_id: str,
        reviewer_user: Dict[str, Any],
        correction_notes: str,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Request corrections from the applicant:
        - Sets status to CORRECTION_REQUIRED.
        - Preserves the current_stage where correction was requested.
        - Records append-only ApprovalHistory with action='REQUEST_CORRECTION'.
        """
        if not correction_notes or not correction_notes.strip():
            raise ValidationError("correction_notes are required when requesting correction.")

        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status in ("APPROVED", "REJECTED"):
            raise InvalidStageTransitionError(f"Cannot request corrections on application in status '{app.status}'.")

        self._validate_reviewer_authority(reviewer_user, app)

        old_status = app.status
        app.status = "CORRECTION_REQUIRED"
        app.correction_notes = correction_notes.strip()

        reviewer_role = reviewer_user["role"]
        current_tier = {
            "DISTRICT_ADMIN": "DISTRICT",
            "STATE_ADMIN": "STATE",
            "CENTRAL_ADMIN": "CENTRAL",
        }.get(reviewer_role, "CENTRAL")

        history_entry = ApprovalHistory(
            application_id=app.application_id,
            reviewer_user_id=reviewer_user.get("user_id"),
            reviewer_role=reviewer_role,
            action="REQUEST_CORRECTION",
            review_tier=current_tier,
            previous_status=old_status,
            new_status="CORRECTION_REQUIRED",
            remarks=correction_notes.strip(),
            ip_address=client_ip,
        )
        self.session.add(history_entry)
        self.session.flush()

        # Phase 4D-2: Correction request notification & outbox email
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            workflow_notif_svc = WorkflowNotificationService(self.session)
            workflow_notif_svc.notify_correction_requested(
                app, correction_notes=correction_notes.strip(), reviewer_user=reviewer_user, client_ip=client_ip
            )
        except Exception as notif_err:
            logger.error("Failed to generate correction request notifications for app %s: %s", app.application_id, notif_err)

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "status": app.status,
            "current_stage": app.current_stage,
            "correction_notes": app.correction_notes,
        }

    def resubmit_application(
        self,
        application_id: str,
        applicant_notes: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Applicant resubmits following requested corrections:
        - Sets status back to SUBMITTED.
        - Preserves submitted_at and current_stage.
        - Increments resubmission_version (handled by model/trigger).
        - Records append-only ApprovalHistory with action='RESUBMIT'.
        """
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            raise ApplicationNotFoundError(f"Application '{application_id}' not found.")

        if app.status != "CORRECTION_REQUIRED":
            raise InvalidStageTransitionError(
                f"Application is in status '{app.status}'. Only CORRECTION_REQUIRED applications can be resubmitted."
            )

        old_status = app.status
        app.status = "SUBMITTED"

        # Record append-only ApprovalHistory entry for RESUBMIT
        history_entry = ApprovalHistory(
            application_id=app.application_id,
            reviewer_user_id=None,
            reviewer_role="APPLICANT",
            action="RESUBMIT",
            review_tier="APPLICANT",
            previous_status=old_status,
            new_status="SUBMITTED",
            remarks=applicant_notes or "Applicant resubmitted following corrections.",
            ip_address=client_ip,
        )
        self.session.add(history_entry)
        self.session.flush()

        # Phase 4D-2: Resubmission confirmation & reviewer alert
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            workflow_notif_svc = WorkflowNotificationService(self.session)
            workflow_notif_svc.notify_application_resubmitted(
                app, applicant_notes=applicant_notes, client_ip=client_ip
            )
        except Exception as notif_err:
            logger.error("Failed to generate resubmission notifications for app %s: %s", app.application_id, notif_err)

        return {
            "application_id": app.application_id,
            "application_number": app.application_number,
            "status": app.status,
            "current_stage": app.current_stage,
            "resubmission_version": app.resubmission_version,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "resubmitted_at": app.resubmitted_at.isoformat() if app.resubmitted_at else None,
        }

    # ============================================================
    # 7. FINAL APPROVAL ELIGIBILITY CHECKS
    # ============================================================

    def check_final_approval_eligibility(self, application_id: str) -> Tuple[bool, List[str]]:
        """
        Evaluate comprehensive eligibility criteria before granting final approval:
        1. Current stage must be CENTRAL_REVIEW.
        2. Status must be active (SUBMITTED or UNDER_REVIEW).
        3. Mandatory documents exist for the applicant type.
        4. Every attached document has verification_status == 'VERIFIED'.
        5. Administrative hierarchy is valid.
        6. Essential fields are complete.
        """
        issues: List[str] = []
        app = self.session.query(RegistrationApplication).filter_by(application_id=application_id).first()
        if not app:
            return False, ["Application not found."]

        # 1. Stage and status check
        if app.current_stage != "CENTRAL_REVIEW":
            issues.append(f"Application is at stage '{app.current_stage}'; final approval requires CENTRAL_REVIEW.")

        if app.status not in ("SUBMITTED", "UNDER_REVIEW"):
            issues.append(f"Application status is '{app.status}'; must be SUBMITTED or UNDER_REVIEW.")

        # 2. Mandatory documents check
        uploaded_doc_types = {doc.document_type for doc in app.documents}
        if app.applicant_type == "HOSPITAL":
            missing = [d for d in MANDATORY_HOSPITAL_DOCS if d not in uploaded_doc_types]
            if missing:
                issues.append(f"Missing mandatory documents: {', '.join(missing)}.")
        elif app.applicant_type in ("DISTRICT", "STATE"):
            if "GOVERNMENT_ORDER" not in uploaded_doc_types:
                issues.append("Missing mandatory GOVERNMENT_ORDER document.")

        # 3. Document verification check: all attached documents must be VERIFIED
        if not app.documents:
            issues.append("No documents attached to application.")
        else:
            unverified = [doc for doc in app.documents if doc.verification_status != "VERIFIED"]
            if unverified:
                unverified_names = [f"{d.document_type} ({d.verification_status})" for d in unverified]
                issues.append(f"Documents pending verification: {', '.join(unverified_names)}.")

        # 4. Mandatory contact details check
        if not app.applicant_email or not app.applicant_phone:
            issues.append("Incomplete applicant contact details.")

        # 5. Hierarchy check
        try:
            self.validate_parent_child_hierarchy(app.applicant_type, app.state, app.district)
        except InvalidHierarchyError as e:
            issues.append(f"Hierarchy violation: {str(e)}")

        is_eligible = len(issues) == 0
        return is_eligible, issues

    # ============================================================
    # 8. SAFE PUBLIC TRACKING SERVICE
    # ============================================================

    def track_application_public(
        self,
        application_number: str,
        tracking_token: str,
    ) -> Dict[str, Any]:
        """
        Public status tracking service that exposes strictly sanitized, safe information.
        Mandatory tracking_token validation ensures only authorized parties with the token can query status.
        Uses uniform error responses to eliminate application number enumeration oracles.
        """
        if not tracking_token or not tracking_token.strip():
            raise TrackingTokenError("Tracking token is required.")

        app = (
            self.session.query(RegistrationApplication)
            .filter_by(application_number=application_number.strip())
            .first()
        )
        if not app:
            # Uniform error: does not leak whether application number exists
            raise TrackingTokenError("Invalid application number or tracking token.")

        token_hash = hashlib.sha256(tracking_token.strip().encode("utf-8")).hexdigest()
        tok = (
            self.session.query(ApplicationTrackingToken)
            .filter_by(application_id=app.application_id, token_hash=token_hash)
            .first()
        )
        if not tok or tok.is_revoked:
            raise TrackingTokenError("Invalid application number or tracking token.")

        now = datetime.now(timezone.utc)
        tok_exp = tok.expires_at if tok.expires_at.tzinfo else tok.expires_at.replace(tzinfo=timezone.utc)
        if tok_exp < now:
            raise TrackingTokenError("Invalid application number or tracking token.")

        tok.access_count += 1
        tok.last_accessed_at = now
        self.session.flush()

        # Build sanitized public milestones (action & stage without private remarks or reviewer IDs)
        milestones = []
        for h in app.history:
            milestones.append({
                "stage": h.review_tier,
                "action": h.action,
                "status": h.new_status,
                "timestamp": h.created_at.isoformat() if h.created_at else None,
            })

        return {
            "application_number": app.application_number,
            "applicant_type": app.applicant_type,
            "applicant_name": app.applicant_name,
            "state": app.state,
            "district": app.district,
            "status": app.status,
            "current_stage": app.current_stage,
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "submitted_at": app.submitted_at.isoformat() if app.submitted_at else None,
            "resubmission_version": app.resubmission_version,
            "milestones": milestones,
        }
