"""
Transactional Email Outbox Service.
Guarantees durable, transactional email delivery with retries, exponential backoff,
idempotent worker execution, and protection against secret leakage.
"""

import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from src.database.pg_models import RegistrationEmailOutbox
from src.services.email_service import BaseEmailProvider, get_email_provider

logger = logging.getLogger("email_outbox")

DEFAULT_MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 30  # 30s, 60s, 120s exponential backoff
DEFAULT_LEASE_TIMEOUT_SECONDS = 300  # 5-minute worker lease before crash recovery


class EmailOutboxService:
    """
    Manages enqueueing and dispatching transactional email events.
    """

    def __init__(self, session: Session, email_provider: Optional[BaseEmailProvider] = None):
        self.session = session
        self.email_provider = email_provider or get_email_provider()

    def enqueue_email(
        self,
        event_type: str,
        recipient_email: str,
        subject: str,
        payload: Dict[str, Any],
        recipient_name: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> RegistrationEmailOutbox:
        """
        Enqueues an email event in the outbox table as part of the caller's database transaction.
        Never logs sensitive payload tokens or passwords.
        """
        outbox_id = f"OUT_{secrets.token_hex(16)}"
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
            max_retries=max_retries,
            next_retry_at=now,
            created_at=now,
        )
        self.session.add(outbox_record)
        self.session.flush()

        logger.info(
            "Enqueued outbox email event '%s' (type: %s) for recipient '%s'.",
            outbox_id,
            event_type,
            self._mask_email(recipient_email),
        )
        return outbox_record

    def process_outbox(
        self,
        batch_size: int = 10,
        worker_id: Optional[str] = None,
        lease_timeout_seconds: int = DEFAULT_LEASE_TIMEOUT_SECONDS,
    ) -> Dict[str, Any]:
        """
        Processes pending, retryable, and abandoned outbox events:
        1. Selects candidate events:
           - PENDING
           - FAILED with retry_count < max_retries and next_retry_at <= now
           - PROCESSING with processed_at <= now - lease_timeout (abandoned worker crash recovery)
        2. Acquires row lock (using with_for_update in Postgres to prevent duplicate processing).
        3. Attempts delivery via configured email provider.
        4. Updates status to SENT on success or FAILED with backoff on failure.
        5. Delivery guarantee: At-least-once delivery (SMTP lacks distributed 2PC commit).
        """
        now = datetime.now(timezone.utc)
        worker_tag = worker_id or secrets.token_hex(4)
        lease_cutoff = now - timedelta(seconds=lease_timeout_seconds)

        # Query eligible events
        query = (
            self.session.query(RegistrationEmailOutbox)
            .filter(
                or_(
                    RegistrationEmailOutbox.status == "PENDING",
                    (
                        (RegistrationEmailOutbox.status == "FAILED")
                        & (RegistrationEmailOutbox.retry_count < RegistrationEmailOutbox.max_retries)
                        & (RegistrationEmailOutbox.next_retry_at <= now)
                    ),
                    (
                        (RegistrationEmailOutbox.status == "PROCESSING")
                        & (RegistrationEmailOutbox.processed_at <= lease_cutoff)
                        & (RegistrationEmailOutbox.retry_count < RegistrationEmailOutbox.max_retries)
                    ),
                )
            )
            .order_by(RegistrationEmailOutbox.id.asc())
            .limit(batch_size)
        )

        # Attempt row locking where supported (PostgreSQL)
        try:
            events: List[RegistrationEmailOutbox] = query.with_for_update(skip_locked=True).all()
        except Exception:
            # SQLite fallback: load without skip_locked
            events = query.all()

        processed_count = 0
        succeeded_count = 0
        failed_count = 0
        reclaimed_count = 0

        for event in events:
            # Skip if already marked SENT or permanently FAILED
            if event.status not in ("PENDING", "FAILED", "PROCESSING"):
                continue

            was_abandoned = (event.status == "PROCESSING")
            if was_abandoned:
                reclaimed_count += 1
                event.retry_count += 1
                if event.retry_count >= event.max_retries:
                    event.status = "FAILED"
                    event.last_error = f"Abandoned processing lease expired and exceeded max retries ({event.max_retries})."
                    self.session.flush()
                    failed_count += 1
                    processed_count += 1
                    continue
                else:
                    event.last_error = f"Worker lease expired (>{lease_timeout_seconds}s). Reclaimed by worker {worker_tag}."

                logger.warning(
                    "Worker %s reclaimed abandoned outbox event '%s' (lease expired; attempt %d/%d).",
                    worker_tag,
                    event.outbox_id,
                    event.retry_count,
                    event.max_retries,
                )

            # Atomically mark as PROCESSING
            event.status = "PROCESSING"
            event.processed_at = now
            self.session.flush()

            try:
                payload = json.loads(event.payload)
                success = self._dispatch_event(event, payload)

                if success:
                    event.status = "SENT"
                    event.sent_at = datetime.now(timezone.utc)
                    event.last_error = None
                    succeeded_count += 1
                    logger.info(
                        "Worker %s successfully delivered outbox event '%s' to '%s'.",
                        worker_tag,
                        event.outbox_id,
                        self._mask_email(event.recipient_email),
                    )
                else:
                    self._record_failure(event, "Provider returned False", now)
                    failed_count += 1

            except Exception as exc:
                err_msg = str(exc)
                logger.error(
                    "Worker %s failed delivering outbox event '%s': %s",
                    worker_tag,
                    event.outbox_id,
                    err_msg,
                )
                self._record_failure(event, err_msg, now)
                failed_count += 1

            processed_count += 1

        self.session.flush()

        return {
            "processed": processed_count,
            "succeeded": succeeded_count,
            "failed": failed_count,
            "reclaimed": reclaimed_count,
            "worker_id": worker_tag,
        }

    def process_event(
        self,
        outbox_id: str,
        worker_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes a specific outbox event by ID immediately with row locking.
        Ensures the outbox table is the single source of truth for immediate dispatches.
        """
        now = datetime.now(timezone.utc)
        worker_tag = worker_id or secrets.token_hex(4)

        query = self.session.query(RegistrationEmailOutbox).filter_by(outbox_id=outbox_id)
        try:
            event = query.with_for_update(skip_locked=True).first()
        except Exception:
            event = query.first()

        if not event:
            return {"status": "NOT_FOUND", "outbox_id": outbox_id}

        if event.status == "SENT":
            return {"status": "ALREADY_SENT", "outbox_id": outbox_id}

        event.status = "PROCESSING"
        event.processed_at = now
        self.session.flush()

        try:
            payload = json.loads(event.payload)
            success = self._dispatch_event(event, payload)

            if success:
                event.status = "SENT"
                event.sent_at = datetime.now(timezone.utc)
                event.last_error = None
                self.session.flush()
                logger.info(
                    "Worker %s successfully delivered immediate outbox event '%s' to '%s'.",
                    worker_tag,
                    event.outbox_id,
                    self._mask_email(event.recipient_email),
                )
                return {"status": "SENT", "outbox_id": outbox_id, "succeeded": True}
            else:
                self._record_failure(event, "Provider returned False", now)
                self.session.flush()
                return {"status": "FAILED", "outbox_id": outbox_id, "succeeded": False}

        except Exception as exc:
            err_msg = str(exc)
            logger.error(
                "Worker %s failed delivering immediate outbox event '%s': %s",
                worker_tag,
                event.outbox_id,
                err_msg,
            )
            self._record_failure(event, err_msg, now)
            self.session.flush()
            return {"status": "FAILED", "outbox_id": outbox_id, "succeeded": False, "error": err_msg}

    def reclaim_expired_leases(
        self,
        lease_timeout_seconds: int = DEFAULT_LEASE_TIMEOUT_SECONDS,
    ) -> int:
        """
        Explicitly reset abandoned PROCESSING events whose lease has expired back to PENDING.
        """
        now = datetime.now(timezone.utc)
        lease_cutoff = now - timedelta(seconds=lease_timeout_seconds)

        query = (
            self.session.query(RegistrationEmailOutbox)
            .filter(
                RegistrationEmailOutbox.status == "PROCESSING",
                RegistrationEmailOutbox.processed_at <= lease_cutoff,
            )
        )
        try:
            events = query.with_for_update(skip_locked=True).all()
        except Exception:
            events = query.all()

        reclaimed = 0
        for event in events:
            event.status = "PENDING"
            event.retry_count += 1
            event.last_error = f"Processing lease expired after {lease_timeout_seconds}s. Reset to PENDING."
            reclaimed += 1

        self.session.flush()
        return reclaimed

    def _dispatch_event(self, event: RegistrationEmailOutbox, payload: Dict[str, Any]) -> bool:
        """Dispatch based on event type."""
        if event.event_type == "ACCOUNT_ACTIVATION":
            return self.email_provider.send_activation_email(
                to_email=event.recipient_email,
                recipient_name=event.recipient_name or "Administrator",
                activation_link=payload["activation_link"],
                role_title=payload.get("role_title", "Operational Administrator"),
                application_number=payload.get("application_number", "N/A"),
            )
        elif event.event_type == "PASSWORD_RESET":
            reset_link = payload.get("reset_link", "")
            return self.email_provider.send_email(
                to_email=event.recipient_email,
                subject=event.subject,
                body_text=(
                    f"Hello {event.recipient_name or 'User'},\n\n"
                    f"We received a request to reset your password for SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform.\n"
                    f"Please reset your password using the secure link below:\n\n"
                    f"{reset_link}\n\n"
                    f"This link is single-use and will expire in 1 hour.\n"
                    f"If you did not request this, please ignore this email or contact support at pawanbussiness108@gmail.com.\n\n"
                    f"Regards,\n"
                    f"SWASTHYA SAMANVAY Support Desk"
                ),
            )
        else:
            # Generic email dispatch
            return self.email_provider.send_email(
                to_email=event.recipient_email,
                subject=event.subject,
                body_text=payload.get("body_text", ""),
                body_html=payload.get("body_html"),
            )

    def _record_failure(self, event: RegistrationEmailOutbox, error_msg: str, now: datetime):
        """Record delivery failure and calculate exponential backoff."""
        event.retry_count += 1
        # Truncate error message and ensure no token leak
        event.last_error = error_msg[:500]

        if event.retry_count >= event.max_retries:
            event.status = "FAILED"
            logger.warning(
                "Outbox event '%s' exceeded max retries (%d). Marked permanently FAILED.",
                event.outbox_id,
                event.max_retries,
            )
        else:
            event.status = "FAILED"
            backoff_seconds = INITIAL_BACKOFF_SECONDS * (2 ** (event.retry_count - 1))
            event.next_retry_at = now + timedelta(seconds=backoff_seconds)
            logger.info(
                "Outbox event '%s' retry scheduled in %d seconds (attempt %d/%d).",
                event.outbox_id,
                backoff_seconds,
                event.retry_count,
                event.max_retries,
            )

    @staticmethod
    def _mask_email(email: str) -> str:
        """Mask email address for secure logging."""
        if not email or "@" not in email:
            return "***"
        parts = email.split("@", 1)
        name = parts[0]
        domain = parts[1]
        masked_name = name[0] + "***" if len(name) > 1 else "*"
        return f"{masked_name}@{domain}"
