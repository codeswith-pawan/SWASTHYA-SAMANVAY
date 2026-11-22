"""
Hierarchical Workflow Notification & Recipient Resolution Service
AI Powered Smart Hospital Referral System - Phase 4D-2

Handles reliable in-app alerts and transactional email outbox enqueueing for:
- Applicant registration submission, corrections, resubmissions, approvals, and rejections.
- Hierarchical government reviewer dispatch (District, State, Central) with strict jurisdiction routing.
- Idempotency protection, operational audit logging for unresolvable recipients, and privacy preservation.
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from src.database.pg_models import (
    Notification,
    RegistrationApplication,
    RegistrationEmailOutbox,
    User,
    AuditLog,
)
from src.services.email_outbox_service import EmailOutboxService

logger = logging.getLogger("workflow_notifications")

DEFAULT_PORTAL_BASE_URL = "http://localhost:3000"


def get_portal_base_url() -> str:
    """Return configured frontend base URL from env or SystemSettings."""
    from src.config import get_settings
    env_override = os.getenv("PORTAL_BASE_URL") or os.getenv("SIH_PORTAL_BASE_URL")
    if env_override and env_override.strip():
        return env_override.strip().rstrip("/")
    try:
        settings = get_settings()
        if settings.portal_base_url:
            return settings.portal_base_url.rstrip("/")
    except Exception:
        pass
    return DEFAULT_PORTAL_BASE_URL


class WorkflowNotificationService:
    """
    Manages in-app notifications and transactional email outbox dispatch
    for the registration review pipeline.
    """

    def __init__(self, session: Session):
        self.session = session
        self.outbox_service = EmailOutboxService(session)

    # ============================================================
    # 1. HIERARCHICAL RECIPIENT RESOLUTION
    # ============================================================

    def resolve_reviewers(
        self,
        target_stage: str,
        application: RegistrationApplication,
        client_ip: Optional[str] = None,
    ) -> List[User]:
        """
        Resolves active reviewer users matching the hierarchical jurisdiction
        for the given review stage.
        - DISTRICT_REVIEW: DISTRICT_ADMIN users matching application state & district.
        - STATE_REVIEW:    STATE_ADMIN users matching application state.
        - CENTRAL_REVIEW:  CENTRAL_ADMIN users.

        If no active reviewer exists, records an AuditLog operational warning
        without failing the business transaction or inventing fake emails.
        """
        reviewers: List[User] = []

        if target_stage == "DISTRICT_REVIEW":
            if not application.district:
                logger.warning(
                    "Application %s has no district specified for DISTRICT_REVIEW routing.",
                    application.application_id,
                )
            else:
                reviewers = (
                    self.session.query(User)
                    .filter(
                        User.role_id == "DISTRICT_ADMIN",
                        User.is_active == True,
                        func.lower(User.state) == func.lower(application.state),
                        func.lower(User.district) == func.lower(application.district),
                    )
                    .all()
                )

        elif target_stage == "STATE_REVIEW":
            reviewers = (
                self.session.query(User)
                .filter(
                    User.role_id == "STATE_ADMIN",
                    User.is_active == True,
                    func.lower(User.state) == func.lower(application.state),
                )
                .all()
            )

        elif target_stage == "CENTRAL_REVIEW":
            reviewers = (
                self.session.query(User)
                .filter(
                    User.role_id == "CENTRAL_ADMIN",
                    User.is_active == True,
                )
                .all()
            )

        # Audit unresolved reviewer recipients if no active user is found
        if not reviewers:
            logger.warning(
                "UNRESOLVED_RECIPIENT: No active %s reviewers found for app %s (state=%s, district=%s).",
                target_stage,
                application.application_number,
                application.state,
                application.district,
            )
            audit = AuditLog(
                entity_type="NOTIFICATION",
                entity_id=application.application_id,
                action="UNRESOLVED_RECIPIENT",
                performed_by="SYSTEM",
                previous_state={
                    "target_stage": target_stage,
                    "state": application.state,
                    "district": application.district,
                },
                new_state={
                    "status": "UNRESOLVED_RECIPIENT",
                    "reason": f"No active reviewer registered for {target_stage} jurisdiction",
                    "application_number": application.application_number,
                },
                ip_address=client_ip,
                created_at=datetime.now(timezone.utc),
            )
            self.session.add(audit)
            self.session.flush()

        return reviewers

    # ============================================================
    # 2. ATOMIC NOTIFICATION & OUTBOX EMISSION HELPERS
    # ============================================================

    def _create_in_app_notification(
        self,
        idempotency_key: str,
        title: str,
        message: str,
        event_type: str,
        application_id: Optional[str] = None,
        hospital_id: Optional[str] = None,
        referral_id: Optional[str] = None,
        user_id: Optional[str] = None,
        role_id: Optional[str] = None,
        state: Optional[str] = None,
        district: Optional[str] = None,
        action_url: Optional[str] = None,
        priority: str = "NORMAL",
    ) -> Optional[Notification]:
        """
        Creates an in-app notification row with idempotency protection.
        """
        # Check idempotency
        existing = (
            self.session.query(Notification)
            .filter_by(idempotency_key=idempotency_key)
            .first()
        )
        if existing:
            logger.info("Notification with idempotency key '%s' already exists. Skipping.", idempotency_key)
            return existing

        now = datetime.now(timezone.utc)
        notif = Notification(
            event_type=event_type,
            title=title,
            message=message,
            priority=priority,
            is_read=False,
            created_at=now,
            application_id=application_id,
            hospital_id=hospital_id,
            referral_id=referral_id,
            user_id=user_id,
            role_id=role_id,
            state=state,
            district=district,
            action_url=action_url,
            idempotency_key=idempotency_key,
        )
        self.session.add(notif)
        self.session.flush()
        return notif

    def _enqueue_email(
        self,
        event_type: str,
        recipient_email: str,
        recipient_name: Optional[str],
        subject: str,
        payload: Dict[str, Any],
        idempotency_key: str,
    ) -> Optional[RegistrationEmailOutbox]:
        """
        Enqueues an email into the transactional outbox with stable deterministic outbox_id.
        """
        if not recipient_email or "@" not in recipient_email:
            logger.warning("Skipping email outbox enqueue: invalid recipient '%s'", recipient_email)
            return None

        # Stable deterministic outbox ID (max 64 chars)
        outbox_id = f"OUT_{hashlib.sha256(idempotency_key.encode('utf-8')).hexdigest()[:48]}"

        existing = (
            self.session.query(RegistrationEmailOutbox)
            .filter_by(outbox_id=outbox_id)
            .first()
        )
        if existing:
            logger.info("Outbox email '%s' already exists. Skipping.", outbox_id)
            return existing

        now = datetime.now(timezone.utc)
        outbox_record = RegistrationEmailOutbox(
            outbox_id=outbox_id,
            event_type=event_type,
            recipient_email=recipient_email.strip().lower(),
            recipient_name=recipient_name,
            subject=subject,
            payload=json.dumps(payload),
            status="PENDING",
            retry_count=0,
            max_retries=3,
            next_retry_at=now,
            created_at=now,
        )
        self.session.add(outbox_record)
        self.session.flush()
        return outbox_record

    # ============================================================
    # 3. LIFECYCLE EVENT DISPATCHERS
    # ============================================================

    def notify_application_submitted(
        self,
        application: RegistrationApplication,
        tracking_token: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered when an applicant submits their DRAFT application:
        1. Emits confirmation notification and email to Applicant containing Official Application Number
           and Secret Tracking Token with direct portal tracking instructions.
        2. Dispatches new application alert and email to initial Reviewers (District / State / Central).
        """
        base_url = get_portal_base_url()
        if tracking_token:
            tracking_url = f"{base_url}/application/track?app={application.application_number}&token={tracking_token}"
        else:
            tracking_url = f"{base_url}/application/track?app={application.application_number}"

        applicant_status_url = f"{base_url}/application/status?id={application.application_id}"
        reviewer_dossier_url = f"{base_url}/reviewer/applications/{application.application_id}"
        stage = application.current_stage or "DISTRICT_REVIEW"

        stage_display_names = {
            "DISTRICT_REVIEW": "District Verification",
            "STATE_REVIEW": "State Verification",
            "CENTRAL_REVIEW": "Central Verification",
        }
        stage_display = stage_display_names.get(stage, stage)

        # A. Applicant In-App & Email
        app_idem = f"APP_SUBMIT:{application.application_id}:{stage}:APPLICANT"
        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"Application Submitted: {application.application_number}",
            message=(
                f"Your registration application for {application.applicant_name} ({application.applicant_type}) "
                f"has been successfully submitted and forwarded to {stage} for document verification."
            ),
            event_type="APPLICATION_SUBMITTED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="NORMAL",
        )

        tracking_token_display = tracking_token or "Issued upon submission (see portal session)"

        body_text = (
            f"Dear {application.applicant_name},\n\n"
            f"Thank you for submitting your healthcare registration application on ArogyaSetu Grid — Unified Critical Care & Hospital Command Network.\n\n"
            f"Your application has been received and assigned for administrative review.\n\n"
            f"OFFICIAL REGISTRATION DETAILS:\n"
            f"--------------------------------------------------\n"
            f"Applicant / Organization: {application.applicant_name}\n"
            f"Application Number:       {application.application_number}\n"
            f"Applicant Type:           {application.applicant_type}\n"
            f"State / District:         {application.state}" + (f" / {application.district}" if application.district else "") + "\n"
            f"Current Review Stage:     {stage_display} ({stage})\n"
            f"Application Status:       SUBMITTED\n"
            f"--------------------------------------------------\n\n"
            f"CONFIDENTIAL TRACKING CREDENTIALS:\n"
            f"--------------------------------------------------\n"
            f"Official Application Number: {application.application_number}\n"
            f"Secret Tracking Token:       {tracking_token_display}\n"
            f"--------------------------------------------------\n"
            f"SECURITY NOTICE: Your Secret Tracking Token is required to track application\n"
            f"progress, view reviewer remarks, and submit corrections if requested.\n"
            f"Please keep this token secure and confidential.\n\n"
            f"DIRECT PORTAL TRACKING INSTRUCTIONS:\n"
            f"1. Direct Link: Open the following URL to verify your application milestones:\n"
            f"   {tracking_url}\n\n"
            f"2. Manual Access: Visit {base_url}/application/track (or /track) and enter:\n"
            f"   - Application Number: {application.application_number}\n"
            f"   - Secret Tracking Token: {tracking_token_display}\n\n"
            f"WHAT TO EXPECT NEXT:\n"
            f"Designated healthcare regulatory officers at the {stage_display} level will verify\n"
            f"your uploaded compliance documents and facility credentials. You will receive an\n"
            f"automated email notification when your application status changes or if additional\n"
            f"documents are required.\n\n"
            f"Regards,\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )

        body_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Application Submitted - {application.application_number}</title>
</head>
<body style="margin: 0; padding: 24px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc;">
  <div style="max-width: 600px; margin: 0 auto; background-color: #1e293b; border-radius: 12px; border: 1px solid #334155; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.3);">
    <div style="background: linear-gradient(135deg, #0f172a 0%, #0b132b 100%); padding: 28px 24px; text-align: center; border-bottom: 1px solid #1e293b;">
      <h1 style="margin: 0 0 6px 0; font-size: 20px; color: #14b8a6; font-weight: 700; letter-spacing: -0.025em;">ArogyaSetu Grid</h1>
      <p style="margin: 0; font-size: 13px; color: #94a3b8;">Unified Critical Care & Hospital Command Network</p>
    </div>
    <div style="padding: 28px 24px;">
      <p style="margin-top: 0; font-size: 15px; color: #f8fafc;">Dear <strong>{application.applicant_name}</strong>,</p>
      <p style="font-size: 13px; color: #cbd5e1; line-height: 1.6;">
        Your healthcare registration dossier has been submitted successfully and forwarded to <strong>{stage_display}</strong> for document verification.
      </p>

      <div style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 18px 20px; margin: 20px 0;">
        <table style="width: 100%; border-collapse: collapse; font-size: 13px;">
          <tr>
            <td style="padding: 6px 0; color: #94a3b8; font-weight: 500;">Application Number</td>
            <td style="padding: 6px 0; color: #60a5fa; font-weight: 700; text-align: right; font-family: monospace;">{application.application_number}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #94a3b8; font-weight: 500;">Facility / Organization</td>
            <td style="padding: 6px 0; color: #f8fafc; font-weight: 600; text-align: right;">{application.applicant_name}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #94a3b8; font-weight: 500;">Applicant Type</td>
            <td style="padding: 6px 0; color: #f8fafc; font-weight: 600; text-align: right;">{application.applicant_type}</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #94a3b8; font-weight: 500;">Current Review Stage</td>
            <td style="padding: 6px 0; color: #34d399; font-weight: 600; text-align: right;">{stage_display} ({stage})</td>
          </tr>
          <tr>
            <td style="padding: 6px 0; color: #94a3b8; font-weight: 500;">Status</td>
            <td style="padding: 6px 0; color: #fbbf24; font-weight: 600; text-align: right;">SUBMITTED</td>
          </tr>
        </table>
      </div>

      <div style="background-color: #020617; border: 1px solid #2563eb; border-radius: 8px; padding: 16px; margin: 20px 0; text-align: center;">
        <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: #93c5fd; font-weight: 600; margin-bottom: 4px;">Secret Tracking Token</div>
        <div style="font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 15px; font-weight: 700; color: #38bdf8; word-break: break-all;">{tracking_token_display}</div>
        <p style="margin: 8px 0 0 0; font-size: 11px; color: #94a3b8;">Keep this token secure. Required for status inquiries and resubmissions.</p>
      </div>

      <div style="text-align: center; margin: 24px 0;">
        <a href="{tracking_url}" style="display: inline-block; background-color: #2563eb; color: #ffffff !important; font-weight: 600; font-size: 13px; text-decoration: none; padding: 12px 28px; border-radius: 6px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2);">Track Application Status &rarr;</a>
      </div>

      <div style="font-size: 12px; color: #94a3b8; line-height: 1.6; border-top: 1px solid #334155; padding-top: 16px;">
        <strong style="color: #cbd5e1;">Portal Tracking Instructions (/track):</strong><br>
        You can track the progress of your application at any time by visiting <a href="{base_url}/application/track" style="color: #60a5fa; text-decoration: underline;">{base_url}/application/track</a> (or <code>/track</code>) and entering your Official Application Number (<strong>{application.application_number}</strong>) and Secret Tracking Token.
      </div>
    </div>
    <div style="padding: 16px 24px; background-color: #0b132b; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #1e293b;">
      ArogyaSetu Grid &bull; National Critical Care & Hospital Command Network &bull; Support: pawanbussiness108@gmail.com<br>
      Automated confirmation &bull; Please do not reply directly to this email.
    </div>
  </div>
</body>
</html>"""

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "applicant_type": application.applicant_type,
            "status": "SUBMITTED",
            "current_stage": stage,
            "current_stage_display": stage_display,
            "tracking_url": tracking_url,
            "tracking_token": tracking_token,
            "body_text": body_text,
            "body_html": body_html,
        }

        self._enqueue_email(
            event_type="APPLICATION_SUBMITTED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Application Submitted: {application.application_number} ({application.applicant_name})",
            payload=email_payload,
            idempotency_key=app_idem,
        )

        # B. Hierarchical Reviewer In-App & Email
        target_role = {
            "DISTRICT_REVIEW": "DISTRICT_ADMIN",
            "STATE_REVIEW": "STATE_ADMIN",
            "CENTRAL_REVIEW": "CENTRAL_ADMIN",
        }.get(stage, "DISTRICT_ADMIN")

        rev_idem = f"REV_SUBMIT:{application.application_id}:{stage}:ROLE"
        self._create_in_app_notification(
            idempotency_key=rev_idem,
            title=f"New {application.applicant_type} Application: {application.application_number}",
            message=(
                f"New {application.applicant_type} registration submitted by {application.applicant_name} "
                f"in {application.district or application.state}, {application.state}. Document verification required."
            ),
            event_type="NEW_REGISTRATION_APPLICATION",
            application_id=application.application_id,
            role_id=target_role,
            state=application.state,
            district=application.district if target_role == "DISTRICT_ADMIN" else None,
            action_url=f"/reviewer/applications/{application.application_id}",
            priority="HIGH",
        )

        reviewers = self.resolve_reviewers(stage, application, client_ip)
        for rev in reviewers:
            if rev.email:
                rev_email_idem = f"REV_EMAIL:{application.application_id}:{stage}:{rev.user_id}"
                rev_payload = {
                    "application_number": application.application_number,
                    "applicant_name": application.applicant_name,
                    "applicant_type": application.applicant_type,
                    "stage": stage,
                    "reviewer_name": rev.name,
                    "dossier_url": reviewer_dossier_url,
                    "body_text": (
                        f"Dear {rev.name},\n\n"
                        f"A new healthcare registration application requires your review.\n\n"
                        f"Application Number: {application.application_number}\n"
                        f"Facility Name: {application.applicant_name}\n"
                        f"Applicant Type: {application.applicant_type}\n"
                        f"Jurisdiction: {application.district or 'Statewide'}, {application.state}\n"
                        f"Current Stage: {stage}\n\n"
                        f"Please access the Reviewer Portal to inspect credentials and verify mandatory documents:\n"
                        f"{reviewer_dossier_url}\n\n"
                        f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                        f"Support: pawanbussiness108@gmail.com"
                    ),
                }
                self._enqueue_email(
                    event_type="REVIEWER_REVIEW_REQUIRED",
                    recipient_email=rev.email,
                    recipient_name=rev.name,
                    subject=f"Review Required: {application.application_number} ({application.applicant_name})",
                    payload=rev_payload,
                    idempotency_key=rev_email_idem,
                )

    def notify_correction_requested(
        self,
        application: RegistrationApplication,
        correction_notes: str,
        reviewer_user: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered when a reviewer requests corrections from the applicant:
        - In-app notification to applicant.
        - Outbox email to applicant detailing deficiencies and resubmission tracking link.
        """
        base_url = get_portal_base_url()
        tracking_url = f"{base_url}/application/track?number={application.application_number}"
        version = application.resubmission_version or 0
        app_idem = f"APP_CORRECTION:{application.application_id}:{version}"

        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"Action Required: Corrections Requested ({application.application_number})",
            message=(
                f"The reviewing authority has requested document or detail corrections: "
                f"{correction_notes[:200]}"
            ),
            event_type="CORRECTION_REQUIRED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="HIGH",
        )

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "status": "CORRECTION_REQUIRED",
            "correction_notes": correction_notes,
            "tracking_url": tracking_url,
            "body_text": (
                f"Dear {application.applicant_name},\n\n"
                f"The reviewing authority has reviewed your registration application ({application.application_number}) "
                f"and requires additional information or document corrections before approval can proceed.\n\n"
                f"Reviewer Correction Notes:\n"
                f"----------------------------------------\n"
                f"{correction_notes}\n"
                f"----------------------------------------\n\n"
                f"Instructions:\n"
                f"Please visit your Applicant Portal, upload the requested documents or update your details, "
                f"and resubmit your dossier.\n\n"
                f"Tracking & Resubmission Link:\n"
                f"{tracking_url}\n\n"
                f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                f"Support: pawanbussiness108@gmail.com"
            ),
        }
        self._enqueue_email(
            event_type="CORRECTION_REQUIRED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Action Required: Correction Requested for Application {application.application_number}",
            payload=email_payload,
            idempotency_key=app_idem,
        )

    def notify_application_resubmitted(
        self,
        application: RegistrationApplication,
        applicant_notes: Optional[str] = None,
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered when an applicant resubmits their corrected application:
        1. Emits confirmation in-app and email to Applicant.
        2. Alerts responsible Reviewers of that stage that the corrected dossier is ready.
        """
        base_url = get_portal_base_url()
        tracking_url = f"{base_url}/application/track?number={application.application_number}"
        reviewer_dossier_url = f"{base_url}/reviewer/applications/{application.application_id}"
        version = application.resubmission_version or 1
        stage = application.current_stage or "DISTRICT_REVIEW"

        # A. Applicant confirmation
        app_idem = f"APP_RESUBMIT:{application.application_id}:{version}"
        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"Application Resubmitted: {application.application_number}",
            message=(
                f"Your corrected application has been received and returned to {stage} for evaluation."
            ),
            event_type="APPLICATION_RESUBMITTED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="NORMAL",
        )

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "status": "SUBMITTED",
            "current_stage": stage,
            "resubmission_version": version,
            "tracking_url": tracking_url,
            "body_text": (
                f"Dear {application.applicant_name},\n\n"
                f"We have received your resubmitted registration application (Revision {version}).\n\n"
                f"Application Number: {application.application_number}\n"
                f"Current Status: SUBMITTED (Assigned to {stage})\n\n"
                f"You can monitor review status at:\n"
                f"{tracking_url}\n\n"
                f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                f"Support: pawanbussiness108@gmail.com"
            ),
        }
        self._enqueue_email(
            event_type="APPLICATION_RESUBMITTED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Resubmission Received: {application.application_number} (Revision {version})",
            payload=email_payload,
            idempotency_key=app_idem,
        )

        # B. Reviewer Alert
        target_role = {
            "DISTRICT_REVIEW": "DISTRICT_ADMIN",
            "STATE_REVIEW": "STATE_ADMIN",
            "CENTRAL_REVIEW": "CENTRAL_ADMIN",
        }.get(stage, "DISTRICT_ADMIN")

        rev_idem = f"REV_RESUBMIT:{application.application_id}:{version}"
        self._create_in_app_notification(
            idempotency_key=rev_idem,
            title=f"Corrected Dossier Resubmitted: {application.application_number}",
            message=(
                f"Applicant {application.applicant_name} has resubmitted corrected documents for "
                f"application {application.application_number} (Revision {version}). Ready for review."
            ),
            event_type="CORRECTION_RESUBMITTED",
            application_id=application.application_id,
            role_id=target_role,
            state=application.state,
            district=application.district if target_role == "DISTRICT_ADMIN" else None,
            action_url=f"/reviewer/applications/{application.application_id}",
            priority="HIGH",
        )

        reviewers = self.resolve_reviewers(stage, application, client_ip)
        for rev in reviewers:
            if rev.email:
                rev_email_idem = f"REV_RESUBMIT_EMAIL:{application.application_id}:{version}:{rev.user_id}"
                rev_payload = {
                    "application_number": application.application_number,
                    "applicant_name": application.applicant_name,
                    "resubmission_version": version,
                    "applicant_notes": applicant_notes or "Dossier updated per requested corrections.",
                    "dossier_url": reviewer_dossier_url,
                    "body_text": (
                        f"Dear {rev.name},\n\n"
                        f"Applicant '{application.applicant_name}' has resubmitted their registration dossier "
                        f"following your correction request.\n\n"
                        f"Application Number: {application.application_number}\n"
                        f"Revision: {version}\n"
                        f"Applicant Notes: {applicant_notes or 'Updated per reviewer instructions.'}\n\n"
                        f"Please re-inspect the updated documents in the Reviewer Portal:\n"
                        f"{reviewer_dossier_url}\n\n"
                        f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                        f"Support: pawanbussiness108@gmail.com"
                    ),
                }
                self._enqueue_email(
                    event_type="CORRECTION_RESUBMITTED",
                    recipient_email=rev.email,
                    recipient_name=rev.name,
                    subject=f"Resubmission Alert: {application.application_number} ({application.applicant_name})",
                    payload=rev_payload,
                    idempotency_key=rev_email_idem,
                )

    def notify_stage_forwarded(
        self,
        application: RegistrationApplication,
        previous_stage: str,
        new_stage: str,
        reviewer_user: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered on intermediate approval (District -> State, State -> Central):
        1. Emits status update in-app and email to Applicant.
        2. Dispatches review alert and email to next-tier Reviewers.
        """
        base_url = get_portal_base_url()
        tracking_url = f"{base_url}/application/track?number={application.application_number}"
        reviewer_dossier_url = f"{base_url}/reviewer/applications/{application.application_id}"

        tier_name = "District" if previous_stage == "DISTRICT_REVIEW" else "State"
        next_tier_name = "State" if new_stage == "STATE_REVIEW" else "Central"

        # A. Applicant Status Notification
        app_idem = f"APP_FORWARD:{application.application_id}:{previous_stage}:{new_stage}"
        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"{tier_name} Review Approved: {application.application_number}",
            message=(
                f"Your registration application has cleared {tier_name} review and has been "
                f"forwarded to {next_tier_name} Government oversight for next-level verification."
            ),
            event_type="APPLICATION_FORWARDED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="NORMAL",
        )

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "status": "UNDER_REVIEW",
            "cleared_stage": previous_stage,
            "next_stage": new_stage,
            "tracking_url": tracking_url,
            "body_text": (
                f"Dear {application.applicant_name},\n\n"
                f"Your registration application ({application.application_number}) has successfully "
                f"cleared {tier_name} level verification.\n\n"
                f"The application has now advanced to {next_tier_name} Review ({new_stage}).\n\n"
                f"You can track the ongoing verification status at:\n"
                f"{tracking_url}\n\n"
                f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                f"Support: pawanbussiness108@gmail.com"
            ),
        }
        self._enqueue_email(
            event_type="APPLICATION_FORWARDED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Application Update: {tier_name} Review Cleared for {application.application_number}",
            payload=email_payload,
            idempotency_key=app_idem,
        )

        # B. Next Tier Reviewer In-App & Email
        target_role = "STATE_ADMIN" if new_stage == "STATE_REVIEW" else "CENTRAL_ADMIN"
        rev_idem = f"REV_FORWARD:{application.application_id}:{new_stage}"

        self._create_in_app_notification(
            idempotency_key=rev_idem,
            title=f"{next_tier_name} Review Required: {application.application_number}",
            message=(
                f"Application {application.application_number} ({application.applicant_name}) was approved "
                f"by {tier_name} administration and is awaiting your verification."
            ),
            event_type="NEW_REGISTRATION_APPLICATION",
            application_id=application.application_id,
            role_id=target_role,
            state=application.state,
            district=None,
            action_url=f"/reviewer/applications/{application.application_id}",
            priority="HIGH",
        )

        reviewers = self.resolve_reviewers(new_stage, application, client_ip)
        for rev in reviewers:
            if rev.email:
                rev_email_idem = f"REV_FORWARD_EMAIL:{application.application_id}:{new_stage}:{rev.user_id}"
                rev_payload = {
                    "application_number": application.application_number,
                    "applicant_name": application.applicant_name,
                    "previous_tier": tier_name,
                    "next_stage": new_stage,
                    "dossier_url": reviewer_dossier_url,
                    "body_text": (
                        f"Dear {rev.name},\n\n"
                        f"An application has cleared {tier_name} review and has been escalated to {new_stage}.\n\n"
                        f"Application Number: {application.application_number}\n"
                        f"Facility Name: {application.applicant_name}\n"
                        f"Applicant Type: {application.applicant_type}\n"
                        f"Jurisdiction: {application.district or 'Statewide'}, {application.state}\n\n"
                        f"Please access the Reviewer Portal to perform your review:\n"
                        f"{reviewer_dossier_url}\n\n"
                        f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                        f"Support: pawanbussiness108@gmail.com"
                    ),
                }
                self._enqueue_email(
                    event_type="REVIEWER_REVIEW_REQUIRED",
                    recipient_email=rev.email,
                    recipient_name=rev.name,
                    subject=f"{next_tier_name} Review Required: {application.application_number} ({application.applicant_name})",
                    payload=rev_payload,
                    idempotency_key=rev_email_idem,
                )

    def notify_final_approval(
        self,
        application: RegistrationApplication,
        reviewer_user: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered on final Central Government approval:
        - In-app notification to applicant.
        - Approval decision email to applicant (strictly without claiming operational status
          before account activation is completed).
        - (Note: The separate ACCOUNT_ACTIVATION email is enqueued by AccountProvisioningService).
        """
        base_url = get_portal_base_url()
        tracking_url = f"{base_url}/application/track?number={application.application_number}"
        app_idem = f"APP_APPROVED:{application.application_id}"

        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"Registration Approved: {application.application_number}",
            message=(
                f"Congratulations! Your registration application for {application.applicant_name} "
                f"has received final Central Government approval."
            ),
            event_type="APPLICATION_APPROVED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="HIGH",
        )

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "status": "APPROVED",
            "tracking_url": tracking_url,
            "body_text": (
                f"Dear {application.applicant_name},\n\n"
                f"We are pleased to inform you that your healthcare registration application "
                f"({application.application_number}) has received final Central Government approval.\n\n"
                f"Status: APPROVED\n\n"
                f"Next Steps:\n"
                f"An official operational account is being provisioned. You will receive a separate "
                f"account activation email containing a secure link to activate your administrator credentials.\n"
                f"Please note that facility operations will commence once your account is fully activated.\n\n"
                f"You can verify your final approval record at:\n"
                f"{tracking_url}\n\n"
                f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                f"Support: pawanbussiness108@gmail.com"
            ),
        }
        self._enqueue_email(
            event_type="APPLICATION_APPROVED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Official Approval Decision: Application {application.application_number} Approved",
            payload=email_payload,
            idempotency_key=app_idem,
        )

    def notify_application_rejected(
        self,
        application: RegistrationApplication,
        rejection_reason: str,
        reviewer_user: Dict[str, Any],
        client_ip: Optional[str] = None,
    ) -> None:
        """
        Triggered when an application is rejected:
        - In-app notification to applicant.
        - Formal rejection email to applicant with recorded official reason and tracking link.
        """
        base_url = get_portal_base_url()
        tracking_url = f"{base_url}/application/track?number={application.application_number}"
        app_idem = f"APP_REJECTED:{application.application_id}"

        self._create_in_app_notification(
            idempotency_key=app_idem,
            title=f"Application Rejected: {application.application_number}",
            message=f"Your registration application has been rejected. Reason: {rejection_reason}",
            event_type="APPLICATION_REJECTED",
            application_id=application.application_id,
            action_url=f"/application/status?id={application.application_id}",
            priority="HIGH",
        )

        email_payload = {
            "application_number": application.application_number,
            "applicant_name": application.applicant_name,
            "status": "REJECTED",
            "rejection_reason": rejection_reason,
            "tracking_url": tracking_url,
            "body_text": (
                f"Dear {application.applicant_name},\n\n"
                f"Your healthcare registration application ({application.application_number}) "
                f"has been evaluated and rejected by the competent reviewing authority.\n\n"
                f"Official Reason for Rejection:\n"
                f"----------------------------------------\n"
                f"{rejection_reason}\n"
                f"----------------------------------------\n\n"
                f"You can view the official decision record at:\n"
                f"{tracking_url}\n\n"
                f"If you believe this decision was reached in error, you may submit a fresh registration "
                f"dossier addressing the deficiencies noted above.\n\n"
                f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
                f"Support: pawanbussiness108@gmail.com"
            ),
        }
        self._enqueue_email(
            event_type="APPLICATION_REJECTED",
            recipient_email=application.applicant_email,
            recipient_name=application.applicant_name,
            subject=f"Official Decision: Registration Application {application.application_number} Rejected",
            payload=email_payload,
            idempotency_key=app_idem,
        )

    # ============================================================
    # 4. OPERATIONAL RECIPIENT RESOLUTION & HELPERS (PHASE 4D-3)
    # ============================================================

    @staticmethod
    def _mask_patient_id(patient_id: Optional[str]) -> str:
        """Mask patient identifier to avoid exposing PII in alerts."""
        if not patient_id:
            return "PAT-ANON"
        pid = str(patient_id).strip()
        if len(pid) >= 4:
            return f"PAT-***{pid[-4:]}"
        return f"PAT-***{pid}"

    def resolve_hospital_recipients(self, hospital_id: str) -> List[User]:
        """Resolve active authorized users belonging to target hospital."""
        if not hospital_id:
            return []
        return (
            self.session.query(User)
            .filter(
                User.hospital_id == hospital_id,
                User.is_active == True,
            )
            .all()
        )

    def resolve_district_authorities(self, state: Optional[str], district: Optional[str]) -> List[User]:
        """Resolve active district administrators for jurisdiction."""
        if not state or not district:
            return []
        return (
            self.session.query(User)
            .filter(
                User.role_id == "DISTRICT_ADMIN",
                User.is_active == True,
                func.lower(User.state) == func.lower(state),
                func.lower(User.district) == func.lower(district),
            )
            .all()
        )

    def resolve_state_authorities(self, state: Optional[str]) -> List[User]:
        """Resolve active state administrators for jurisdiction."""
        if not state:
            return []
        return (
            self.session.query(User)
            .filter(
                User.role_id == "STATE_ADMIN",
                User.is_active == True,
                func.lower(User.state) == func.lower(state),
            )
            .all()
        )

    def resolve_central_authorities(self) -> List[User]:
        """Resolve active central administrators."""
        return (
            self.session.query(User)
            .filter(
                User.role_id == "CENTRAL_ADMIN",
                User.is_active == True,
            )
            .all()
        )

    def _enqueue_hospital_emails(
        self,
        hospital_id: str,
        event_type: str,
        subject: str,
        body_text: str,
        base_idempotency_key: str,
    ):
        """Enqueue outbox emails to all registered active hospital users with valid email."""
        users = self.resolve_hospital_recipients(hospital_id)
        for u in users:
            if u.email and "@" in u.email:
                user_idem = f"{base_idempotency_key}_USR_{u.user_id}"
                self._enqueue_email(
                    event_type=event_type,
                    recipient_email=u.email,
                    recipient_name=u.name or "Hospital Administrator",
                    subject=subject,
                    payload={"body_text": body_text, "hospital_id": hospital_id},
                    idempotency_key=user_idem,
                )

    # ============================================================
    # 5. REFERRAL OPERATIONAL NOTIFICATIONS (PHASE 4D-3)
    # ============================================================

    def notify_referral_created(self, referral, from_hospital, to_hospital):
        """
        Notify receiving hospital and district authority upon new incoming referral.
        """
        ref_id = referral.referral_id
        to_hid = referral.to_hospital_id
        from_name = from_hospital.name if from_hospital else referral.from_hospital_id
        to_name = to_hospital.name if to_hospital else to_hid
        masked_pid = self._mask_patient_id(referral.patient_id)
        priority = referral.priority or "Normal"
        bed_type = referral.bed_type or "GENERAL"

        # 1. In-app for receiving hospital
        notif_idem = f"OP_REF_NEW_{ref_id}"
        self._create_in_app_notification(
            idempotency_key=notif_idem,
            title=f"New Incoming Referral: {ref_id}",
            message=f"New {priority} referral received for {bed_type} bed hold. Referring hospital: {from_name}. Patient: {masked_pid}.",
            event_type="NEW_REFERRAL",
            state=to_hospital.state if to_hospital else None,
            district=to_hospital.district if to_hospital else None,
            action_url=f"/hospitals/{to_hid}?tab=referrals",
            priority="CRITICAL" if priority.upper() == "CRITICAL" else "HIGH",
        )
        # Ensure hospital_id is set
        existing = self.session.query(Notification).filter_by(idempotency_key=notif_idem).first()
        if existing:
            existing.hospital_id = to_hid
            existing.referral_id = ref_id

        # 2. In-app for district authority
        if to_hospital and to_hospital.state and to_hospital.district:
            dist_idem = f"OP_REF_NEW_DIST_{ref_id}"
            self._create_in_app_notification(
                idempotency_key=dist_idem,
                title=f"District Referral Alert: {to_name}",
                message=f"Incoming {priority} referral ({ref_id}) routed to {to_name} in {to_hospital.district}.",
                event_type="NEW_REFERRAL",
                role_id="DISTRICT_ADMIN",
                state=to_hospital.state,
                district=to_hospital.district,
                action_url="/district/referrals",
                priority="HIGH" if priority.upper() == "CRITICAL" else "NORMAL",
            )
            dist_notif = self.session.query(Notification).filter_by(idempotency_key=dist_idem).first()
            if dist_notif:
                dist_notif.referral_id = ref_id

        # 3. In-app for state authority (destination state for critical or inter-state transfers)
        is_interstate = bool(
            from_hospital and to_hospital and from_hospital.state and to_hospital.state
            and from_hospital.state.strip().lower() != to_hospital.state.strip().lower()
        )
        if to_hospital and to_hospital.state and (is_interstate or priority.upper() == "CRITICAL"):
            state_idem = f"OP_REF_NEW_STATE_{ref_id}"
            self._create_in_app_notification(
                idempotency_key=state_idem,
                title=f"State Referral Alert: {to_name}",
                message=f"Incoming {'inter-state ' if is_interstate else ''}{priority} referral ({ref_id}) routed to {to_name} in {to_hospital.district}.",
                event_type="NEW_REFERRAL",
                role_id="STATE_ADMIN",
                state=to_hospital.state,
                action_url="/state/referrals",
                priority="CRITICAL" if priority.upper() == "CRITICAL" else "HIGH",
            )
            state_notif = self.session.query(Notification).filter_by(idempotency_key=state_idem).first()
            if state_notif:
                state_notif.referral_id = ref_id

        # 4. In-app for central authority (only for cross-border inter-state transfers)
        if is_interstate:
            central_idem = f"OP_REF_NEW_CENTRAL_{ref_id}"
            self._create_in_app_notification(
                idempotency_key=central_idem,
                title=f"National Inter-State Referral: {ref_id}",
                message=f"Cross-border referral initiated: {from_name} ({from_hospital.state}) -> {to_name} ({to_hospital.state}). Patient {masked_pid}.",
                event_type="NEW_REFERRAL",
                role_id="CENTRAL_ADMIN",
                action_url="/central/referrals",
                priority="HIGH",
            )
            central_notif = self.session.query(Notification).filter_by(idempotency_key=central_idem).first()
            if central_notif:
                central_notif.referral_id = ref_id

        # 5. Email to receiving hospital contacts
        email_body = (
            f"Notification of Incoming Patient Referral\n\n"
            f"Referral ID: {ref_id}\n"
            f"Priority: {priority}\n"
            f"Required Bed Type: {bed_type}\n"
            f"Referring Facility: {from_name}\n"
            f"Destination Facility: {to_name}\n"
            f"Patient Identifier: {masked_pid}\n\n"
            f"Please review and accept or redirect this referral in your clinical dashboard:\n"
            f"{get_portal_base_url()}/hospitals/{to_hid}?tab=referrals\n\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )
        self._enqueue_hospital_emails(
            hospital_id=to_hid,
            event_type="NEW_REFERRAL",
            subject=f"Urgent Referral Received: {ref_id} ({priority})",
            body_text=email_body,
            base_idempotency_key=notif_idem,
        )

    def notify_referral_accepted(self, referral, from_hospital, to_hospital, bed):
        """
        Notify referring and receiving hospitals upon referral acceptance.
        """
        ref_id = referral.referral_id
        from_hid = referral.from_hospital_id
        to_hid = referral.to_hospital_id
        to_name = to_hospital.name if to_hospital else to_hid
        masked_pid = self._mask_patient_id(referral.patient_id)
        bed_num = bed.bed_number if bed else "Bed"
        bed_type = bed.bed_type if bed else referral.bed_type

        # 1. In-app for referring hospital
        from_idem = f"OP_REF_ACC_FROM_{ref_id}"
        self._create_in_app_notification(
            idempotency_key=from_idem,
            title=f"Referral Accepted: {ref_id}",
            message=f"{to_name} accepted your referral for patient {masked_pid}. Bed {bed_num} ({bed_type}) reserved.",
            event_type="REFERRAL_ACCEPTED",
            action_url=f"/hospitals/{from_hid}?tab=referrals",
            priority="HIGH",
        )
        existing_from = self.session.query(Notification).filter_by(idempotency_key=from_idem).first()
        if existing_from:
            existing_from.hospital_id = from_hid
            existing_from.referral_id = ref_id

        # 2. In-app for receiving hospital
        to_idem = f"OP_REF_ACC_TO_{ref_id}"
        self._create_in_app_notification(
            idempotency_key=to_idem,
            title=f"Referral Confirmed: {ref_id}",
            message=f"Referral {ref_id} accepted. Bed {bed_num} ({bed_type}) held for patient arrival.",
            event_type="REFERRAL_ACCEPTED",
            action_url=f"/hospitals/{to_hid}?tab=referrals",
            priority="NORMAL",
        )
        existing_to = self.session.query(Notification).filter_by(idempotency_key=to_idem).first()
        if existing_to:
            existing_to.hospital_id = to_hid
            existing_to.referral_id = ref_id

        # 3. Email to referring hospital
        email_body = (
            f"Referral Acceptance Confirmation\n\n"
            f"Referral ID: {ref_id}\n"
            f"Destination Hospital: {to_name}\n"
            f"Allocated Bed: {bed_num} ({bed_type})\n"
            f"Patient Identifier: {masked_pid}\n\n"
            f"Please coordinate ambulance transport. You can track progress at:\n"
            f"{get_portal_base_url()}/hospitals/{from_hid}?tab=referrals\n\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )
        self._enqueue_hospital_emails(
            hospital_id=from_hid,
            event_type="REFERRAL_ACCEPTED",
            subject=f"Referral Accepted by {to_name}: {ref_id}",
            body_text=email_body,
            base_idempotency_key=from_idem,
        )

    def notify_referral_rejected(self, referral, from_hospital, to_hospital, notes: Optional[str] = None):
        """
        Notify referring hospital upon referral rejection with sanitized reason.
        """
        ref_id = referral.referral_id
        from_hid = referral.from_hospital_id
        to_name = to_hospital.name if to_hospital else referral.to_hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id)
        safe_reason = notes[:200] if notes else "Capacity unavailable at destination hospital"

        # 1. In-app for referring hospital
        rej_idem = f"OP_REF_REJ_{ref_id}"
        self._create_in_app_notification(
            idempotency_key=rej_idem,
            title=f"Referral Rejected: {ref_id}",
            message=f"{to_name} declined referral for patient {masked_pid}. Reason: {safe_reason}.",
            event_type="REFERRAL_REJECTED",
            action_url=f"/hospitals/{from_hid}?tab=referrals",
            priority="HIGH",
        )
        existing = self.session.query(Notification).filter_by(idempotency_key=rej_idem).first()
        if existing:
            existing.hospital_id = from_hid
            existing.referral_id = ref_id

        # 2. Email to referring hospital
        email_body = (
            f"Referral Rejection Notice\n\n"
            f"Referral ID: {ref_id}\n"
            f"Declined by: {to_name}\n"
            f"Patient Identifier: {masked_pid}\n"
            f"Reason/Notes: {safe_reason}\n\n"
            f"Please request recommendations for alternative facilities in your portal:\n"
            f"{get_portal_base_url()}/hospitals/{from_hid}?tab=referrals\n\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )
        self._enqueue_hospital_emails(
            hospital_id=from_hid,
            event_type="REFERRAL_REJECTED",
            subject=f"Referral Declined: {ref_id}",
            body_text=email_body,
            base_idempotency_key=rej_idem,
        )

    # ============================================================
    # 6. BED RESERVATION OPERATIONAL NOTIFICATIONS (PHASE 4D-3)
    # ============================================================

    def notify_bed_reserved(self, reservation, bed, hospital, referral=None):
        """Notify hospital on direct or referral bed reservation."""
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")
        expires_str = reservation.expires_at.strftime("%H:%M UTC") if reservation.expires_at else "2 hours"

        res_idem = f"OP_BED_RES_{res_id}"
        self._create_in_app_notification(
            idempotency_key=res_idem,
            title=f"Bed Hold Reserved: {bed.bed_number}",
            message=f"{bed.bed_type} bed {bed.bed_number} reserved for patient {masked_pid}. Expiry hold: {expires_str}.",
            event_type="BED_RESERVED",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="NORMAL",
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=res_idem).first()
        if notif:
            notif.hospital_id = hid
            if referral:
                notif.referral_id = referral.referral_id

    def notify_bed_confirmed(self, reservation, bed, hospital, referral=None):
        """Notify hospital on reservation confirmation (patient arrival)."""
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")

        conf_idem = f"OP_BED_CONFIRM_{res_id}"
        self._create_in_app_notification(
            idempotency_key=conf_idem,
            title=f"Bed Hold Confirmed: {bed.bed_number}",
            message=f"Arrival confirmed for patient {masked_pid}. {bed.bed_type} bed {bed.bed_number} is guaranteed.",
            event_type="RESERVATION_CONFIRMED",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="HIGH",
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=conf_idem).first()
        if notif:
            notif.hospital_id = hid
            if referral:
                notif.referral_id = referral.referral_id

        # If referring hospital exists and is different, notify them
        if referral and referral.from_hospital_id and referral.from_hospital_id != hid:
            from_hid = referral.from_hospital_id
            from_idem = f"OP_BED_CONFIRM_FROM_{res_id}"
            self._create_in_app_notification(
                idempotency_key=from_idem,
                title=f"Patient Arrival Confirmed: {referral.referral_id}",
                message=f"Patient {masked_pid} arrived at destination hospital. Bed {bed.bed_number} confirmed.",
                event_type="PATIENT_ARRIVED",
                action_url=f"/hospitals/{from_hid}?tab=referrals",
                priority="NORMAL",
            )
            from_notif = self.session.query(Notification).filter_by(idempotency_key=from_idem).first()
            if from_notif:
                from_notif.hospital_id = from_hid
                from_notif.referral_id = referral.referral_id

    def notify_bed_occupied(self, reservation, bed, hospital, referral=None):
        """Notify hospital on patient admission and bed occupancy."""
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")

        occ_idem = f"OP_BED_OCCUPY_{res_id}"
        self._create_in_app_notification(
            idempotency_key=occ_idem,
            title=f"Patient Admitted: Bed {bed.bed_number}",
            message=f"Patient {masked_pid} admitted to {bed.bed_type} bed {bed.bed_number}. Active clinical care commenced.",
            event_type="BED_OCCUPIED",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="NORMAL",
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=occ_idem).first()
        if notif:
            notif.hospital_id = hid
            if referral:
                notif.referral_id = referral.referral_id

    def notify_bed_discharged(self, reservation, bed, hospital, referral=None):
        """Notify hospital and referring facility on patient discharge."""
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")

        dis_idem = f"OP_BED_DISCHARGE_{res_id}"
        self._create_in_app_notification(
            idempotency_key=dis_idem,
            title=f"Patient Discharged: Bed {bed.bed_number}",
            message=f"Patient {masked_pid} discharged from {bed.bed_type} bed {bed.bed_number}. Bed restored to available inventory.",
            event_type="PATIENT_DISCHARGED",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="NORMAL",
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=dis_idem).first()
        if notif:
            notif.hospital_id = hid
            if referral:
                notif.referral_id = referral.referral_id

        # Notify referring facility of completed episode of care
        if referral and referral.from_hospital_id and referral.from_hospital_id != hid:
            from_hid = referral.from_hospital_id
            from_idem = f"OP_BED_DISCHARGE_REF_{res_id}"
            self._create_in_app_notification(
                idempotency_key=from_idem,
                title=f"Episode Completed: {referral.referral_id}",
                message=f"Patient {masked_pid} referred to {hospital.name} has completed treatment and was discharged.",
                event_type="REFERRAL_COMPLETED",
                action_url=f"/hospitals/{from_hid}?tab=referrals",
                priority="NORMAL",
            )
            from_notif = self.session.query(Notification).filter_by(idempotency_key=from_idem).first()
            if from_notif:
                from_notif.hospital_id = from_hid
                from_notif.referral_id = referral.referral_id

    def notify_bed_expired(self, reservation, bed, hospital, referral=None):
        """
        Notify hospital and referring stakeholder when an overdue reservation automatically expires.
        Only executed when the expiry transition has succeeded.
        """
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")
        bed_num = bed.bed_number if bed else "Bed"
        bed_type = bed.bed_type if bed else "GENERAL"

        # 1. In-app for receiving hospital
        exp_idem = f"OP_BED_EXPIRED_{res_id}"
        self._create_in_app_notification(
            idempotency_key=exp_idem,
            title=f"Reservation Expired: {bed_num}",
            message=f"Overdue reservation hold {res_id} for {bed_type} bed {bed_num} (Patient {masked_pid}) expired. Bed restored to available inventory.",
            event_type="RESERVATION_EXPIRED",
            hospital_id=hid,
            referral_id=referral.referral_id if referral else None,
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="HIGH",
        )

        # 2. In-app for referring hospital if applicable
        if referral and referral.from_hospital_id and referral.from_hospital_id != hid:
            from_hid = referral.from_hospital_id
            from_idem = f"OP_BED_EXPIRED_FROM_{res_id}"
            self._create_in_app_notification(
                idempotency_key=from_idem,
                title=f"Referral Hold Expired: {referral.referral_id}",
                message=f"Bed reservation hold at {hospital.name} for referral {referral.referral_id} expired prior to confirmation.",
                event_type="RESERVATION_EXPIRED",
                action_url=f"/hospitals/{from_hid}?tab=referrals",
                priority="HIGH",
            )
            from_notif = self.session.query(Notification).filter_by(idempotency_key=from_idem).first()
            if from_notif:
                from_notif.hospital_id = from_hid
                from_notif.referral_id = referral.referral_id

        # 3. Email notification to receiving hospital
        email_body = (
            f"Notice of Expired Bed Reservation\n\n"
            f"Reservation ID: {res_id}\n"
            f"Hospital: {hospital.name}\n"
            f"Bed: {bed_num} ({bed_type})\n"
            f"Patient Identifier: {masked_pid}\n\n"
            f"The reservation window exceeded its time-to-live without patient confirmation. "
            f"The bed capacity has been automatically returned to the active pool.\n\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )
        self._enqueue_hospital_emails(
            hospital_id=hid,
            event_type="RESERVATION_EXPIRED",
            subject=f"Reservation Expired: Bed {bed_num} ({hospital.name})",
            body_text=email_body,
            base_idempotency_key=exp_idem,
        )

    def notify_bed_released(self, reservation, bed, hospital, referral=None):
        """Notify hospital on reservation cancellation / direct release."""
        res_id = reservation.reservation_id
        hid = hospital.hospital_id
        masked_pid = self._mask_patient_id(referral.patient_id if referral else "DIRECT")
        bed_num = bed.bed_number if bed else "Bed"
        bed_type = bed.bed_type if bed else "GENERAL"

        rel_idem = f"OP_BED_RELEASE_{res_id}"
        self._create_in_app_notification(
            idempotency_key=rel_idem,
            title=f"Reservation Cancelled: {bed_num}",
            message=f"Reservation {res_id} for {bed_type} bed {bed_num} was cancelled. Capacity released to inventory.",
            event_type="RESERVATION_CANCELLED",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority="NORMAL",
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=rel_idem).first()
        if notif:
            notif.hospital_id = hid
            if referral:
                notif.referral_id = referral.referral_id

        if referral and referral.from_hospital_id and referral.from_hospital_id != hid:
            from_hid = referral.from_hospital_id
            from_idem = f"OP_BED_RELEASE_FROM_{res_id}"
            self._create_in_app_notification(
                idempotency_key=from_idem,
                title=f"Referral Hold Cancelled: {referral.referral_id}",
                message=f"Bed reservation at {hospital.name} for referral {referral.referral_id} was cancelled.",
                event_type="RESERVATION_CANCELLED",
                action_url=f"/hospitals/{from_hid}?tab=referrals",
                priority="NORMAL",
            )
            from_notif = self.session.query(Notification).filter_by(idempotency_key=from_idem).first()
            if from_notif:
                from_notif.hospital_id = from_hid
                from_notif.referral_id = referral.referral_id

    # ============================================================
    # 7. INVENTORY THRESHOLD NOTIFICATIONS (PHASE 4D-3)
    # ============================================================

    def notify_low_bed_availability(
        self,
        hospital,
        bed_type: str,
        available_count: Optional[int] = None,
        total_count: Optional[int] = None,
    ):
        """
        Trigger critical capacity alerts for hospital and district authorities
        when bed availability reaches critical threshold.
        Deduplicated per hospital, bed type, and hourly window to avoid notification spam.
        """
        if not hospital:
            return

        norm_type = (bed_type or "GENERAL").upper()
        if available_count is None or total_count is None:
            if norm_type == "ICU":
                available_count = hospital.available_icu_beds if hospital.available_icu_beds is not None else 0
                total_count = hospital.icu_beds if hospital.icu_beds is not None else 0
            elif norm_type == "EMERGENCY":
                available_count = hospital.available_emergency_beds if hospital.available_emergency_beds is not None else 0
                total_count = hospital.emergency_beds if hospital.emergency_beds is not None else 0
            else:
                available_count = hospital.available_beds if hospital.available_beds is not None else 0
                total_count = hospital.total_beds if hospital.total_beds is not None else 0

        # Meaningful threshold: ICU <= 1 or GENERAL <= 2 (or emergency == 0)
        if norm_type == "ICU":
            is_critical = (available_count <= 1)
        else:
            is_critical = (available_count <= 2)
        if not is_critical:
            return

        now = datetime.now(timezone.utc)
        hour_window = now.strftime("%Y%m%d%H")
        hid = hospital.hospital_id
        hname = hospital.name
        priority = "CRITICAL" if norm_type == "ICU" or available_count == 0 else "HIGH"

        # 1. In-app for hospital
        hosp_idem = f"OP_LOW_BED_{hid}_{norm_type}_{hour_window}"
        self._create_in_app_notification(
            idempotency_key=hosp_idem,
            title=f"Low {norm_type} Capacity Alert: {available_count} Remaining",
            message=f"Critical capacity threshold reached at {hname}: only {available_count} of {total_count} {norm_type} beds available.",
            event_type="LOW_BED_AVAILABILITY",
            action_url=f"/hospitals/{hid}?tab=inventory",
            priority=priority,
        )
        notif = self.session.query(Notification).filter_by(idempotency_key=hosp_idem).first()
        if notif:
            notif.hospital_id = hid

        # 2. In-app for district authority
        if hospital.state and hospital.district:
            dist_idem = f"OP_LOW_BED_DIST_{hid}_{norm_type}_{hour_window}"
            self._create_in_app_notification(
                idempotency_key=dist_idem,
                title=f"District Alert: Low {norm_type} Capacity at {hname}",
                message=f"{hname} ({hospital.district}, {hospital.state}) reports low {norm_type} capacity: {available_count} remaining.",
                event_type="LOW_BED_AVAILABILITY",
                role_id="DISTRICT_ADMIN",
                state=hospital.state,
                district=hospital.district,
                action_url="/district/hospitals",
                priority=priority,
            )

        # 3. In-app for state authority
        if hospital.state:
            state_idem = f"OP_LOW_BED_STATE_{hid}_{norm_type}_{hour_window}"
            self._create_in_app_notification(
                idempotency_key=state_idem,
                title=f"State Alert: Critical {norm_type} Shortage at {hname}",
                message=f"{hname} ({hospital.district}, {hospital.state}) reports critical {norm_type} capacity: {available_count} remaining.",
                event_type="LOW_BED_AVAILABILITY",
                role_id="STATE_ADMIN",
                state=hospital.state,
                action_url="/state/hospitals",
                priority=priority,
            )

        # 4. In-app for central authority (only on zero capacity emergency)
        if available_count == 0:
            central_idem = f"OP_LOW_BED_CENTRAL_{hid}_{norm_type}_{hour_window}"
            self._create_in_app_notification(
                idempotency_key=central_idem,
                title=f"Emergency: Zero {norm_type} Capacity at {hname}",
                message=f"Critical capacity exhaustion: {hname} ({hospital.district}, {hospital.state}) has 0 {norm_type} beds available.",
                event_type="LOW_BED_AVAILABILITY",
                role_id="CENTRAL_ADMIN",
                action_url="/central/hospitals",
                priority="CRITICAL",
            )

        # 5. Email to hospital administrators
        email_body = (
            f"Critical Bed Availability Warning\n\n"
            f"Facility: {hname}\n"
            f"Department: {norm_type} Department\n"
            f"Available Beds: {available_count} / {total_count}\n"
            f"Jurisdiction: {hospital.district}, {hospital.state}\n\n"
            f"Please manage admissions or request diversion support via your dashboard:\n"
            f"{get_portal_base_url()}/hospitals/{hid}?tab=inventory\n\n"
            f"ArogyaSetu Grid — Unified Critical Care & Hospital Command Network\n"
            f"Support: pawanbussiness108@gmail.com"
        )
        self._enqueue_hospital_emails(
            hospital_id=hid,
            event_type="LOW_BED_AVAILABILITY",
            subject=f"URGENT: Low {norm_type} Bed Availability at {hname}",
            body_text=email_body,
            base_idempotency_key=hosp_idem,
        )
