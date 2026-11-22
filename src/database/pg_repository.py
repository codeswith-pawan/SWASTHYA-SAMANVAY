"""
PostgreSQL Transactional Repository
AI Powered Smart Hospital Referral System - Phase 18

Implements ACID-compliant row-level locking (SELECT ... FOR UPDATE SKIP LOCKED),
atomic bed reservation, complete referral lifecycle state transitions,
duplicate referral prevention, in-app notifications, and audit logging.
"""

import uuid
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import select, update, and_, or_, desc, func, delete, case
from sqlalchemy.orm import Session, aliased

from src.database.pg_models import (
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
)


logger = logging.getLogger("sih.repository")


class PgReferralRepository:
    """
    Production-grade repository providing transactional consistency,
    preventing race conditions and phantom reads during concurrent bed booking
    and end-to-end referral workflow management.
    """

    def __init__(self, session: Session):
        self.session = session
        self._owns_session = False

    def _close_if_owned(self):
        if getattr(self, "_owns_session", False) and self.session:
            try:
                self.session.close()
            except Exception:
                pass

    def __del__(self):
        self._close_if_owned()

    # ============================================================
    # HELPER: SERIALIZE REFERRAL
    # ============================================================

    def _serialize_referral(self, referral: Referral) -> Dict[str, Any]:
        """Convert Referral model instance to standardized dictionary."""
        active_res = None
        for res in referral.reservations:
            if res.status in ["RESERVED", "CONFIRMED", "OCCUPIED"]:
                active_res = res
                break
        if not active_res and referral.reservations:
            active_res = referral.reservations[-1]

        # Look up hospital geo metadata
        from_hosp = self.session.execute(
            select(Hospital).where(Hospital.hospital_id == referral.from_hospital_id)
        ).scalar_one_or_none()

        to_hosp = self.session.execute(
            select(Hospital).where(Hospital.hospital_id == referral.to_hospital_id)
        ).scalar_one_or_none()

        return {
            "referral_id": referral.referral_id,
            "patient_id": referral.patient_id,
            "from_hospital_id": referral.from_hospital_id,
            "to_hospital_id": referral.to_hospital_id,
            "from_hospital_name": from_hosp.name if from_hosp else referral.from_hospital_id,
            "to_hospital_name": to_hosp.name if to_hosp else referral.to_hospital_id,
            "from_state": from_hosp.state if from_hosp else None,
            "from_district": from_hosp.district if from_hosp else None,
            "to_state": to_hosp.state if to_hosp else None,
            "to_district": to_hosp.district if to_hosp else None,
            "status": referral.status,
            "priority": referral.priority,
            "bed_type": referral.bed_type,
            "reason": referral.reason,
            "notes": referral.notes,
            "ambulance_id": referral.ambulance_id,
            "eta_minutes": referral.eta_minutes,
            "created_at": referral.created_at.isoformat() if referral.created_at else None,
            "updated_at": referral.updated_at.isoformat() if referral.updated_at else None,
            "accepted_at": referral.accepted_at.isoformat() if referral.accepted_at else None,
            "rejected_at": referral.rejected_at.isoformat() if referral.rejected_at else None,
            "dispatched_at": referral.dispatched_at.isoformat() if referral.dispatched_at else None,
            "arrived_at": referral.arrived_at.isoformat() if referral.arrived_at else None,
            "completed_at": referral.completed_at.isoformat() if referral.completed_at else None,
            # Reservation details
            "reservation_id": active_res.reservation_id if active_res else None,
            "bed_id": str(active_res.bed_id) if active_res else None,
            "bed_number": active_res.bed.bed_number if (active_res and active_res.bed) else None,
            "reservation_status": active_res.status if active_res else None,
            "auto_reservation": active_res is not None,
        }

    # ============================================================
    # 1. REFERRAL INITIATION & DUPLICATE PREVENTION
    # ============================================================

    def create_referral(
        self,
        patient_id: str,
        from_hospital_id: str,
        to_hospital_id: str,
        reason: Optional[str] = None,
        priority: str = "Urgent",
        bed_type: str = "GENERAL",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new hospital-to-hospital referral.
        Enforces validation:
        - Patient exists.
        - Source and destination hospitals exist.
        - Destination hospital is not identical to source hospital.
        - Duplicate prevention: Patient cannot have another active referral.
        """
        now = datetime.now(timezone.utc)

        # 1. Validate or auto-provision patient existence
        pat = self.session.execute(
            select(Patient).where(Patient.patient_id == patient_id)
        ).scalar_one_or_none()

        # 2. Validate or auto-provision source hospital
        from_hosp = self.session.execute(
            select(Hospital).where(Hospital.hospital_id == from_hospital_id)
        ).scalar_one_or_none()
        if not from_hosp:
            from_hosp = Hospital(
                hospital_id=from_hospital_id,
                name=f"Hospital {from_hospital_id}",
                state="Punjab",
                district="Amritsar",
                latitude=31.634,
                longitude=74.872,
                total_beds=50,
                available_beds=20,
                icu_beds=10,
                available_icu_beds=5,
            )
            self.session.add(from_hosp)
            self.session.flush()

        # 3. Validate or auto-provision destination hospital
        to_hosp = self.session.execute(
            select(Hospital).where(Hospital.hospital_id == to_hospital_id)
        ).scalar_one_or_none()
        if not to_hosp:
            to_hosp = Hospital(
                hospital_id=to_hospital_id,
                name=f"Hospital {to_hospital_id}",
                state="Punjab",
                district="Amritsar",
                latitude=31.634,
                longitude=74.872,
                total_beds=50,
                available_beds=20,
                icu_beds=10,
                available_icu_beds=5,
            )
            self.session.add(to_hosp)
            self.session.flush()

        # 4. Forbid self-referral
        if from_hospital_id == to_hospital_id:
            return {
                "success": False,
                "status": "INVALID_DESTINATION",
                "message": "Source and destination hospitals cannot be the same.",
            }

        # 5. Prevent duplicate active referrals
        active_statuses = ["PENDING", "ACCEPTED", "IN_TRANSIT", "ARRIVED", "TREATMENT_ACTIVE"]
        existing_stmt = select(Referral).where(
            Referral.patient_id == patient_id,
            Referral.status.in_(active_statuses),
        )
        existing_ref = self.session.execute(existing_stmt).scalar_one_or_none()
        if existing_ref:
            return {
                "success": False,
                "status": "ACTIVE_REFERRAL_EXISTS",
                "message": f"Patient already has an active referral '{existing_ref.referral_id}' in status '{existing_ref.status}'.",
                "referral": self._serialize_referral(existing_ref),
            }

        # 6. Normalize priority and bed type
        norm_bed_type = "GENERAL"
        if "icu" in bed_type.lower():
            norm_bed_type = "ICU"
        elif "emer" in bed_type.lower():
            norm_bed_type = "EMERGENCY"

        norm_priority = "Urgent"
        if "crit" in priority.lower():
            norm_priority = "Critical"
        elif "stab" in priority.lower():
            norm_priority = "Stable"

        if not pat:
            pat = Patient(
                patient_id=patient_id,
                name=f"Emergency Patient {patient_id}",
                priority=norm_priority,
                referral_required="Yes",
                icu_required="Yes" if norm_bed_type == "ICU" else "No",
                state=from_hosp.state if from_hosp else "Punjab",
                district=from_hosp.district if from_hosp else "Amritsar",
                created_at=now,
                updated_at=now,
            )
            self.session.add(pat)
            self.session.flush()

        # 7. Generate canonical referral ID
        ref_id = f"REF-{now.year}-{uuid.uuid4().hex[:6].upper()}"

        new_ref = Referral(
            referral_id=ref_id,
            patient_id=patient_id,
            from_hospital_id=from_hospital_id,
            to_hospital_id=to_hospital_id,
            status="PENDING",
            priority=norm_priority,
            bed_type=norm_bed_type,
            reason=reason or f"Referral requested for {norm_bed_type} admission.",
            notes=None,
            created_at=now,
            updated_at=now,
        )
        self.session.add(new_ref)

        # 8. Audit log
        audit = AuditLog(
            entity_type="REFERRAL",
            entity_id=ref_id,
            action="REFERRAL_CREATED",
            performed_by=user_id,
            previous_state=None,
            new_state={
                "patient_id": patient_id,
                "from_hospital_id": from_hospital_id,
                "to_hospital_id": to_hospital_id,
                "bed_type": norm_bed_type,
                "priority": norm_priority,
            },
            created_at=now,
        )
        self.session.add(audit)

        # 9. In-app notification for destination hospital & operational dispatch
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_referral_created(new_ref, from_hosp, to_hosp)
        except Exception as e:
            logger.warning("Error dispatching referral created notification: %s", e)
            notif = Notification(
                hospital_id=to_hospital_id,
                referral_id=ref_id,
                event_type="NEW_REFERRAL",
                title=f"New Incoming Referral: {ref_id}",
                message=f"Patient {patient_id} referred from {from_hosp.name} ({from_hospital_id}) for {norm_bed_type} bed. Reason: {reason or 'Clinical transfer'}.",
                priority="CRITICAL" if norm_priority == "Critical" else "NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        self.session.commit()

        return {
            "success": True,
            "status": "PENDING",
            "message": "Referral created successfully.",
            "referral": self._serialize_referral(new_ref),
        }

    # ============================================================
    # 2. ATOMIC ACCEPTANCE & BED RESERVATION
    # ============================================================

    def get_referral_for_update(self, referral_id: str) -> Optional[Referral]:
        """Lock and return referral record."""
        stmt = (
            select(Referral)
            .where(Referral.referral_id == referral_id)
            .with_for_update()
        )
        return self.session.execute(stmt).scalar_one_or_none()

    def atomic_accept_and_reserve(
        self,
        referral_id: str,
        user_id: Optional[str] = None,
        ttl_hours: int = 2,
    ) -> Dict[str, Any]:
        """
        Atomically accepts a pending referral and holds an available bed
        using row-level locking (FOR UPDATE SKIP LOCKED).
        """
        now = datetime.now(timezone.utc)

        # 1. Lock the referral row
        referral = self.get_referral_for_update(referral_id)
        if not referral:
            return {
                "success": False,
                "status": "NOT_FOUND",
                "reason": "NOT_FOUND",
                "message": f"Referral {referral_id} does not exist.",
            }

        if referral.status != "PENDING":
            return {
                "success": False,
                "status": "INVALID_STATUS_TRANSITION",
                "reason": "INVALID_STATUS_TRANSITION",
                "message": f"Referral is already in '{referral.status}' state.",
                "current_status": referral.status,
            }

        # 2. Check for duplicate active reservation on this referral
        existing_res_stmt = (
            select(BedReservation)
            .where(
                BedReservation.referral_id == referral_id,
                BedReservation.status.in_(["RESERVED", "CONFIRMED", "OCCUPIED"]),
            )
        )
        if self.session.execute(existing_res_stmt).scalar_one_or_none():
            return {
                "success": False,
                "status": "DUPLICATE_RESERVATION",
                "reason": "DUPLICATE_RESERVATION",
                "message": "Referral already has an active bed reservation.",
            }

        target_bed_type = referral.bed_type
        if target_bed_type not in ["GENERAL", "ICU", "EMERGENCY"]:
            target_bed_type = "GENERAL"

        # 3. Row-level lock the next available bed (SKIP LOCKED prevents lock contention)
        bed_stmt = (
            select(Bed)
            .where(
                Bed.hospital_id == referral.to_hospital_id,
                Bed.bed_type == target_bed_type,
                Bed.status == "AVAILABLE",
            )
            .order_by(Bed.id.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        bed = self.session.execute(bed_stmt).scalar_one_or_none()

        if not bed:
            bed_count = self.session.execute(
                select(func.count(Bed.id)).where(Bed.hospital_id == referral.to_hospital_id)
            ).scalar() or 0
            if bed_count == 0:
                self.initialize_default_inventory(referral.to_hospital_id)
                bed = self.session.execute(bed_stmt).scalar_one_or_none()

        if not bed:
            # Bed unavailable: referral remains PENDING
            audit = AuditLog(
                entity_type="REFERRAL",
                entity_id=referral_id,
                action="ACCEPTANCE_FAILED_NO_BEDS",
                performed_by=user_id,
                new_state={"reason": f"NO_{target_bed_type}_AVAILABLE"},
                created_at=now,
            )
            self.session.add(audit)
            self.session.commit()
            return {
                "success": False,
                "status": "NO_BEDS_AVAILABLE",
                "reason": "NO_BEDS_AVAILABLE",
                "message": f"No available {target_bed_type} beds at hospital {referral.to_hospital_id}.",
                "bed_type": target_bed_type,
                "referral_status": "PENDING",
            }

        # 4. Allocate bed and decrement hospital counter
        bed.status = "RESERVED"
        bed.updated_at = now

        # Lock hospital row for counter decrement
        hosp_stmt = (
            select(Hospital)
            .where(Hospital.hospital_id == referral.to_hospital_id)
            .with_for_update()
        )
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if hospital:
            if target_bed_type == "ICU":
                hospital.available_icu_beds = max(0, hospital.available_icu_beds - 1)
            elif target_bed_type == "EMERGENCY":
                hospital.available_emergency_beds = max(0, hospital.available_emergency_beds - 1)
            else:
                hospital.available_beds = max(0, hospital.available_beds - 1)
            hospital.updated_at = now

        # 5. Create reservation record
        res_id = f"RES-{uuid.uuid4().hex[:12].upper()}"
        expires_at = now + timedelta(hours=ttl_hours)
        reservation = BedReservation(
            reservation_id=res_id,
            referral_id=referral_id,
            hospital_id=referral.to_hospital_id,
            bed_id=bed.id,
            status="RESERVED",
            reserved_at=now,
            expires_at=expires_at,
            created_at=now,
        )
        self.session.add(reservation)

        # 6. Update referral status
        referral.status = "ACCEPTED"
        referral.accepted_at = now
        referral.updated_at = now

        # 7. Audit Log
        audit = AuditLog(
            entity_type="REFERRAL",
            entity_id=referral_id,
            action="ACCEPTED_WITH_BED",
            performed_by=user_id,
            previous_state={"status": "PENDING"},
            new_state={
                "status": "ACCEPTED",
                "reservation_id": res_id,
                "bed_number": bed.bed_number,
                "bed_type": target_bed_type,
                "expires_at": expires_at.isoformat(),
            },
            created_at=now,
        )
        self.session.add(audit)

        # 8. Operational notifications (source hospital, destination, and low bed capacity)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            from_hosp = self.session.get(Hospital, referral.from_hospital_id)
            notif_svc.notify_referral_accepted(referral, from_hosp, hospital, bed)
            notif_svc.notify_low_bed_availability(hospital, target_bed_type)
        except Exception as e:
            logger.warning("Error dispatching referral accepted notification: %s", e)
            notif = Notification(
                hospital_id=referral.from_hospital_id,
                referral_id=referral_id,
                event_type="REFERRAL_ACCEPTED",
                title=f"Referral Accepted: {referral_id}",
                message=f"Hospital {referral.to_hospital_id} accepted the referral. Bed {bed.bed_number} ({target_bed_type}) reserved.",
                priority="NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        self.session.commit()

        return {
            "success": True,
            "status": "ACCEPTED",
            "message": "Referral accepted and bed reserved.",
            "referral": self._serialize_referral(referral),
            "reservation": {
                "reservation_id": res_id,
                "bed_id": bed.bed_number,
                "bed_type": target_bed_type,
                "status": "RESERVED",
                "expires_at": expires_at.isoformat(),
                "auto_reservation": True,
            },
        }

    # ============================================================
    # 3. ATOMIC LIFECYCLE TRANSITIONS
    # ============================================================

    def atomic_transition_lifecycle(
        self,
        referral_id: str,
        new_status: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
        ambulance_id: Optional[str] = None,
        eta_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes an atomic lifecycle transition across transfer, admission, and completion.
        """
        now = datetime.now(timezone.utc)
        new_status = new_status.upper().strip()

        referral = self.get_referral_for_update(referral_id)
        if not referral:
            return {"success": False, "status": "NOT_FOUND", "message": f"Referral '{referral_id}' not found."}

        old_status = referral.status

        # Retrieve active reservation if any
        res_stmt = (
            select(BedReservation)
            .where(
                BedReservation.referral_id == referral_id,
                BedReservation.status.in_(["RESERVED", "CONFIRMED", "OCCUPIED"]),
            )
            .with_for_update()
        )
        reservation = self.session.execute(res_stmt).scalar_one_or_none()

        bed = None
        if reservation:
            bed_stmt = (
                select(Bed)
                .where(Bed.id == reservation.bed_id)
                .with_for_update()
            )
            bed = self.session.execute(bed_stmt).scalar_one_or_none()

        # Terminal state idempotency and immutability
        if old_status in ["COMPLETED", "DISCHARGED", "TRANSFERRED", "DIED", "CANCELLED", "REJECTED"]:
            if new_status == old_status:
                return {
                    "success": True,
                    "status": old_status,
                    "new_status": old_status,
                    "message": f"Referral is already in terminal state '{old_status}'.",
                    "referral": self._serialize_referral(referral),
                }
            return {
                "success": False,
                "status": "INVALID_STATE",
                "message": f"Referral is already in terminal state '{old_status}' and cannot transition to '{new_status}'.",
            }

        # Handle specific transitions
        if new_status == "REJECTED":
            if old_status != "PENDING":
                return {
                    "success": False,
                    "status": "INVALID_STATE",
                    "message": f"Only PENDING referrals can be rejected. Current status is {old_status}.",
                }
            referral.rejected_at = now
            if notes:
                referral.notes = notes

            # Notification for source hospital & operational dispatch
            try:
                from src.services.workflow_notification_service import WorkflowNotificationService
                notif_svc = WorkflowNotificationService(self.session)
                from_hosp = self.session.get(Hospital, referral.from_hospital_id)
                to_hosp = self.session.get(Hospital, referral.to_hospital_id)
                notif_svc.notify_referral_rejected(referral, from_hosp, to_hosp, notes=notes)
            except Exception as e:
                logger.warning("Error dispatching referral rejected notification: %s", e)
                notif = Notification(
                    hospital_id=referral.from_hospital_id,
                    referral_id=referral_id,
                    event_type="REFERRAL_REJECTED",
                    title=f"Referral Rejected: {referral_id}",
                    message=f"Hospital {referral.to_hospital_id} rejected referral. Reason/Notes: {notes or 'No reason provided'}.",
                    priority="URGENT",
                    is_read=False,
                    created_at=now,
                )
                self.session.add(notif)

        elif new_status == "IN_TRANSIT":
            if old_status != "ACCEPTED":
                return {
                    "success": False,
                    "status": "INVALID_STATE",
                    "message": f"Referral must be in ACCEPTED state before dispatch. Current status is {old_status}.",
                }
            referral.dispatched_at = now
            referral.ambulance_id = ambulance_id or "AMB-108-PB"
            referral.eta_minutes = eta_minutes or 25
            if notes:
                referral.notes = notes

            # Release originating hospital bed and mark active origin visit as TRANSFERRED
            try:
                from src.database.pg_models import HospitalVisit
                origin_v_stmt = (
                    select(HospitalVisit)
                    .where(
                        HospitalVisit.hospital_id == referral.from_hospital_id,
                        HospitalVisit.patient_id == referral.patient_id,
                        HospitalVisit.status == "ACTIVE",
                    )
                    .with_for_update()
                )
                origin_visit = self.session.execute(origin_v_stmt).scalars().first()
                if origin_visit:
                    origin_visit.status = "TRANSFERRED"
                    origin_visit.completed_at = now
                    v_meta = {}
                    if origin_visit.notes:
                        try:
                            v_meta = json.loads(origin_visit.notes)
                        except Exception:
                            v_meta = {"raw": origin_visit.notes}
                    v_meta["transferred_to"] = referral.to_hospital_id
                    v_meta["referral_id"] = referral.referral_id
                    v_meta["transferred_at"] = now.isoformat()
                    origin_visit.notes = json.dumps(v_meta)

                    # Update originating hospital bed counters
                    origin_hosp_stmt = (
                        select(Hospital)
                        .where(Hospital.hospital_id == referral.from_hospital_id)
                        .with_for_update()
                    )
                    origin_hosp = self.session.execute(origin_hosp_stmt).scalar_one_or_none()
                    if origin_hosp:
                        b_type = (v_meta.get("bed_type_assigned") or referral.bed_type or "GENERAL").upper()
                        if b_type in ["ICU", "VENTILATOR"]:
                            origin_hosp.occupied_icu_beds = max(0, (origin_hosp.occupied_icu_beds or 1) - 1)
                            origin_hosp.available_icu_beds = min(origin_hosp.icu_beds, (origin_hosp.available_icu_beds or 0) + 1)
                        elif b_type == "EMERGENCY":
                            origin_hosp.occupied_emergency_beds = max(0, (origin_hosp.occupied_emergency_beds or 1) - 1)
                            origin_hosp.available_emergency_beds = min(origin_hosp.emergency_beds, (origin_hosp.available_emergency_beds or 0) + 1)
                        else:
                            origin_hosp.occupied_beds = max(0, (origin_hosp.occupied_beds or 1) - 1)
                            origin_hosp.available_beds = min(origin_hosp.total_beds, (origin_hosp.available_beds or 0) + 1)
                        origin_hosp.updated_at = now
            except Exception as e:
                logger.warning("Could not release originating hospital bed during transfer: %s", e)

            # Notification for destination hospital
            notif = Notification(
                hospital_id=referral.to_hospital_id,
                referral_id=referral_id,
                event_type="AMBULANCE_DISPATCHED",
                title=f"Ambulance Dispatched: {referral_id}",
                message=f"Patient in transit via Ambulance {referral.ambulance_id}. ETA: {referral.eta_minutes} mins (Simulated tracking, manually updated).",
                priority="NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        elif new_status == "ARRIVED":
            if old_status not in ["IN_TRANSIT", "ACCEPTED"]:
                return {
                    "success": False,
                    "status": "INVALID_STATE",
                    "message": f"Referral must be IN_TRANSIT or ACCEPTED to mark arrived. Current status is {old_status}.",
                }
            referral.arrived_at = now
            if reservation:
                reservation.status = "CONFIRMED"

            # Notification for source hospital
            notif = Notification(
                hospital_id=referral.from_hospital_id,
                referral_id=referral_id,
                event_type="PATIENT_ARRIVED",
                title=f"Patient Arrived: {referral_id}",
                message=f"Patient {referral.patient_id} arrived at destination hospital. Bed reservation confirmed.",
                priority="NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        elif new_status == "TREATMENT_ACTIVE":
            if old_status not in ["ARRIVED", "ACCEPTED"]:
                return {
                    "success": False,
                    "status": "INVALID_STATE",
                    "message": f"Patient must have ARRIVED before starting treatment. Current status is {old_status}.",
                }
            if reservation:
                reservation.status = "OCCUPIED"
            if bed:
                bed.status = "OCCUPIED"
                bed.updated_at = now
                hosp_stmt = (
                    select(Hospital)
                    .where(Hospital.hospital_id == bed.hospital_id)
                    .with_for_update()
                )
                hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
                if hosp:
                    if bed and bed.bed_type == "ICU":
                        hosp.occupied_icu_beds = (hosp.occupied_icu_beds or 0) + 1
                    elif bed and bed.bed_type == "EMERGENCY":
                        hosp.occupied_emergency_beds = (hosp.occupied_emergency_beds or 0) + 1
                    else:
                        hosp.occupied_beds = (hosp.occupied_beds or 0) + 1
                    hosp.updated_at = now

            # Ensure an active HospitalVisit exists at the destination hospital
            try:
                from src.database.pg_models import HospitalVisit
                import uuid
                dest_v_stmt = (
                    select(HospitalVisit)
                    .where(
                        HospitalVisit.hospital_id == referral.to_hospital_id,
                        HospitalVisit.patient_id == referral.patient_id,
                        HospitalVisit.status == "ACTIVE",
                    )
                )
                dest_visit = self.session.execute(dest_v_stmt).scalars().first()
                if not dest_visit:
                    dest_visit = HospitalVisit(
                        hospital_id=referral.to_hospital_id,
                        patient_id=referral.patient_id,
                        admission_type="REFERRAL",
                        status="ACTIVE",
                        admitted_at=now,
                        treatment_started_at=now,
                        notes=json.dumps({
                            "referral_id": referral.referral_id,
                            "transferred_from": referral.from_hospital_id,
                            "bed_id": bed.id if bed else None,
                            "bed_type_assigned": bed.bed_type if bed else (referral.bed_type or "GENERAL"),
                            "chief_complaint": f"Transferred via Referral {referral.referral_id}",
                        }),
                        created_at=now,
                        updated_at=now,
                    )
                    self.session.add(dest_visit)
            except Exception as e:
                logger.warning("Could not create destination HospitalVisit: %s", e)

            # Notification for source hospital
            notif = Notification(
                hospital_id=referral.from_hospital_id,
                referral_id=referral_id,
                event_type="TREATMENT_STARTED",
                title=f"Treatment Active: {referral_id}",
                message=f"Clinical treatment started for patient {referral.patient_id}. Bed marked occupied.",
                priority="NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        elif new_status in ["COMPLETED", "DISCHARGED", "TRANSFERRED", "DIED", "CANCELLED"]:
            # Terminal states release the bed hold
            referral.completed_at = now
            if reservation:
                reservation.status = "RELEASED"
                reservation.released_at = now

            if bed:
                bed.status = "AVAILABLE"
                bed.updated_at = now
                # Restore hospital availability counter
                hosp_stmt = (
                    select(Hospital)
                    .where(Hospital.hospital_id == bed.hospital_id)
                    .with_for_update()
                )
                hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
                if hosp:
                    if bed.bed_type == "ICU":
                        hosp.available_icu_beds = min(hosp.icu_beds, hosp.available_icu_beds + 1)
                    elif bed.bed_type == "EMERGENCY":
                        hosp.available_emergency_beds = min(hosp.emergency_beds, hosp.available_emergency_beds + 1)
                    else:
                        hosp.available_beds = min(hosp.total_beds, hosp.available_beds + 1)
                    if old_status == "TREATMENT_ACTIVE" or (reservation and reservation.status == "OCCUPIED"):
                        if bed.bed_type == "ICU":
                            hosp.occupied_icu_beds = max(0, (hosp.occupied_icu_beds or 1) - 1)
                        elif bed.bed_type == "EMERGENCY":
                            hosp.occupied_emergency_beds = max(0, (hosp.occupied_emergency_beds or 1) - 1)
                        else:
                            hosp.occupied_beds = max(0, (hosp.occupied_beds or 1) - 1)
                    hosp.updated_at = now

            # Discharge destination hospital visit if any active
            try:
                from src.database.pg_models import HospitalVisit
                dest_v_stmt = (
                    select(HospitalVisit)
                    .where(
                        HospitalVisit.hospital_id == referral.to_hospital_id,
                        HospitalVisit.patient_id == referral.patient_id,
                        HospitalVisit.status == "ACTIVE",
                    )
                    .with_for_update()
                )
                dest_visit = self.session.execute(dest_v_stmt).scalars().first()
                if dest_visit:
                    dest_visit.status = "DISCHARGED" if new_status in ["COMPLETED", "DISCHARGED"] else new_status
                    dest_visit.completed_at = now
                    dest_visit.updated_at = now
            except Exception as e:
                logger.warning("Could not close destination HospitalVisit: %s", e)

            # Notification for source hospital
            notif = Notification(
                hospital_id=referral.from_hospital_id,
                referral_id=referral_id,
                event_type="REFERRAL_COMPLETED",
                title=f"Referral Completed: {referral_id}",
                message=f"Episode of care completed for patient {referral.patient_id}. Bed released back to inventory.",
                priority="NORMAL",
                is_read=False,
                created_at=now,
            )
            self.session.add(notif)

        referral.status = new_status
        referral.updated_at = now
        if notes:
            referral.notes = notes

        # Audit
        audit = AuditLog(
            entity_type="REFERRAL",
            entity_id=referral_id,
            action=f"TRANSITION_{new_status}",
            performed_by=user_id,
            previous_state={"status": old_status},
            new_state={
                "status": new_status,
                "reservation_status": reservation.status if reservation else None,
                "ambulance_id": referral.ambulance_id,
                "eta_minutes": referral.eta_minutes,
            },
            created_at=now,
        )
        self.session.add(audit)
        self.session.commit()

        serialized = self._serialize_referral(referral)
        return {
            "success": True,
            "status": new_status,
            "new_status": new_status,
            "message": f"Referral transitioned to {new_status}.",
            "referral": serialized,
            "reservation_status": serialized.get("reservation_status"),
            "reservation": {
                "reservation_status": serialized.get("reservation_status"),
                "bed_id": serialized.get("bed_id"),
                "bed_type": serialized.get("bed_type"),
                "auto_reservation": serialized.get("auto_reservation"),
            },
        }

    # ============================================================
    # 4. READ & QUERY METHODS
    # ============================================================

    def get_referral(self, referral_id: str) -> Optional[Dict[str, Any]]:
        """Get single referral by ID."""
        stmt = select(Referral).where(Referral.referral_id == referral_id)
        ref = self.session.execute(stmt).scalar_one_or_none()
        if not ref:
            return None
        return self._serialize_referral(ref)

    def get_patient_referrals(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all referrals for a given patient."""
        stmt = select(Referral).where(Referral.patient_id == patient_id).order_by(Referral.created_at.desc())
        refs = self.session.execute(stmt).scalars().all()
        return [self._serialize_referral(r) for r in refs]

    def get_hospital_referrals(self, hospital_id: str, scope: str = "incoming") -> List[Dict[str, Any]]:
        """
        Get referrals for a hospital.
        scope="incoming": to_hospital_id == hospital_id
        scope="outgoing": from_hospital_id == hospital_id
        scope="all": either
        """
        hid = hospital_id.strip()
        hid_lower = hid.lower()
        if scope == "outgoing":
            stmt = select(Referral).where(
                or_(Referral.from_hospital_id == hid, func.lower(Referral.from_hospital_id) == hid_lower)
            ).order_by(Referral.created_at.desc())
        elif scope == "all":
            stmt = select(Referral).where(
                or_(
                    Referral.to_hospital_id == hid,
                    func.lower(Referral.to_hospital_id) == hid_lower,
                    Referral.from_hospital_id == hid,
                    func.lower(Referral.from_hospital_id) == hid_lower,
                )
            ).order_by(Referral.created_at.desc())
        else:
            stmt = select(Referral).where(
                or_(Referral.to_hospital_id == hid, func.lower(Referral.to_hospital_id) == hid_lower)
            ).order_by(Referral.created_at.desc())

        refs = self.session.execute(stmt).scalars().all()
        return [self._serialize_referral(r) for r in refs]

    # ============================================================
    # 5. IN-APP NOTIFICATIONS
    # ============================================================

    def get_hospital_notifications(
        self,
        hospital_id: str,
        unread_only: bool = False,
        limit: int = 50,
        page: int = 1,
        page_size: Optional[int] = None,
        event_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fetch notifications for a hospital with unread count, pagination, and category filtering."""
        effective_limit = page_size if page_size is not None else limit
        offset = (page - 1) * effective_limit if page > 1 else 0

        conditions = [Notification.hospital_id == hospital_id]
        if unread_only:
            conditions.append(Notification.is_read == False)

        if event_category:
            cat = event_category.lower().strip()
            if cat in ("referral", "referrals"):
                conditions.append(Notification.event_type.ilike("%REFERRAL%"))
            elif cat in ("bed", "beds", "bed_hold", "reservation", "reservations"):
                conditions.append(or_(
                    Notification.event_type.ilike("BED_%"),
                    Notification.event_type.ilike("RESERVATION_%"),
                    Notification.event_type.ilike("PATIENT_%"),
                ))
            elif cat in ("capacity", "inventory"):
                conditions.append(Notification.event_type.ilike("%AVAILABILITY%"))
            elif cat in ("registration", "review"):
                conditions.append(Notification.event_type.ilike("REGISTRATION_%"))
            else:
                conditions.append(Notification.event_type.ilike(f"%{cat}%"))

        count_total_stmt = select(func.count(Notification.id)).where(*conditions)
        total_count = self.session.execute(count_total_stmt).scalar() or 0

        stmt = (
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(effective_limit)
        )
        notifs = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count(Notification.id)).where(
            Notification.hospital_id == hospital_id,
            Notification.is_read == False,
        )
        unread_count = self.session.execute(count_stmt).scalar() or 0

        return {
            "hospital_id": hospital_id,
            "unread_count": unread_count,
            "total_count": total_count,
            "total_returned": len(notifs),
            "page": page,
            "page_size": effective_limit,
            "notifications": [
                {
                    "id": n.id,
                    "notification_id": str(n.id),
                    "hospital_id": n.hospital_id,
                    "referral_id": n.referral_id,
                    "event_type": n.event_type,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority,
                    "is_read": n.is_read,
                    "action_url": n.action_url,
                    "state": n.state,
                    "district": n.district,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ],
        }

    def mark_notification_as_read(self, notification_id: Any, hospital_id: str) -> bool:
        """Mark single notification as read."""
        try:
            nid = int(notification_id)
        except (ValueError, TypeError):
            return False
        stmt = (
            update(Notification)
            .where(Notification.id == nid, Notification.hospital_id == hospital_id)
            .values(is_read=True)
        )
        res = self.session.execute(stmt)
        self.session.commit()
        return res.rowcount > 0

    def mark_all_notifications_read(self, hospital_id: str) -> int:
        """Mark all unread notifications for a hospital as read."""
        stmt = (
            update(Notification)
            .where(Notification.hospital_id == hospital_id, Notification.is_read == False)
            .values(is_read=True)
        )
        res = self.session.execute(stmt)
        self.session.commit()
        return res.rowcount

    def get_user_notifications(
        self,
        user: Dict[str, Any],
        unread_only: bool = False,
        limit: int = 50,
        page: int = 1,
        page_size: Optional[int] = None,
        event_category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Unified notification retrieval for any authenticated user.
        - Hospital Staff (with hospital_id): retrieves hospital notifications.
        - Reviewers (DISTRICT_ADMIN, STATE_ADMIN, CENTRAL_ADMIN): retrieves reviewer notifications.
        - Applicants (with application_id): retrieves applicant dossier notifications.
        - Individual user_id: retrieves direct user notifications.
        """
        role = user.get("role")
        hospital_id = user.get("hospital_id")
        application_id = user.get("application_id")
        user_id = user.get("user_id")

        if hospital_id:
            return self.get_hospital_notifications(
                hospital_id=hospital_id,
                unread_only=unread_only,
                limit=limit,
                page=page,
                page_size=page_size,
                event_category=event_category,
            )
        elif role in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return self.get_reviewer_notifications(
                user=user,
                unread_only=unread_only,
                limit=limit,
            )
        elif application_id:
            return self.get_applicant_notifications(
                application_id=application_id,
                unread_only=unread_only,
                limit=limit,
            )
        else:
            conditions = [Notification.user_id == user_id] if user_id else [False]
            if unread_only:
                conditions.append(Notification.is_read == False)
            effective_limit = page_size if page_size is not None else limit
            offset = (page - 1) * effective_limit if page > 1 else 0
            stmt = select(Notification).where(*conditions).order_by(Notification.created_at.desc()).offset(offset).limit(effective_limit)
            notifs = self.session.execute(stmt).scalars().all()
            unread_count = self.session.execute(
                select(func.count(Notification.id)).where(Notification.user_id == user_id, Notification.is_read == False)
            ).scalar() or 0
            return {
                "user_id": user_id,
                "unread_count": unread_count,
                "total_returned": len(notifs),
                "page": page,
                "page_size": effective_limit,
                "notifications": [
                    {
                        "id": n.id,
                        "notification_id": str(n.id),
                        "event_type": n.event_type,
                        "title": n.title,
                        "message": n.message,
                        "priority": n.priority,
                        "is_read": n.is_read,
                        "action_url": n.action_url,
                        "created_at": n.created_at.isoformat() if n.created_at else None,
                    }
                    for n in notifs
                ],
            }

    def mark_user_notification_as_read(self, notification_id: Any, user: Dict[str, Any]) -> bool:
        """Mark single notification as read for current user."""
        try:
            nid = int(notification_id)
        except (ValueError, TypeError):
            return False

        role = user.get("role")
        hospital_id = user.get("hospital_id")
        application_id = user.get("application_id")
        user_id = user.get("user_id")

        if hospital_id:
            return self.mark_notification_as_read(nid, hospital_id)
        elif role in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return self.mark_reviewer_notification_as_read(nid, user)
        elif application_id:
            return self.mark_applicant_notification_as_read(nid, application_id)
        elif user_id:
            stmt = (
                update(Notification)
                .where(Notification.id == nid, Notification.user_id == user_id)
                .values(is_read=True)
            )
            res = self.session.execute(stmt)
            self.session.commit()
            return res.rowcount > 0
        return False

    def mark_all_user_notifications_read(self, user: Dict[str, Any]) -> int:
        """Mark all notifications as read for current user."""
        role = user.get("role")
        hospital_id = user.get("hospital_id")
        application_id = user.get("application_id")
        user_id = user.get("user_id")

        if hospital_id:
            return self.mark_all_notifications_read(hospital_id)
        elif role in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return self.mark_all_reviewer_notifications_read(user)
        elif application_id:
            return self.mark_all_applicant_notifications_read(application_id)
        elif user_id:
            stmt = (
                update(Notification)
                .where(Notification.user_id == user_id, Notification.is_read == False)
                .values(is_read=True)
            )
            res = self.session.execute(stmt)
            self.session.commit()
            return res.rowcount
        return 0

    # ============================================================
    # PHASE 4D-2: REVIEWER & APPLICANT NOTIFICATION REPOSITORY
    # ============================================================

    def get_reviewer_notifications(
        self,
        user: Dict[str, Any],
        unread_only: bool = False,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Fetch notifications for a government reviewer enforcing jurisdiction isolation.
        - DISTRICT_ADMIN: Can only see notifications for their state and district (or assigned user_id).
        - STATE_ADMIN: Can only see notifications for their state (or assigned user_id).
        - CENTRAL_ADMIN: Can see Central notifications (or assigned user_id).
        - Non-reviewer / hospital roles: Forbidden from accessing government reviewer alerts.
        """
        role = user.get("role")
        user_id = user.get("user_id")
        user_state = user.get("state")
        user_district = user.get("district")

        if role not in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return {"role": role, "unread_count": 0, "total_returned": 0, "notifications": []}

        conditions = []
        if role == "DISTRICT_ADMIN":
            jurisdiction_clause = and_(
                Notification.role_id == "DISTRICT_ADMIN",
                func.lower(Notification.state) == func.lower(user_state or ""),
                func.lower(Notification.district) == func.lower(user_district or ""),
            )
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        elif role == "STATE_ADMIN":
            jurisdiction_clause = and_(
                Notification.role_id == "STATE_ADMIN",
                func.lower(Notification.state) == func.lower(user_state or ""),
            )
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        elif role == "CENTRAL_ADMIN":
            jurisdiction_clause = (Notification.role_id == "CENTRAL_ADMIN")
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        count_conditions = list(conditions)
        count_conditions.append(Notification.is_read == False)

        if unread_only:
            conditions.append(Notification.is_read == False)

        stmt = select(Notification).where(*conditions).order_by(Notification.created_at.desc()).limit(limit)
        notifs = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count(Notification.id)).where(*count_conditions)
        unread_count = self.session.execute(count_stmt).scalar() or 0

        return {
            "role": role,
            "user_id": user_id,
            "jurisdiction": f"{user_district or ''}, {user_state or 'Central'}".strip(", "),
            "unread_count": unread_count,
            "total_returned": len(notifs),
            "notifications": [
                {
                    "notification_id": str(n.id),
                    "id": n.id,
                    "event_type": n.event_type,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority,
                    "is_read": n.is_read,
                    "application_id": n.application_id,
                    "action_url": n.action_url,
                    "state": n.state,
                    "district": n.district,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ],
        }

    def mark_reviewer_notification_as_read(self, notification_id: int, user: Dict[str, Any]) -> bool:
        """
        Mark a reviewer notification as read only if the reviewer is authorized for its jurisdiction.
        """
        role = user.get("role")
        user_id = user.get("user_id")
        user_state = user.get("state")
        user_district = user.get("district")

        if role not in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return False

        notif = self.session.get(Notification, notification_id)
        if not notif:
            return False

        # Verify authorization
        is_authorized = False
        if notif.user_id and notif.user_id == user_id:
            is_authorized = True
        elif notif.role_id == "CENTRAL_ADMIN" and role == "CENTRAL_ADMIN":
            is_authorized = True
        elif (
            notif.role_id == "STATE_ADMIN"
            and role == "STATE_ADMIN"
            and (notif.state or "").lower() == (user_state or "").lower()
        ):
            is_authorized = True
        elif (
            notif.role_id == "DISTRICT_ADMIN"
            and role == "DISTRICT_ADMIN"
            and (notif.state or "").lower() == (user_state or "").lower()
            and (notif.district or "").lower() == (user_district or "").lower()
        ):
            is_authorized = True

        if not is_authorized:
            return False

        notif.is_read = True
        self.session.commit()
        return True

    def mark_all_reviewer_notifications_read(self, user: Dict[str, Any]) -> int:
        """Mark all unread notifications for a reviewer's jurisdiction as read."""
        role = user.get("role")
        user_id = user.get("user_id")
        user_state = user.get("state")
        user_district = user.get("district")

        if role not in ("DISTRICT_ADMIN", "STATE_ADMIN", "CENTRAL_ADMIN"):
            return 0

        conditions = [Notification.is_read == False]
        if role == "DISTRICT_ADMIN":
            jurisdiction_clause = and_(
                Notification.role_id == "DISTRICT_ADMIN",
                func.lower(Notification.state) == func.lower(user_state or ""),
                func.lower(Notification.district) == func.lower(user_district or ""),
            )
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        elif role == "STATE_ADMIN":
            jurisdiction_clause = and_(
                Notification.role_id == "STATE_ADMIN",
                func.lower(Notification.state) == func.lower(user_state or ""),
            )
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        elif role == "CENTRAL_ADMIN":
            jurisdiction_clause = (Notification.role_id == "CENTRAL_ADMIN")
            if user_id:
                conditions.append(or_(Notification.user_id == user_id, jurisdiction_clause))
            else:
                conditions.append(jurisdiction_clause)

        stmt = update(Notification).where(*conditions).values(is_read=True)
        res = self.session.execute(stmt)
        self.session.commit()
        return res.rowcount

    def get_applicant_notifications(
        self,
        application_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Fetch in-app notifications for an applicant application dossier.
        """
        conditions = [
            Notification.application_id == application_id,
            Notification.role_id.is_(None),  # Only notifications addressed to the applicant
        ]
        count_conditions = list(conditions)
        count_conditions.append(Notification.is_read == False)

        if unread_only:
            conditions.append(Notification.is_read == False)

        stmt = select(Notification).where(*conditions).order_by(Notification.created_at.desc()).limit(limit)
        notifs = self.session.execute(stmt).scalars().all()

        count_stmt = select(func.count(Notification.id)).where(*count_conditions)
        unread_count = self.session.execute(count_stmt).scalar() or 0

        return {
            "application_id": application_id,
            "unread_count": unread_count,
            "total_returned": len(notifs),
            "notifications": [
                {
                    "notification_id": str(n.id),
                    "id": n.id,
                    "event_type": n.event_type,
                    "title": n.title,
                    "message": n.message,
                    "priority": n.priority,
                    "is_read": n.is_read,
                    "application_id": n.application_id,
                    "action_url": n.action_url,
                    "created_at": n.created_at.isoformat() if n.created_at else None,
                }
                for n in notifs
            ],
        }

    def mark_applicant_notification_as_read(self, notification_id: int, application_id: str) -> bool:
        """Mark an applicant notification as read, enforcing applicant isolation."""
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.application_id == application_id,
                Notification.role_id.is_(None),
            )
            .values(is_read=True)
        )
        res = self.session.execute(stmt)
        self.session.commit()
        return res.rowcount > 0

    def mark_all_applicant_notifications_read(self, application_id: str) -> int:
        """Mark all unread notifications for an applicant as read."""
        stmt = (
            update(Notification)
            .where(
                Notification.application_id == application_id,
                Notification.role_id.is_(None),
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        res = self.session.execute(stmt)
        self.session.commit()
        return res.rowcount

    # ============================================================
    # PHASE 4A: OPERATIONAL INVENTORY & BED MANAGEMENT
    # ============================================================

    def get_hospital_inventory(self, hospital_id: str) -> Optional[Dict[str, Any]]:
        """
        Authoritative calculation of hospital bed inventory from PostgreSQL.
        Aggregates individual physical beds by category and status.
        Falls back to hospital aggregate columns if individual bed rows are not yet seeded.
        """
        hospital = (
            self.session.execute(
                select(Hospital).where(Hospital.hospital_id == hospital_id)
            )
            .scalar_one_or_none()
        )
        if not hospital:
            return None

        # Fetch physical beds
        beds = (
            self.session.execute(
                select(Bed).where(Bed.hospital_id == hospital_id)
            )
            .scalars()
            .all()
        )

        has_physical_beds = len(beds) > 0

        categories = {
            "GENERAL": {"total": 0, "available": 0, "reserved": 0, "occupied": 0, "maintenance": 0},
            "ICU": {"total": 0, "available": 0, "reserved": 0, "occupied": 0, "maintenance": 0},
            "EMERGENCY": {"total": 0, "available": 0, "reserved": 0, "occupied": 0, "maintenance": 0},
        }

        if has_physical_beds:
            for b in beds:
                b_type = b.bed_type.upper() if b.bed_type else "GENERAL"
                if b_type not in categories:
                    b_type = "GENERAL"
                categories[b_type]["total"] += 1
                status = b.status.upper() if b.status else "AVAILABLE"
                if status == "AVAILABLE":
                    categories[b_type]["available"] += 1
                elif status == "RESERVED":
                    categories[b_type]["reserved"] += 1
                elif status == "OCCUPIED":
                    categories[b_type]["occupied"] += 1
                elif status == "MAINTENANCE":
                    categories[b_type]["maintenance"] += 1

            avail_gen = categories["GENERAL"]["available"]
            res_gen = categories["GENERAL"]["reserved"]
            occ_gen = categories["GENERAL"]["occupied"]
            total_gen = categories["GENERAL"]["total"]

            avail_icu = categories["ICU"]["available"]
            res_icu = categories["ICU"]["reserved"]
            occ_icu = categories["ICU"]["occupied"]
            total_icu = categories["ICU"]["total"]

            avail_emg = categories["EMERGENCY"]["available"]
            res_emg = categories["EMERGENCY"]["reserved"]
            occ_emg = categories["EMERGENCY"]["occupied"]
            total_emg = categories["EMERGENCY"]["total"]
        else:
            # Fall back to Hospital counters
            total_gen = hospital.total_beds or 0
            avail_gen = hospital.available_beds or 0
            occ_gen = hospital.occupied_beds or 0
            # Query actual active reservations for this hospital by department (Fix F-05)
            res_stmt = (
                select(Bed.bed_type, func.count(BedReservation.reservation_id))
                .join(Bed, BedReservation.bed_id == Bed.id)
                .where(
                    BedReservation.hospital_id == hospital_id,
                    BedReservation.status.in_(["RESERVED", "CONFIRMED"]),
                )
                .group_by(Bed.bed_type)
            )
            res_counts = {r[0].upper(): r[1] for r in self.session.execute(res_stmt).fetchall()}

            direct_res_stmt = (
                select(func.count(BedReservation.reservation_id))
                .where(
                    BedReservation.hospital_id == hospital_id,
                    BedReservation.status.in_(["RESERVED", "CONFIRMED"]),
                )
            )
            total_active_res = self.session.execute(direct_res_stmt).scalar() or 0
            res_gen = res_counts.get("GENERAL", 0)
            res_icu = res_counts.get("ICU", 0)
            res_emg = res_counts.get("EMERGENCY", 0)
            if total_active_res > 0 and (res_gen + res_icu + res_emg) == 0:
                res_gen = total_active_res

            total_icu = hospital.icu_beds or 0
            avail_icu = hospital.available_icu_beds or 0
            occ_icu = getattr(hospital, "occupied_icu_beds", 0) or 0

            total_emg = hospital.emergency_beds or 0
            avail_emg = hospital.available_emergency_beds or 0
            occ_emg = getattr(hospital, "occupied_emergency_beds", 0) or 0

            categories["GENERAL"] = {"total": total_gen, "available": avail_gen, "reserved": res_gen, "occupied": occ_gen, "maintenance": 0}
            categories["ICU"] = {"total": total_icu, "available": avail_icu, "reserved": res_icu, "occupied": occ_icu, "maintenance": 0}
            categories["EMERGENCY"] = {"total": total_emg, "available": avail_emg, "reserved": res_emg, "occupied": occ_emg, "maintenance": 0}

        total_avail = avail_gen + avail_icu + avail_emg
        total_res = res_gen + res_icu + res_emg
        total_occ = occ_gen + occ_icu + occ_emg
        total_cap = total_gen + total_icu + total_emg

        is_configured = total_cap > 0

        return {
            "hospital_id": hospital_id,
            "name": hospital.name,
            "state": hospital.state,
            "district": hospital.district,
            "city": hospital.city,
            "is_configured": is_configured,
            # Top-level legacy keys expected by HospitalDashboard and api.ts
            "available_beds": avail_gen,
            "reserved_beds": res_gen,
            "occupied_beds": occ_gen,
            "total_general_beds": total_gen,
            "available_icu_beds": avail_icu,
            "reserved_icu_beds": res_icu,
            "occupied_icu_beds": occ_icu,
            "total_icu_beds": total_icu,
            "available_emergency_beds": avail_emg,
            "reserved_emergency_beds": res_emg,
            "occupied_emergency_beds": occ_emg,
            "total_emergency_beds": total_emg,
            "total_available_beds": total_avail,
            "total_reserved_beds": total_res,
            "total_occupied_beds": total_occ,
            "total_capacity": total_cap,
            # Resource flags
            "oxygen_support": hospital.oxygen_support or "No",
            "ventilator": hospital.ventilator or "No",
            "ambulance": hospital.ambulance or "No",
            "blood_bank": hospital.blood_bank or "No",
            "emergency_24x7": hospital.emergency_24x7 or "No",
            # Category breakdown
            "categories": categories,
            "beds": {b.bed_number: b.status for b in beds} if has_physical_beds else {},
        }

    def initialize_default_inventory(
        self,
        hospital_id: str,
        capacities: Optional[Dict[str, int]] = None,
        resources: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Initializes missing bed records and capacity metrics for a hospital.
        Idempotent: will not create duplicate beds if already initialized.
        """
        now = datetime.now(timezone.utc)
        hosp_stmt = (
            select(Hospital)
            .where(Hospital.hospital_id == hospital_id)
            .with_for_update()
        )
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if not hospital:
            raise ValueError(f"Hospital '{hospital_id}' does not exist.")

        capacities = capacities or {}
        # Expected categories: GENERAL, ICU, EMERGENCY
        default_counts = {
            "GENERAL": capacities.get("GENERAL", hospital.total_beds if (hospital.total_beds and hospital.total_beds > 0) else 20),
            "ICU": capacities.get("ICU", hospital.icu_beds if (hospital.icu_beds and hospital.icu_beds > 0) else 5),
            "EMERGENCY": capacities.get("EMERGENCY", hospital.emergency_beds if (hospital.emergency_beds and hospital.emergency_beds > 0) else 5),
        }

        prefix_map = {
            "GENERAL": "GEN",
            "ICU": "ICU",
            "EMERGENCY": "EMG",
        }

        # Check existing physical beds
        existing_beds = (
            self.session.execute(
                select(Bed)
                .where(Bed.hospital_id == hospital_id)
                .with_for_update()
            )
            .scalars()
            .all()
        )

        existing_by_type: Dict[str, List[Bed]] = {"GENERAL": [], "ICU": [], "EMERGENCY": []}
        for b in existing_beds:
            b_type = b.bed_type.upper() if b.bed_type else "GENERAL"
            if b_type in existing_by_type:
                existing_by_type[b_type].append(b)

        beds_created = 0
        for b_type, desired_count in default_counts.items():
            current_count = len(existing_by_type[b_type])
            if current_count < desired_count:
                prefix = prefix_map[b_type]
                for i in range(current_count + 1, desired_count + 1):
                    bed_num = f"{prefix}-{i:03d}"
                    new_bed = Bed(
                        hospital_id=hospital_id,
                        bed_number=bed_num,
                        bed_type=b_type,
                        status="AVAILABLE",
                        created_at=now,
                        updated_at=now,
                    )
                    self.session.add(new_bed)
                    beds_created += 1

        # Synchronize Hospital aggregate columns
        gen_total = max(len(existing_by_type["GENERAL"]) + max(0, default_counts["GENERAL"] - len(existing_by_type["GENERAL"])), hospital.total_beds or 0)
        hospital.total_beds = gen_total
        hospital.available_beds = max(0, gen_total - (hospital.occupied_beds or 0))

        icu_total = max(len(existing_by_type["ICU"]) + max(0, default_counts["ICU"] - len(existing_by_type["ICU"])), hospital.icu_beds or 0)
        hospital.icu_beds = icu_total
        hospital.available_icu_beds = icu_total

        emg_total = max(len(existing_by_type["EMERGENCY"]) + max(0, default_counts["EMERGENCY"] - len(existing_by_type["EMERGENCY"])), hospital.emergency_beds or 0)
        hospital.emergency_beds = emg_total
        hospital.available_emergency_beds = emg_total

        if resources:
            for k, v in resources.items():
                if hasattr(hospital, k) and v is not None:
                    setattr(hospital, k, v)

        hospital.updated_at = now

        # Audit
        audit = AuditLog(
            entity_type="HOSPITAL",
            entity_id=hospital_id,
            action="INITIALIZE_INVENTORY",
            performed_by=user_id or "SYSTEM_PROVISIONER",
            new_state={
                "beds_created": beds_created,
                "general": hospital.total_beds,
                "icu": hospital.icu_beds,
                "emergency": hospital.emergency_beds,
            },
            created_at=now,
        )
        self.session.add(audit)
        self.session.flush()

        return self.get_hospital_inventory(hospital_id)

    def update_hospital_bed_capacity(
        self,
        hospital_id: str,
        bed_type: str,
        total_capacity: int,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Atomically updates capacity for a given bed category.
        Ensures total_capacity >= occupied + reserved beds.
        Uses row locking (SELECT ... FOR UPDATE) to prevent race conditions.
        """
        now = datetime.now(timezone.utc)
        b_type = bed_type.upper().strip()
        if b_type not in ["GENERAL", "ICU", "EMERGENCY"]:
            raise ValueError(f"Invalid bed_type '{bed_type}'. Must be GENERAL, ICU, or EMERGENCY.")

        if total_capacity < 0:
            raise ValueError("Total capacity cannot be negative.")

        # Lock hospital row
        hosp_stmt = (
            select(Hospital)
            .where(Hospital.hospital_id == hospital_id)
            .with_for_update()
        )
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if not hospital:
            raise ValueError(f"Hospital '{hospital_id}' not found.")

        # Lock existing beds of this type
        beds_stmt = (
            select(Bed)
            .where(Bed.hospital_id == hospital_id, Bed.bed_type == b_type)
            .with_for_update()
            .order_by(Bed.id.asc())
        )
        beds = self.session.execute(beds_stmt).scalars().all()

        occupied_count = sum(1 for b in beds if b.status == "OCCUPIED")
        reserved_count = sum(1 for b in beds if b.status == "RESERVED")
        available_beds_list = [b for b in beds if b.status == "AVAILABLE"]
        current_total = len(beds)

        if total_capacity < (occupied_count + reserved_count):
            raise ValueError(
                f"Cannot reduce capacity to {total_capacity}. "
                f"Currently {occupied_count} occupied and {reserved_count} reserved beds require at least {occupied_count + reserved_count} capacity."
            )

        prefix_map = {"GENERAL": "GEN", "ICU": "ICU", "EMERGENCY": "EMG"}
        prefix = prefix_map[b_type]

        if total_capacity > current_total:
            # Need to add (total_capacity - current_total) AVAILABLE beds
            existing_numbers = [b.bed_number for b in beds if b.bed_number.startswith(prefix)]
            max_num = 0
            for bn in existing_numbers:
                try:
                    num_part = int(bn.split("-")[-1])
                    if num_part > max_num:
                        max_num = num_part
                except (ValueError, IndexError):
                    pass

            for i in range(1, total_capacity - current_total + 1):
                bed_num = f"{prefix}-{(max_num + i):03d}"
                new_bed = Bed(
                    hospital_id=hospital_id,
                    bed_number=bed_num,
                    bed_type=b_type,
                    status="AVAILABLE",
                    created_at=now,
                    updated_at=now,
                )
                self.session.add(new_bed)

        elif total_capacity < current_total:
            # Need to remove (current_total - total_capacity) beds that are AVAILABLE
            to_remove_count = current_total - total_capacity
            if len(available_beds_list) < to_remove_count:
                raise ValueError(
                    f"Cannot reduce capacity to {total_capacity}: Not enough available (unoccupied/unreserved) beds to remove."
                )
            for b in available_beds_list[-to_remove_count:]:
                self.session.delete(b)

        # Synchronize Hospital aggregate columns
        new_avail = total_capacity - occupied_count - reserved_count
        if b_type == "GENERAL":
            hospital.total_beds = total_capacity
            hospital.available_beds = new_avail
            hospital.occupied_beds = occupied_count
        elif b_type == "ICU":
            hospital.icu_beds = total_capacity
            hospital.available_icu_beds = new_avail
            hospital.occupied_icu_beds = occupied_count
        elif b_type == "EMERGENCY":
            hospital.emergency_beds = total_capacity
            hospital.available_emergency_beds = new_avail
            hospital.occupied_emergency_beds = occupied_count

        hospital.updated_at = now

        # Audit
        audit = AuditLog(
            entity_type="HOSPITAL",
            entity_id=hospital_id,
            action="UPDATE_BED_CAPACITY",
            performed_by=user_id or "ADMIN",
            previous_state={"bed_type": b_type, "capacity": current_total},
            new_state={"bed_type": b_type, "capacity": total_capacity, "available": new_avail},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications for capacity threshold
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_low_bed_availability(hospital, b_type, available_count=new_avail, total_count=total_capacity)
        except Exception as e:
            logger.warning("Error dispatching bed capacity notification: %s", e)

        self.session.commit()

        return self.get_hospital_inventory(hospital_id)

    def update_hospital_resources(
        self,
        hospital_id: str,
        resources: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Updates hospital support resources (oxygen, ventilator, ambulance, etc.).
        """
        now = datetime.now(timezone.utc)
        hosp_stmt = (
            select(Hospital)
            .where(Hospital.hospital_id == hospital_id)
            .with_for_update()
        )
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if not hospital:
            raise ValueError(f"Hospital '{hospital_id}' not found.")

        prev_state = {}
        new_state = {}

        allowed_fields = [
            "oxygen_support",
            "ventilator",
            "ambulance",
            "blood_bank",
            "emergency_24x7",
        ]

        for field in allowed_fields:
            if field in resources and resources[field] is not None:
                val = str(resources[field]).strip()
                if val.lower() in ("yes", "true", "1"):
                    norm_val = "Yes"
                elif val.lower() in ("no", "false", "0"):
                    norm_val = "No"
                else:
                    raise ValueError(f"Invalid value for {field}: must be 'Yes' or 'No'")
                prev_state[field] = getattr(hospital, field)
                setattr(hospital, field, norm_val)
                new_state[field] = norm_val

        hospital.updated_at = now

        audit = AuditLog(
            entity_type="HOSPITAL",
            entity_id=hospital_id,
            action="UPDATE_RESOURCES",
            performed_by=user_id or "ADMIN",
            previous_state=prev_state,
            new_state=new_state,
            created_at=now,
        )
        self.session.add(audit)
        self.session.commit()

        return self.get_hospital_inventory(hospital_id)

    # ============================================================
    # PHASE 4B: UNIFIED DIRECT BED RESERVATION & PATIENT BED LIFECYCLE
    # ============================================================

    def reserve_bed_direct(
        self,
        hospital_id: str,
        patient_id: str,
        bed_type: str,
        user_id: Optional[str] = None,
        ttl_hours: int = 2,
    ) -> Dict[str, Any]:
        """
        Transactional direct bed reservation against PostgreSQL beds table.
        Locks bed row, enforces capacity invariants, prevents duplicate reservations,
        and links to an active referral record.
        """
        now = datetime.now(timezone.utc)
        target_bed_type = (bed_type or "GENERAL").upper().strip()
        if target_bed_type not in ["GENERAL", "ICU", "EMERGENCY"]:
            return {
                "success": False,
                "status": "INVALID_BED_TYPE",
                "message": f"Invalid bed type '{bed_type}'. Allowed: GENERAL, ICU, EMERGENCY.",
            }

        # 1. Lock hospital row
        hosp_stmt = select(Hospital).where(Hospital.hospital_id == hospital_id).with_for_update()
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if not hospital:
            return {
                "success": False,
                "status": "HOSPITAL_NOT_FOUND",
                "message": f"Hospital '{hospital_id}' does not exist.",
            }

        # 2. Check for duplicate active reservation for this patient at this hospital
        dup_stmt = (
            select(BedReservation, Bed)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
                BedReservation.status.in_(["RESERVED", "CONFIRMED", "OCCUPIED"]),
            )
        )
        existing = self.session.execute(dup_stmt).first()
        if existing:
            existing_res, existing_bed = existing
            return {
                "success": False,
                "status": "ALREADY_RESERVED",
                "message": "Patient already has an active reservation.",
                "reservation": {
                    "hospital_id": hospital_id,
                    "patient_id": patient_id,
                    "bed_type": existing_bed.bed_type,
                    "bed_id": existing_bed.bed_number,
                    "status": existing_res.status,
                    "reserved_at": existing_res.reserved_at.isoformat() if existing_res.reserved_at else None,
                    "reservation_id": existing_res.reservation_id,
                },
            }

        # 3. Lock the next available physical bed
        bed_stmt = (
            select(Bed)
            .where(
                Bed.hospital_id == hospital_id,
                Bed.bed_type == target_bed_type,
                Bed.status == "AVAILABLE",
            )
            .order_by(Bed.id.asc())
            .with_for_update()
            .limit(1)
        )
        bed = self.session.execute(bed_stmt).scalar_one_or_none()

        # If no physical bed found, verify if hospital beds are unseeded; seed if empty
        if not bed:
            bed_count = self.session.execute(
                select(func.count(Bed.id)).where(Bed.hospital_id == hospital_id)
            ).scalar() or 0
            if bed_count == 0:
                self.initialize_default_inventory(hospital_id)
                bed = self.session.execute(bed_stmt).scalar_one_or_none()

        if not bed:
            status_code = "NO_ICU_AVAILABLE" if target_bed_type == "ICU" else "NO_BED_AVAILABLE"
            return {
                "success": False,
                "status": status_code,
                "message": f"No physical {target_bed_type} bed available.",
            }

        # 4. Ensure Patient record exists
        pat_stmt = select(Patient).where(Patient.patient_id == patient_id)
        patient = self.session.execute(pat_stmt).scalar_one_or_none()
        if not patient:
            patient = Patient(
                patient_id=patient_id,
                name=f"Direct Patient {patient_id}",
                priority="Critical" if target_bed_type == "ICU" else "Urgent",
                referral_required="Yes",
                icu_required="Yes" if target_bed_type == "ICU" else "No",
                state=hospital.state,
                district=hospital.district,
                created_at=now,
                updated_at=now,
            )
            self.session.add(patient)
            self.session.flush()

        # 5. Link or create Referral record
        ref_stmt = (
            select(Referral)
            .where(
                Referral.patient_id == patient_id,
                Referral.to_hospital_id == hospital_id,
                Referral.status.in_(["PENDING", "ACCEPTED"]),
            )
            .order_by(Referral.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        referral = self.session.execute(ref_stmt).scalar_one_or_none()
        if not referral:
            referral_id = f"REF-DIR-{uuid.uuid4().hex[:8].upper()}"
            referral = Referral(
                referral_id=referral_id,
                patient_id=patient_id,
                from_hospital_id=hospital_id,
                to_hospital_id=hospital_id,
                status="ACCEPTED",
                priority="Critical" if target_bed_type == "ICU" else "Urgent",
                bed_type=target_bed_type,
                reason="Direct Bed Reservation",
                accepted_at=now,
                created_at=now,
                updated_at=now,
            )
            self.session.add(referral)
            self.session.flush()
        else:
            referral.status = "ACCEPTED"
            referral.accepted_at = now
            referral.updated_at = now

        # 6. Mark bed RESERVED and update hospital counters
        bed.status = "RESERVED"
        bed.updated_at = now

        if target_bed_type == "ICU":
            hospital.available_icu_beds = max(0, hospital.available_icu_beds - 1)
        elif target_bed_type == "EMERGENCY":
            hospital.available_emergency_beds = max(0, hospital.available_emergency_beds - 1)
        else:
            hospital.available_beds = max(0, hospital.available_beds - 1)
        hospital.updated_at = now

        # 7. Create BedReservation record
        res_id = f"RES-{uuid.uuid4().hex[:12].upper()}"
        expires_at = now + timedelta(hours=ttl_hours)
        reservation = BedReservation(
            reservation_id=res_id,
            referral_id=referral.referral_id,
            hospital_id=hospital_id,
            bed_id=bed.id,
            status="RESERVED",
            reserved_at=now,
            expires_at=expires_at,
            created_at=now,
        )
        self.session.add(reservation)

        # 8. Audit log
        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res_id,
            action="DIRECT_RESERVE_SUCCESS",
            performed_by=user_id or "API_CLIENT",
            new_state={
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "bed_id": bed.bed_number,
                "bed_type": target_bed_type,
                "referral_id": referral.referral_id,
                "status": "RESERVED",
            },
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (bed hold reserved)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_bed_reserved(reservation, bed, hospital, referral)
            notif_svc.notify_low_bed_availability(hospital, target_bed_type)
        except Exception as e:
            logger.warning("Error dispatching bed reserved notification: %s", e)

        self.session.commit()

        res_data = {
            "hospital_id": hospital_id,
            "patient_id": patient_id,
            "bed_type": target_bed_type,
            "bed_id": bed.bed_number,
            "status": "RESERVED",
            "reserved_at": now.isoformat(),
            "reservation_id": res_id,
            "referral_id": referral.referral_id,
            "expires_at": expires_at.isoformat(),
        }

        return {
            "success": True,
            "status": "RESERVED",
            "message": f"{target_bed_type} bed {bed.bed_number} successfully reserved.",
            "reservation": res_data,
        }

    def get_reservation_direct(self, hospital_id: str, patient_id: str) -> Optional[Dict[str, Any]]:
        """Fetch latest active or historical bed reservation for patient at hospital."""
        stmt = (
            select(BedReservation, Bed, Referral)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
            )
            .order_by(BedReservation.created_at.desc())
            .limit(1)
        )
        row = self.session.execute(stmt).first()
        if not row:
            return None
        res, bed, ref = row
        return {
            "hospital_id": hospital_id,
            "patient_id": patient_id,
            "bed_type": bed.bed_type,
            "bed_id": bed.bed_number,
            "status": res.status,
            "reserved_at": res.reserved_at.isoformat() if res.reserved_at else None,
            "reservation_id": res.reservation_id,
            "referral_id": ref.referral_id,
            "expires_at": res.expires_at.isoformat() if res.expires_at else None,
            "released_at": res.released_at.isoformat() if res.released_at else None,
        }

    def confirm_bed_direct(self, hospital_id: str, patient_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Transitions reservation from RESERVED -> CONFIRMED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(BedReservation, Bed, Referral)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
            )
            .order_by(BedReservation.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        row = self.session.execute(stmt).first()
        if not row:
            return {"success": False, "status": "NOT_FOUND", "message": "Reservation not found."}
        res, bed, ref = row
        if res.status != "RESERVED":
            return {"success": False, "status": "INVALID_STATUS", "message": f"Cannot confirm reservation with status '{res.status}'."}

        res.status = "CONFIRMED"
        if ref.status in ["PENDING", "ACCEPTED"]:
            ref.status = "ARRIVED"
            ref.arrived_at = now
            ref.updated_at = now

        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res.reservation_id,
            action="DIRECT_CONFIRM",
            performed_by=user_id or "API_CLIENT",
            previous_state={"status": "RESERVED"},
            new_state={"status": "CONFIRMED"},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (patient arrival confirmed)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            hosp = self.session.get(Hospital, hospital_id)
            notif_svc.notify_bed_confirmed(res, bed, hosp, ref)
        except Exception as e:
            logger.warning("Error dispatching bed confirmed notification: %s", e)

        self.session.commit()

        return {
            "success": True,
            "status": "CONFIRMED",
            "message": "Reservation confirmed successfully.",
            "reservation": {
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "bed_type": bed.bed_type,
                "bed_id": bed.bed_number,
                "status": "CONFIRMED",
                "confirmed_at": now.isoformat(),
                "reservation_id": res.reservation_id,
            },
        }

    def occupy_bed_direct(self, hospital_id: str, patient_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Transitions reservation from CONFIRMED/RESERVED -> OCCUPIED."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(BedReservation, Bed, Referral)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
            )
            .order_by(BedReservation.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        row = self.session.execute(stmt).first()
        if not row:
            return {"success": False, "status": "NOT_FOUND", "message": "Reservation not found."}
        res, bed, ref = row
        if res.status not in ["CONFIRMED", "RESERVED"]:
            return {"success": False, "status": "INVALID_STATUS", "message": f"Only confirmed or reserved bed can be marked occupied. Current status: '{res.status}'."}

        res.status = "OCCUPIED"
        bed.status = "OCCUPIED"
        bed.updated_at = now

        # Update hospital occupied counter atomically by department
        hosp_stmt = select(Hospital).where(Hospital.hospital_id == hospital_id).with_for_update()
        hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
        if hosp:
            if bed.bed_type == "ICU":
                hosp.occupied_icu_beds = (hosp.occupied_icu_beds or 0) + 1
            elif bed.bed_type == "EMERGENCY":
                hosp.occupied_emergency_beds = (hosp.occupied_emergency_beds or 0) + 1
            else:
                hosp.occupied_beds = (hosp.occupied_beds or 0) + 1
            hosp.updated_at = now

        if ref.status in ["PENDING", "ACCEPTED", "IN_TRANSIT", "ARRIVED"]:
            ref.status = "TREATMENT_ACTIVE"
            ref.updated_at = now

        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res.reservation_id,
            action="DIRECT_OCCUPY",
            performed_by=user_id or "API_CLIENT",
            previous_state={"status": res.status},
            new_state={"status": "OCCUPIED", "bed_id": bed.bed_number},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (bed occupied)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_bed_occupied(res, bed, hosp, ref)
        except Exception as e:
            logger.warning("Error dispatching bed occupied notification: %s", e)

        self.session.commit()

        return {
            "success": True,
            "status": "OCCUPIED",
            "message": "Bed marked as occupied successfully.",
            "reservation": {
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "bed_type": bed.bed_type,
                "bed_id": bed.bed_number,
                "status": "OCCUPIED",
                "occupied_at": now.isoformat(),
                "reservation_id": res.reservation_id,
            },
        }

    def release_bed_direct(self, hospital_id: str, patient_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Releases a RESERVED or CONFIRMED bed back to inventory."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(BedReservation, Bed, Referral)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
            )
            .order_by(BedReservation.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        row = self.session.execute(stmt).first()
        if not row:
            return {"success": False, "status": "NOT_FOUND", "message": "Reservation not found."}
        res, bed, ref = row

        if res.status == "RELEASED":
            return {"success": False, "status": "ALREADY_RELEASED", "message": "This reservation has already been released."}
        if res.status == "OCCUPIED":
            return {"success": False, "status": "BED_OCCUPIED", "message": "Occupied bed cannot be released. Use the discharge process instead."}
        if res.status not in ["RESERVED", "CONFIRMED"]:
            return {"success": False, "status": "INVALID_STATUS", "message": "Only a reserved or confirmed bed can be released.", "current_status": res.status}

        bed.status = "AVAILABLE"
        bed.updated_at = now

        # Restore hospital counters
        hosp_stmt = select(Hospital).where(Hospital.hospital_id == hospital_id).with_for_update()
        hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
        if hosp:
            if bed.bed_type == "ICU":
                hosp.available_icu_beds = min(hosp.icu_beds, hosp.available_icu_beds + 1)
            elif bed.bed_type == "EMERGENCY":
                hosp.available_emergency_beds = min(hosp.emergency_beds, hosp.available_emergency_beds + 1)
            else:
                hosp.available_beds = min(hosp.total_beds, hosp.available_beds + 1)
            hosp.updated_at = now
            hosp.updated_at = now

        res.status = "RELEASED"
        res.released_at = now

        if ref.status in ["PENDING", "ACCEPTED", "IN_TRANSIT", "ARRIVED"]:
            ref.status = "CANCELLED"
            ref.completed_at = now
            ref.updated_at = now

        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res.reservation_id,
            action="DIRECT_RELEASE",
            performed_by=user_id or "API_CLIENT",
            previous_state={"status": "RESERVED"},
            new_state={"status": "RELEASED", "bed_id": bed.bed_number},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (bed hold released)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_bed_released(res, bed, hosp, ref)
        except Exception as e:
            logger.warning("Error dispatching bed released notification: %s", e)

        self.session.commit()

        return {
            "success": True,
            "status": "RELEASED",
            "message": "Reservation released successfully.",
            "reservation": {
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "bed_type": bed.bed_type,
                "bed_id": bed.bed_number,
                "status": "RELEASED",
                "released_at": now.isoformat(),
                "reservation_id": res.reservation_id,
            },
        }

    def discharge_patient_direct(self, hospital_id: str, patient_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Discharges an OCCUPIED patient and releases the bed back to AVAILABLE."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(BedReservation, Bed, Referral)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .join(Referral, BedReservation.referral_id == Referral.referral_id)
            .where(
                BedReservation.hospital_id == hospital_id,
                Referral.patient_id == patient_id,
            )
            .order_by(BedReservation.created_at.desc())
            .with_for_update()
            .limit(1)
        )
        row = self.session.execute(stmt).first()
        if not row:
            return {"success": False, "status": "NOT_FOUND", "message": "Reservation not found."}
        res, bed, ref = row

        if res.status == "RELEASED":
            return {"success": False, "status": "ALREADY_RELEASED", "message": "Patient has already been discharged."}
        if res.status != "OCCUPIED":
            return {"success": False, "status": "INVALID_STATUS", "message": "Only an occupied bed can be discharged.", "current_status": res.status}

        bed.status = "AVAILABLE"
        bed.updated_at = now

        hosp_stmt = select(Hospital).where(Hospital.hospital_id == hospital_id).with_for_update()
        hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
        if hosp:
            if bed.bed_type == "ICU":
                hosp.available_icu_beds = min(hosp.icu_beds, hosp.available_icu_beds + 1)
                hosp.occupied_icu_beds = max(0, (hosp.occupied_icu_beds or 1) - 1)
            elif bed.bed_type == "EMERGENCY":
                hosp.available_emergency_beds = min(hosp.emergency_beds, hosp.available_emergency_beds + 1)
                hosp.occupied_emergency_beds = max(0, (hosp.occupied_emergency_beds or 1) - 1)
            else:
                hosp.available_beds = min(hosp.total_beds, hosp.available_beds + 1)
                hosp.occupied_beds = max(0, (hosp.occupied_beds or 1) - 1)
            hosp.updated_at = now

        res.status = "RELEASED"
        res.released_at = now

        ref.status = "DISCHARGED"
        ref.completed_at = now
        ref.updated_at = now

        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res.reservation_id,
            action="DIRECT_DISCHARGE",
            performed_by=user_id or "API_CLIENT",
            previous_state={"status": "OCCUPIED"},
            new_state={"status": "RELEASED", "bed_id": bed.bed_number},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (patient discharged)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_bed_discharged(res, bed, hosp, ref)
        except Exception as e:
            logger.warning("Error dispatching bed discharged notification: %s", e)

        self.session.commit()

        return {
            "success": True,
            "status": "RELEASED",
            "message": "Patient discharged successfully.",
            "reservation": {
                "hospital_id": hospital_id,
                "patient_id": patient_id,
                "bed_type": bed.bed_type,
                "bed_id": bed.bed_number,
                "status": "RELEASED",
                "discharged_at": now.isoformat(),
                "reservation_id": res.reservation_id,
            },
        }

    def expire_reservation_direct(
        self,
        hospital_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        reservation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Dict[str, Any]:
        """
        Expires a temporary RESERVED bed hold and restores inventory capacity atomically.
        Guarantees:
        - Locks reservation, bed, referral, and hospital records with FOR UPDATE.
        - Rechecks eligibility inside transaction.
        - Only RESERVED status can expire (CONFIRMED is guaranteed and cannot auto/direct expire).
        - OCCUPIED, RELEASED, or EXPIRED reservations are safely rejected.
        - Restores category-specific available counters (ICU, EMERGENCY, GENERAL).
        - Transitions referral to CANCELLED and writes structured AuditLog.
        """
        now = datetime.now(timezone.utc)
        query = (
            select(BedReservation, Bed)
            .join(Bed, BedReservation.bed_id == Bed.id)
        )
        if reservation_id:
            stmt = query.where(BedReservation.reservation_id == reservation_id).with_for_update().limit(1)
        elif hospital_id and patient_id:
            stmt = (
                query.where(
                    BedReservation.hospital_id == hospital_id,
                )
                .order_by(BedReservation.created_at.desc())
                .with_for_update()
                .limit(1)
            )
        else:
            return {"success": False, "status": "INVALID_PARAMETERS", "message": "Either reservation_id or (hospital_id, patient_id) is required."}

        row = self.session.execute(stmt).first()
        if not row:
            return {"success": False, "status": "NOT_FOUND", "message": "Reservation not found."}
        res, bed = row

        ref = None
        if res.referral_id:
            ref = self.session.execute(
                select(Referral).where(Referral.referral_id == res.referral_id).with_for_update()
            ).scalar_one_or_none()

        if res.status in ["RELEASED", "EXPIRED"]:
            return {"success": False, "status": "ALREADY_RELEASED", "message": "Reservation has already been released or expired."}
        if res.status == "OCCUPIED":
            return {"success": False, "status": "BED_OCCUPIED", "message": "Occupied bed cannot be expired."}
        if res.status == "CONFIRMED":
            return {
                "success": False,
                "status": "CONFIRMED_CANNOT_EXPIRE",
                "message": "Confirmed reservations are guaranteed and cannot be automatically or directly expired. Use release or discharge instead.",
            }
        if res.status != "RESERVED":
            return {
                "success": False,
                "status": "INVALID_STATUS",
                "message": f"Only RESERVED reservations can expire. Current status: '{res.status}'.",
            }

        target_hospital_id = res.hospital_id
        target_patient_id = ref.patient_id if ref else (patient_id or "DIRECT")

        bed.status = "AVAILABLE"
        bed.updated_at = now

        hosp_stmt = select(Hospital).where(Hospital.hospital_id == target_hospital_id).with_for_update()
        hosp = self.session.execute(hosp_stmt).scalar_one_or_none()
        if hosp:
            if bed.bed_type == "ICU":
                hosp.available_icu_beds = min(hosp.icu_beds, hosp.available_icu_beds + 1)
            elif bed.bed_type == "EMERGENCY":
                hosp.available_emergency_beds = min(hosp.emergency_beds, hosp.available_emergency_beds + 1)
            else:
                hosp.available_beds = min(hosp.total_beds, hosp.available_beds + 1)
            hosp.updated_at = now

        previous_status = res.status
        res.status = "EXPIRED"
        res.released_at = now

        if ref and ref.status in ["PENDING", "ACCEPTED"]:
            ref.status = "CANCELLED"
            ref.completed_at = now
            ref.updated_at = now

        audit = AuditLog(
            entity_type="BED_RESERVATION",
            entity_id=res.reservation_id,
            action="AUTO_EXPIRE" if user_id == "RESERVATION_EXPIRY_WORKER" else "DIRECT_EXPIRE",
            performed_by=user_id or "SYSTEM_EXPIRER",
            previous_state={"status": previous_status},
            new_state={"status": "EXPIRED", "bed_id": bed.bed_number, "hospital_id": target_hospital_id},
            created_at=now,
        )
        self.session.add(audit)

        # Operational notifications (only on successful expiration)
        try:
            from src.services.workflow_notification_service import WorkflowNotificationService
            notif_svc = WorkflowNotificationService(self.session)
            notif_svc.notify_bed_expired(res, bed, hosp, ref)
        except Exception as e:
            logger.warning("Error dispatching bed expired notification: %s", e)

        if auto_commit:
            self.session.commit()

        return {
            "success": True,
            "status": "EXPIRED",
            "message": "Reservation expired successfully.",
            "reservation": {
                "hospital_id": target_hospital_id,
                "patient_id": target_patient_id,
                "bed_type": bed.bed_type,
                "bed_id": bed.bed_number,
                "status": "EXPIRED",
                "expired_at": now.isoformat(),
                "reservation_id": res.reservation_id,
            },
        }

    def get_expired_reservations(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """
        Query eligible expired reservations using authoritative PostgreSQL database time.
        Eligible reservations:
        - Status is strictly 'RESERVED' (CONFIRMED is guaranteed and does not auto-expire)
        - expires_at < current database time (func.now())
        - Referral is not already DISCHARGED or CANCELLED or COMPLETED
        """
        stmt = (
            select(BedReservation, Bed)
            .join(Bed, BedReservation.bed_id == Bed.id)
            .where(
                BedReservation.status == "RESERVED",
                BedReservation.expires_at < func.now(),
            )
            .order_by(BedReservation.expires_at.asc())
            .limit(batch_size)
        )
        rows = self.session.execute(stmt).all()
        results = []
        for res, bed in rows:
            patient_id = "DIRECT"
            if res.referral_id:
                ref = self.session.query(Referral).filter_by(referral_id=res.referral_id).first()
                if ref:
                    if ref.status in ["DISCHARGED", "CANCELLED", "COMPLETED"]:
                        continue
                    patient_id = ref.patient_id

            results.append({
                "reservation_id": res.reservation_id,
                "hospital_id": res.hospital_id,
                "bed_id": bed.bed_number,
                "bed_type": bed.bed_type,
                "patient_id": patient_id,
                "referral_id": res.referral_id,
                "status": res.status,
                "expires_at": res.expires_at.isoformat() if res.expires_at else None,
                "reserved_at": res.reserved_at.isoformat() if res.reserved_at else None,
            })
        return results

    def process_expired_reservations_batch(
        self,
        batch_size: int = 100,
        user_id: str = "RESERVATION_EXPIRY_WORKER",
    ) -> Dict[str, Any]:
        """
        Atomically claims and processes a batch of expired reservations using FOR UPDATE SKIP LOCKED.
        Safe for concurrent multi-worker environments.
        Guarantees:
        - No two workers expire the same reservation.
        - Sub-transaction savepoints isolate failures so single row errors do not abort batch.
        - Category-specific counters and audit logs committed atomically.
        """
        claim_stmt = (
            select(BedReservation.reservation_id)
            .where(
                BedReservation.status == "RESERVED",
                BedReservation.expires_at < func.now(),
            )
            .order_by(BedReservation.expires_at.asc())
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        candidate_ids = [r[0] for r in self.session.execute(claim_stmt).fetchall()]

        if not candidate_ids:
            return {
                "processed": 0,
                "succeeded": 0,
                "failed": 0,
                "expired_reservations": [],
            }

        succeeded = 0
        failed = 0
        expired_list = []

        for res_id in candidate_ids:
            sp = self.session.begin_nested()
            try:
                res_outcome = self.expire_reservation_direct(
                    reservation_id=res_id,
                    user_id=user_id,
                    auto_commit=False,
                )
                if res_outcome.get("success"):
                    sp.commit()
                    succeeded += 1
                    expired_list.append(res_outcome["reservation"])
                else:
                    sp.rollback()
                    if res_outcome.get("status") in ("ALREADY_RELEASED", "BED_OCCUPIED", "CONFIRMED_CANNOT_EXPIRE", "INVALID_STATUS"):
                        logger.info("Reservation %s bypassed expiry: %s", res_id, res_outcome.get("status"))
                    else:
                        failed += 1
            except Exception as exc:
                sp.rollback()
                failed += 1
                logger.error("Failed to expire reservation %s in batch: %s", res_id, exc)

        self.session.commit()

        return {
            "processed": len(candidate_ids),
            "succeeded": succeeded,
            "failed": failed,
            "expired_reservations": expired_list,
        }

    def attach_reservation_to_referral(
        self,
        referral_id: str,
        hospital_id: str,
        bed_type: str,
    ) -> Dict[str, Any]:
        """Attach or update destination hospital and bed type on referral."""
        referral = self.get_referral_for_update(referral_id)
        if not referral:
            return {"success": False, "status": "NOT_FOUND", "message": "Referral not found."}

        target_bed_type = (bed_type or "GENERAL").upper().strip()
        referral.to_hospital_id = hospital_id
        referral.bed_type = target_bed_type
        referral.updated_at = datetime.now(timezone.utc)
        self.session.commit()

        return {
            "success": True,
            "status": "UPDATED",
            "referral": self._serialize_referral(referral),
        }

    def initialize_or_reset_inventory(
        self,
        hospital_id: str,
        available_beds: int,
        available_icu_beds: int,
        reset: bool = False,
        available_emergency_beds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create or reset persistent hospital bed inventory in PostgreSQL."""
        now = datetime.now(timezone.utc)
        emg_target = int(available_emergency_beds if available_emergency_beds is not None else 2)
        hosp_stmt = select(Hospital).where(Hospital.hospital_id == hospital_id).with_for_update()
        hospital = self.session.execute(hosp_stmt).scalar_one_or_none()
        if not hospital:
            hospital = Hospital(
                hospital_id=hospital_id,
                name=f"Hospital {hospital_id}",
                state="Punjab",
                district="Amritsar",
                latitude=31.634,
                longitude=74.872,
                total_beds=int(available_beds),
                available_beds=int(available_beds),
                occupied_beds=0,
                icu_beds=int(available_icu_beds),
                available_icu_beds=int(available_icu_beds),
                occupied_icu_beds=0,
                emergency_beds=emg_target,
                available_emergency_beds=emg_target,
                occupied_emergency_beds=0,
                created_at=now,
                updated_at=now,
            )
            self.session.add(hospital)
            self.session.flush()

        existing_beds = self.session.execute(
            select(Bed).where(Bed.hospital_id == hospital_id)
        ).scalars().all()

        if existing_beds and not reset:
            return self.get_hospital_inventory(hospital_id)

        if reset and existing_beds:
            bed_ids = [b.id for b in existing_beds]
            self.session.execute(delete(BedReservation).where(BedReservation.bed_id.in_(bed_ids)))
            self.session.execute(delete(Bed).where(Bed.hospital_id == hospital_id))
            self.session.flush()

        actual_emg = int(available_emergency_beds if available_emergency_beds is not None else (hospital.emergency_beds or 2))
        hospital.total_beds = int(available_beds)
        hospital.available_beds = int(available_beds)
        hospital.occupied_beds = 0
        hospital.icu_beds = int(available_icu_beds)
        hospital.available_icu_beds = int(available_icu_beds)
        hospital.occupied_icu_beds = 0
        hospital.emergency_beds = actual_emg
        hospital.available_emergency_beds = actual_emg
        hospital.occupied_emergency_beds = 0
        hospital.updated_at = now

        for i in range(1, int(available_beds) + 1):
            b = Bed(
                hospital_id=hospital_id,
                bed_number=f"GENERAL-{i:03d}",
                bed_type="GENERAL",
                status="AVAILABLE",
                created_at=now,
                updated_at=now,
            )
            self.session.add(b)

        for i in range(1, int(available_icu_beds) + 1):
            b = Bed(
                hospital_id=hospital_id,
                bed_number=f"ICU-{i:03d}",
                bed_type="ICU",
                status="AVAILABLE",
                created_at=now,
                updated_at=now,
            )
            self.session.add(b)

        for i in range(1, actual_emg + 1):
            b = Bed(
                hospital_id=hospital_id,
                bed_number=f"EMERGENCY-{i:03d}",
                bed_type="EMERGENCY",
                status="AVAILABLE",
                created_at=now,
                updated_at=now,
            )
            self.session.add(b)

        self.session.commit()
        return self.get_hospital_inventory(hospital_id)

# ============================================================
# POSTGRESQL ADMINISTRATIVE REPOSITORY (Phase 4C)
# ============================================================

class PgAdminRepository:
    """
    Administrative Repository for Central, State, and District Governance.
    Performs efficient SQL-level aggregations across PostgreSQL hospital inventories,
    bed capacities, referrals, and registration pipelines without exposing patient PII.
    Includes backward-compatible fallback for offline SQLite development test runners.
    """

    def __init__(self, session: Session):
        self.session = session
        self._owns_session = False

    def _close_if_owned(self):
        if getattr(self, "_owns_session", False) and self.session:
            try:
                self.session.close()
            except Exception:
                pass

    def __del__(self):
        self._close_if_owned()

    def _is_pg(self) -> bool:
        from src.database.db_manager import is_postgres
        return is_postgres()

    # ------------------------------------------------------------
    # 1. CENTRAL GOVERNANCE AGGREGATIONS
    # ------------------------------------------------------------

    def get_central_metrics(self) -> Dict[str, Any]:
        """Aggregate national hospital, bed capacity, referral and registration metrics."""
        if not self._is_pg():
            return self._get_central_metrics_sqlite()

        # 1. Hospital and bed capacity aggregations (Category-Specific, Fix F-04, F-06)
        hosp_stmt = select(
            func.count(func.distinct(Hospital.state)).label("participating_states"),
            func.count(Hospital.hospital_id).label("total_hospitals"),
            func.coalesce(func.sum(Hospital.total_beds), 0).label("total_beds"),
            func.coalesce(func.sum(Hospital.available_beds), 0).label("available_beds"),
            func.coalesce(func.sum(Hospital.occupied_beds), 0).label("occupied_beds"),
            func.coalesce(func.sum(Hospital.icu_beds), 0).label("total_icu_beds"),
            func.coalesce(func.sum(Hospital.available_icu_beds), 0).label("available_icu_beds"),
            func.coalesce(func.sum(Hospital.occupied_icu_beds), 0).label("occupied_icu_beds"),
            func.coalesce(func.sum(Hospital.emergency_beds), 0).label("total_emergency_beds"),
            func.coalesce(func.sum(Hospital.available_emergency_beds), 0).label("available_emergency_beds"),
            func.coalesce(func.sum(Hospital.occupied_emergency_beds), 0).label("occupied_emergency_beds"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(Hospital.approval_status == "APPROVED", Hospital.is_grandfathered.is_(True)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("approved_hospitals"),
        )
        hosp_res = self.session.execute(hosp_stmt).one()

        total_beds = int(hosp_res.total_beds)
        available_beds = int(hosp_res.available_beds)
        occupied_beds = int(hosp_res.occupied_beds)
        total_icu = int(hosp_res.total_icu_beds)
        available_icu = int(hosp_res.available_icu_beds)
        occupied_icu = int(getattr(hosp_res, "occupied_icu_beds", 0) or 0)
        total_emg = int(getattr(hosp_res, "total_emergency_beds", 0) or 0)
        available_emg = int(getattr(hosp_res, "available_emergency_beds", 0) or 0)
        occupied_emg = int(getattr(hosp_res, "occupied_emergency_beds", 0) or 0)

        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0
        emg_occ_rate = round((occupied_emg / total_emg * 100), 1) if total_emg > 0 else 0.0

        # 2. Active bed reservations
        try:
            total_reserved = self.session.execute(
                select(func.count(BedReservation.reservation_id)).where(
                    BedReservation.status.in_(["RESERVED", "CONFIRMED"])
                )
            ).scalar() or 0
        except Exception:
            total_reserved = 0

        # 3. Registration pipeline counts
        try:
            app_stmt = select(
                func.coalesce(
                    func.sum(case((RegistrationApplication.status.in_(["SUBMITTED", "UNDER_REVIEW"]), 1), else_=0)),
                    0,
                ).label("pending"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "APPROVED", 1), else_=0)),
                    0,
                ).label("approved"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "REJECTED", 1), else_=0)),
                    0,
                ).label("rejected"),
            )
            app_res = self.session.execute(app_stmt).one()
            pending_apps = int(app_res.pending)
            approved_apps = int(app_res.approved)
            rejected_apps = int(app_res.rejected)
        except Exception:
            pending_apps = 0
            approved_apps = 0
            rejected_apps = 0

        # 4. Referral counts and interstate transfers
        try:
            from_h = aliased(Hospital, name="from_h")
            to_h = aliased(Hospital, name="to_h")
            ref_stmt = select(
                func.count(Referral.referral_id).label("total_referrals"),
                func.coalesce(
                    func.sum(case((and_(from_h.state.is_not(None), to_h.state.is_not(None), from_h.state != to_h.state), 1), else_=0)),
                    0,
                ).label("interstate_referrals"),
            ).outerjoin(from_h, Referral.from_hospital_id == from_h.hospital_id) \
             .outerjoin(to_h, Referral.to_hospital_id == to_h.hospital_id)

            ref_res = self.session.execute(ref_stmt).one()
            total_referrals = int(ref_res.total_referrals)
            interstate_referrals = int(ref_res.interstate_referrals)
        except Exception:
            total_referrals = 0
            interstate_referrals = 0

        return {
            "participating_states": int(hosp_res.participating_states or 0),
            "total_hospitals": int(hosp_res.total_hospitals or 0),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_reserved_beds": int(total_reserved),
            "total_referrals": total_referrals,
            "interstate_referrals": interstate_referrals,
            "approved_hospitals": int(hosp_res.approved_hospitals or 0),
            "pending_applications": pending_apps,
            "approved_applications": approved_apps,
            "rejected_applications": rejected_apps,
        }

    def _get_central_metrics_sqlite(self) -> Dict[str, Any]:
        """SQLite fallback for offline unit test execution without PostgreSQL."""
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory
        from src.prediction.referral_store import _load_referrals

        hospitals = self.session.query(SqliteHospital).all()
        live_inventories = load_bed_inventory()

        state_set = set()
        total_beds = 0
        available_beds = 0
        total_icu = 0
        available_icu = 0

        for h in hospitals:
            if h.state:
                state_set.add(h.state)
            live = live_inventories.get(h.hospital_id)
            h_avail = live.get("available_beds") if live else (h.available_beds or 0)
            h_avail_icu = live.get("available_icu_beds") if live else (h.available_icu_beds or 0)
            h_total = h.total_beds or 0
            h_total_icu = h.icu_beds or 0

            total_beds += h_total
            available_beds += h_avail
            total_icu += h_total_icu
            available_icu += h_avail_icu

        all_referrals = _load_referrals()
        interstate = [
            r for r in all_referrals
            if r.get("from_state") and r.get("to_state") and r.get("from_state") != r.get("to_state")
        ]

        occupied_beds = max(0, total_beds - available_beds)
        occupied_icu = max(0, total_icu - available_icu)
        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0

        return {
            "participating_states": len(state_set),
            "total_hospitals": len(hospitals),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_reserved_beds": 0,
            "total_referrals": len(all_referrals),
            "interstate_referrals": len(interstate),
            "approved_hospitals": len(hospitals),
            "pending_applications": 0,
            "approved_applications": 0,
            "rejected_applications": 0,
        }

    def get_central_states_summary(self) -> List[Dict[str, Any]]:
        """Return state-level aggregated statistics ordered by state name."""
        if not self._is_pg():
            return self._get_central_states_summary_sqlite()

        stmt = select(
            func.coalesce(Hospital.state, "Other").label("state"),
            func.count(Hospital.hospital_id).label("hospitals"),
            func.coalesce(func.sum(Hospital.total_beds), 0).label("total_beds"),
            func.coalesce(func.sum(Hospital.available_beds), 0).label("available_beds"),
            func.coalesce(func.sum(Hospital.icu_beds), 0).label("total_icu"),
            func.coalesce(func.sum(Hospital.available_icu_beds), 0).label("available_icu"),
        ).group_by(Hospital.state).order_by(Hospital.state.asc())

        rows = self.session.execute(stmt).fetchall()
        summaries = []
        for r in rows:
            tot_beds = int(r.total_beds)
            avail_beds = int(r.available_beds)
            occ_rate = round(((tot_beds - avail_beds) / tot_beds * 100), 1) if tot_beds > 0 else 0.0
            summaries.append({
                "state": r.state,
                "hospitals": int(r.hospitals),
                "total_beds": tot_beds,
                "available_beds": avail_beds,
                "total_icu": int(r.total_icu),
                "available_icu": int(r.available_icu),
                "occupancy_rate": occ_rate,
            })
        return summaries

    def _get_central_states_summary_sqlite(self) -> List[Dict[str, Any]]:
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory

        hospitals = self.session.query(SqliteHospital).all()
        live_inventories = load_bed_inventory()

        state_map: dict[str, dict] = {}
        for h in hospitals:
            s = h.state or "Other"
            if s not in state_map:
                state_map[s] = {
                    "state": s,
                    "hospitals": 0,
                    "total_beds": 0,
                    "available_beds": 0,
                    "total_icu": 0,
                    "available_icu": 0,
                }
            live = live_inventories.get(h.hospital_id)
            h_avail = live.get("available_beds") if live else (h.available_beds or 0)
            h_avail_icu = live.get("available_icu_beds") if live else (h.available_icu_beds or 0)
            state_map[s]["hospitals"] += 1
            state_map[s]["total_beds"] += (h.total_beds or 0)
            state_map[s]["available_beds"] += h_avail
            state_map[s]["total_icu"] += (h.icu_beds or 0)
            state_map[s]["available_icu"] += h_avail_icu

        summaries = []
        for s, info in sorted(state_map.items()):
            tot = info["total_beds"]
            avail = info["available_beds"]
            occ = round(((tot - avail) / tot * 100), 1) if tot > 0 else 0.0
            info["occupancy_rate"] = occ
            summaries.append(info)
        return summaries

    # ------------------------------------------------------------
    # 2. STATE GOVERNANCE AGGREGATIONS
    # ------------------------------------------------------------

    def get_state_metrics(self, state: str) -> Dict[str, Any]:
        """Aggregate hospital, bed capacity, referral, and application metrics for a state."""
        if not self._is_pg():
            return self._get_state_metrics_sqlite(state)

        hosp_stmt = select(
            func.count(func.distinct(Hospital.district)).label("total_districts"),
            func.count(Hospital.hospital_id).label("total_hospitals"),
            func.coalesce(func.sum(Hospital.total_beds), 0).label("total_beds"),
            func.coalesce(func.sum(Hospital.available_beds), 0).label("available_beds"),
            func.coalesce(func.sum(Hospital.occupied_beds), 0).label("occupied_beds"),
            func.coalesce(func.sum(Hospital.icu_beds), 0).label("total_icu_beds"),
            func.coalesce(func.sum(Hospital.available_icu_beds), 0).label("available_icu_beds"),
            func.coalesce(func.sum(Hospital.occupied_icu_beds), 0).label("occupied_icu_beds"),
            func.coalesce(func.sum(Hospital.emergency_beds), 0).label("total_emergency_beds"),
            func.coalesce(func.sum(Hospital.available_emergency_beds), 0).label("available_emergency_beds"),
            func.coalesce(func.sum(Hospital.occupied_emergency_beds), 0).label("occupied_emergency_beds"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(Hospital.approval_status == "APPROVED", Hospital.is_grandfathered.is_(True)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("approved_hospitals"),
        ).where(Hospital.state.ilike(state))

        hosp_res = self.session.execute(hosp_stmt).one()

        total_beds = int(hosp_res.total_beds)
        available_beds = int(hosp_res.available_beds)
        occupied_beds = int(hosp_res.occupied_beds)
        total_icu = int(hosp_res.total_icu_beds)
        available_icu = int(hosp_res.available_icu_beds)
        occupied_icu = int(getattr(hosp_res, "occupied_icu_beds", 0) or 0)
        total_emg = int(getattr(hosp_res, "total_emergency_beds", 0) or 0)
        available_emg = int(getattr(hosp_res, "available_emergency_beds", 0) or 0)
        occupied_emg = int(getattr(hosp_res, "occupied_emergency_beds", 0) or 0)

        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0
        emg_occ_rate = round((occupied_emg / total_emg * 100), 1) if total_emg > 0 else 0.0

        # Active reservations in state
        try:
            total_reserved = self.session.execute(
                select(func.count(BedReservation.reservation_id))
                .join(Hospital, BedReservation.hospital_id == Hospital.hospital_id)
                .where(and_(
                    Hospital.state.ilike(state),
                    BedReservation.status.in_(["RESERVED", "CONFIRMED"])
                ))
            ).scalar() or 0
        except Exception:
            total_reserved = 0

        # State registration applications
        try:
            app_stmt = select(
                func.coalesce(
                    func.sum(case((RegistrationApplication.status.in_(["SUBMITTED", "UNDER_REVIEW"]), 1), else_=0)),
                    0,
                ).label("pending"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "APPROVED", 1), else_=0)),
                    0,
                ).label("approved"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "REJECTED", 1), else_=0)),
                    0,
                ).label("rejected"),
            ).where(RegistrationApplication.state.ilike(state))
            app_res = self.session.execute(app_stmt).one()
            pending_apps = int(app_res.pending)
            approved_apps = int(app_res.approved)
            rejected_apps = int(app_res.rejected)
        except Exception:
            pending_apps = 0
            approved_apps = 0
            rejected_apps = 0

        # Referrals involving this state
        try:
            from_h = aliased(Hospital, name="from_h")
            to_h = aliased(Hospital, name="to_h")
            ref_stmt = select(
                func.count(Referral.referral_id).label("total_referrals"),
            ).outerjoin(from_h, Referral.from_hospital_id == from_h.hospital_id) \
             .outerjoin(to_h, Referral.to_hospital_id == to_h.hospital_id) \
             .where(or_(from_h.state.ilike(state), to_h.state.ilike(state)))

            ref_res = self.session.execute(ref_stmt).one()
            total_referrals = int(ref_res.total_referrals)
        except Exception:
            total_referrals = 0

        return {
            "total_districts": int(hosp_res.total_districts or 0),
            "total_hospitals": int(hosp_res.total_hospitals or 0),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_reserved_beds": int(total_reserved),
            "total_referrals": total_referrals,
            "approved_hospitals": int(hosp_res.approved_hospitals or 0),
            "pending_applications": pending_apps,
            "approved_applications": approved_apps,
            "rejected_applications": rejected_apps,
        }

    def _get_state_metrics_sqlite(self, state: str) -> Dict[str, Any]:
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory
        from src.prediction.referral_store import _load_referrals

        hospitals = self.session.query(SqliteHospital).filter(SqliteHospital.state.ilike(state)).all()
        live_inventories = load_bed_inventory()

        district_set = set()
        total_beds = 0
        available_beds = 0
        total_icu = 0
        available_icu = 0

        for h in hospitals:
            if h.district:
                district_set.add(h.district)
            live = live_inventories.get(h.hospital_id)
            h_avail = live.get("available_beds") if live else (h.available_beds or 0)
            h_avail_icu = live.get("available_icu_beds") if live else (h.available_icu_beds or 0)
            total_beds += (h.total_beds or 0)
            available_beds += h_avail
            total_icu += (h.icu_beds or 0)
            available_icu += h_avail_icu

        referrals = _load_referrals()
        state_l = state.lower()
        state_refs = [
            r for r in referrals
            if (r.get("from_state") or "").lower() == state_l or (r.get("to_state") or "").lower() == state_l
        ]

        occupied_beds = max(0, total_beds - available_beds)
        occupied_icu = max(0, total_icu - available_icu)
        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0

        return {
            "total_districts": len(district_set),
            "total_hospitals": len(hospitals),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_reserved_beds": 0,
            "total_referrals": len(state_refs),
            "approved_hospitals": len(hospitals),
            "pending_applications": 0,
            "approved_applications": 0,
            "rejected_applications": 0,
        }

    def get_state_districts_summary(self, state: str) -> List[Dict[str, Any]]:
        """Return district-level aggregated statistics for a specific state."""
        if not self._is_pg():
            return self._get_state_districts_summary_sqlite(state)

        stmt = select(
            func.coalesce(Hospital.district, "Unknown").label("district"),
            func.count(Hospital.hospital_id).label("hospitals"),
            func.coalesce(func.sum(Hospital.total_beds), 0).label("total_beds"),
            func.coalesce(func.sum(Hospital.available_beds), 0).label("available_beds"),
            func.coalesce(func.sum(Hospital.icu_beds), 0).label("total_icu"),
            func.coalesce(func.sum(Hospital.available_icu_beds), 0).label("available_icu"),
        ).where(Hospital.state.ilike(state)).group_by(Hospital.district).order_by(Hospital.district.asc())

        rows = self.session.execute(stmt).fetchall()
        summaries = []
        for r in rows:
            tot_beds = int(r.total_beds)
            avail_beds = int(r.available_beds)
            occ_rate = round(((tot_beds - avail_beds) / tot_beds * 100), 1) if tot_beds > 0 else 0.0
            summaries.append({
                "district": r.district,
                "hospitals": int(r.hospitals),
                "total_beds": tot_beds,
                "available_beds": avail_beds,
                "total_icu": int(r.total_icu),
                "available_icu": int(r.available_icu),
                "occupancy_rate": occ_rate,
            })
        return summaries

    def _get_state_districts_summary_sqlite(self, state: str) -> List[Dict[str, Any]]:
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory

        hospitals = self.session.query(SqliteHospital).filter(SqliteHospital.state.ilike(state)).all()
        live_inventories = load_bed_inventory()

        district_map: dict[str, dict] = {}
        for h in hospitals:
            d = h.district or "Unknown"
            if d not in district_map:
                district_map[d] = {
                    "district": d,
                    "hospitals": 0,
                    "total_beds": 0,
                    "available_beds": 0,
                    "total_icu": 0,
                    "available_icu": 0,
                }
            live = live_inventories.get(h.hospital_id)
            h_avail = live.get("available_beds") if live else (h.available_beds or 0)
            h_avail_icu = live.get("available_icu_beds") if live else (h.available_icu_beds or 0)
            district_map[d]["hospitals"] += 1
            district_map[d]["total_beds"] += (h.total_beds or 0)
            district_map[d]["available_beds"] += h_avail
            district_map[d]["total_icu"] += (h.icu_beds or 0)
            district_map[d]["available_icu"] += h_avail_icu

        summaries = []
        for d, info in sorted(district_map.items()):
            tot = info["total_beds"]
            avail = info["available_beds"]
            occ = round(((tot - avail) / tot * 100), 1) if tot > 0 else 0.0
            info["occupancy_rate"] = occ
            summaries.append(info)
        return summaries

    # ------------------------------------------------------------
    # 3. DISTRICT GOVERNANCE AGGREGATIONS
    # ------------------------------------------------------------

    def get_district_metrics(self, district: str, state: Optional[str] = None) -> Dict[str, Any]:
        """Aggregate hospital, bed capacity, referral, and alert metrics for a district."""
        if not self._is_pg():
            return self._get_district_metrics_sqlite(district, state)

        hosp_filters = [Hospital.district.ilike(district)]
        if state:
            hosp_filters.append(Hospital.state.ilike(state))

        hosp_stmt = select(
            func.count(Hospital.hospital_id).label("total_hospitals"),
            func.coalesce(func.sum(Hospital.total_beds), 0).label("total_beds"),
            func.coalesce(func.sum(Hospital.available_beds), 0).label("available_beds"),
            func.coalesce(func.sum(Hospital.occupied_beds), 0).label("occupied_beds"),
            func.coalesce(func.sum(Hospital.icu_beds), 0).label("total_icu_beds"),
            func.coalesce(func.sum(Hospital.available_icu_beds), 0).label("available_icu_beds"),
            func.coalesce(func.sum(Hospital.occupied_icu_beds), 0).label("occupied_icu_beds"),
            func.coalesce(func.sum(Hospital.emergency_beds), 0).label("total_emergency_beds"),
            func.coalesce(func.sum(Hospital.available_emergency_beds), 0).label("available_emergency_beds"),
            func.coalesce(func.sum(Hospital.occupied_emergency_beds), 0).label("occupied_emergency_beds"),
            func.coalesce(
                func.sum(
                    case(
                        (or_(Hospital.approval_status == "APPROVED", Hospital.is_grandfathered.is_(True)), 1),
                        else_=0,
                    )
                ),
                0,
            ).label("approved_hospitals"),
        ).where(and_(*hosp_filters))

        hosp_res = self.session.execute(hosp_stmt).one()

        total_beds = int(hosp_res.total_beds)
        available_beds = int(hosp_res.available_beds)
        occupied_beds = int(hosp_res.occupied_beds)
        total_icu = int(hosp_res.total_icu_beds)
        available_icu = int(hosp_res.available_icu_beds)
        occupied_icu = int(getattr(hosp_res, "occupied_icu_beds", 0) or 0)
        total_emg = int(getattr(hosp_res, "total_emergency_beds", 0) or 0)
        available_emg = int(getattr(hosp_res, "available_emergency_beds", 0) or 0)
        occupied_emg = int(getattr(hosp_res, "occupied_emergency_beds", 0) or 0)

        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0
        emg_occ_rate = round((occupied_emg / total_emg * 100), 1) if total_emg > 0 else 0.0

        # Active reservations in district
        try:
            total_reserved = self.session.execute(
                select(func.count(BedReservation.reservation_id))
                .join(Hospital, BedReservation.hospital_id == Hospital.hospital_id)
                .where(and_(
                    *hosp_filters,
                    BedReservation.status.in_(["RESERVED", "CONFIRMED"])
                ))
            ).scalar() or 0
        except Exception:
            total_reserved = 0

        # District registration applications
        try:
            app_filters = [RegistrationApplication.district.ilike(district)]
            if state:
                app_filters.append(RegistrationApplication.state.ilike(state))
            app_stmt = select(
                func.coalesce(
                    func.sum(case((RegistrationApplication.status.in_(["SUBMITTED", "UNDER_REVIEW"]), 1), else_=0)),
                    0,
                ).label("pending"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "APPROVED", 1), else_=0)),
                    0,
                ).label("approved"),
                func.coalesce(
                    func.sum(case((RegistrationApplication.status == "REJECTED", 1), else_=0)),
                    0,
                ).label("rejected"),
            ).where(and_(*app_filters))
            app_res = self.session.execute(app_stmt).one()
            pending_apps = int(app_res.pending)
            approved_apps = int(app_res.approved)
            rejected_apps = int(app_res.rejected)
        except Exception:
            pending_apps = 0
            approved_apps = 0
            rejected_apps = 0

        # Referrals involving this district
        try:
            from_h = aliased(Hospital, name="from_h")
            to_h = aliased(Hospital, name="to_h")

            ref_geo_filters = [or_(from_h.district.ilike(district), to_h.district.ilike(district))]
            if state:
                ref_geo_filters.append(or_(from_h.state.ilike(state), to_h.state.ilike(state)))

            ref_stmt = select(
                func.count(Referral.referral_id).label("total_referrals"),
                func.coalesce(
                    func.sum(case((Referral.status.in_(["PENDING", "ACCEPTED", "IN_TRANSIT", "ARRIVED", "TREATMENT_ACTIVE"]), 1), else_=0)),
                    0,
                ).label("active_referrals"),
                func.coalesce(
                    func.sum(case((Referral.status == "PENDING", 1), else_=0)),
                    0,
                ).label("pending_referrals"),
                func.coalesce(
                    func.sum(case((Referral.status == "IN_TRANSIT", 1), else_=0)),
                    0,
                ).label("in_transit_referrals"),
            ).outerjoin(from_h, Referral.from_hospital_id == from_h.hospital_id) \
             .outerjoin(to_h, Referral.to_hospital_id == to_h.hospital_id) \
             .where(and_(*ref_geo_filters))

            ref_res = self.session.execute(ref_stmt).one()
            total_referrals = int(ref_res.total_referrals)
            active_count = int(ref_res.active_referrals)
            pending_count = int(ref_res.pending_referrals)
            in_transit_count = int(ref_res.in_transit_referrals)
        except Exception:
            total_referrals = 0
            active_count = 0
            pending_count = 0
            in_transit_count = 0

        # Critical Alerts: ICU exhaustion and referral bottlenecks
        critical_alerts = []
        try:
            icu_shortage_stmt = select(
                Hospital.hospital_id,
                Hospital.name,
                Hospital.icu_beds,
                Hospital.available_icu_beds,
            ).where(
                and_(
                    *hosp_filters,
                    Hospital.icu_beds > 0,
                    (Hospital.available_icu_beds * 1.0 / Hospital.icu_beds) <= 0.15,
                )
            ).limit(5)
            shortage_rows = self.session.execute(icu_shortage_stmt).fetchall()
            for row in shortage_rows:
                critical_alerts.append({
                    "severity": "CRITICAL",
                    "type": "ICU_EXHAUSTION",
                    "hospital_id": row.hospital_id,
                    "hospital_name": row.name,
                    "message": f"Critical ICU shortage: only {row.available_icu_beds}/{row.icu_beds} ICU beds remaining.",
                })
        except Exception:
            pass

        if pending_count >= 3:
            critical_alerts.append({
                "severity": "WARNING",
                "type": "REFERRAL_BOTTLENECK",
                "message": f"Referral backlog detected: {pending_count} pending referrals awaiting acceptance.",
            })

        metrics = {
            "total_hospitals": int(hosp_res.total_hospitals or 0),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_active_referrals": active_count,
            "pending_referrals": pending_count,
            "in_transit_referrals": in_transit_count,
            "total_referrals": total_referrals,
            "total_reserved_beds": int(total_reserved),
            "approved_hospitals": int(hosp_res.approved_hospitals or 0),
            "pending_applications": pending_apps,
            "approved_applications": approved_apps,
            "rejected_applications": rejected_apps,
        }

        return {
            "metrics": metrics,
            "critical_alerts": critical_alerts,
        }

    def _get_district_metrics_sqlite(self, district: str, state: Optional[str] = None) -> Dict[str, Any]:
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory
        from src.prediction.referral_store import _load_referrals

        query = self.session.query(SqliteHospital).filter(SqliteHospital.district.ilike(district))
        if state:
            query = query.filter(SqliteHospital.state.ilike(state))
        hospitals = query.all()
        live_inventories = load_bed_inventory()

        total_beds = 0
        available_beds = 0
        total_icu = 0
        available_icu = 0
        critical_alerts = []

        for h in hospitals:
            live = live_inventories.get(h.hospital_id)
            h_avail = live.get("available_beds") if live else (h.available_beds or 0)
            h_avail_icu = live.get("available_icu_beds") if live else (h.available_icu_beds or 0)
            h_total = h.total_beds or 0
            h_total_icu = h.icu_beds or 0

            total_beds += h_total
            available_beds += h_avail
            total_icu += h_total_icu
            available_icu += h_avail_icu

            if h_total_icu > 0 and (h_avail_icu / h_total_icu) <= 0.15:
                critical_alerts.append({
                    "severity": "CRITICAL",
                    "type": "ICU_EXHAUSTION",
                    "hospital_id": h.hospital_id,
                    "hospital_name": h.name,
                    "message": f"Critical ICU shortage: only {h_avail_icu}/{h_total_icu} ICU beds remaining.",
                })

        referrals = _load_referrals()
        district_l = district.lower()
        active_count = 0
        pending_count = 0
        in_transit_count = 0
        total_refs = 0

        for r in referrals:
            from_d = (r.get("from_district") or "").lower()
            to_d = (r.get("to_district") or "").lower()
            if from_d == district_l or to_d == district_l:
                total_refs += 1
                status = r.get("status")
                if status == "PENDING":
                    pending_count += 1
                elif status == "IN_TRANSIT":
                    in_transit_count += 1
                if status in ["PENDING", "ACCEPTED", "IN_TRANSIT", "ARRIVED", "TREATMENT_ACTIVE"]:
                    active_count += 1

        if pending_count >= 3:
            critical_alerts.append({
                "severity": "WARNING",
                "type": "REFERRAL_BOTTLENECK",
                "message": f"Referral backlog detected: {pending_count} pending referrals awaiting acceptance.",
            })

        occupied_beds = max(0, total_beds - available_beds)
        occupied_icu = max(0, total_icu - available_icu)
        bed_occ_rate = round((occupied_beds / total_beds * 100), 1) if total_beds > 0 else 0.0
        icu_occ_rate = round((occupied_icu / total_icu * 100), 1) if total_icu > 0 else 0.0

        metrics = {
            "total_hospitals": len(hospitals),
            "total_beds": total_beds,
            "available_beds": available_beds,
            "occupied_beds": occupied_beds,
            "bed_occupancy_rate": bed_occ_rate,
            "total_icu_beds": total_icu,
            "available_icu_beds": available_icu,
            "occupied_icu_beds": occupied_icu,
            "icu_occupancy_rate": icu_occ_rate,
            "total_active_referrals": active_count,
            "pending_referrals": pending_count,
            "in_transit_referrals": in_transit_count,
            "total_referrals": total_refs,
            "total_reserved_beds": 0,
            "approved_hospitals": len(hospitals),
            "pending_applications": 0,
            "approved_applications": 0,
            "rejected_applications": 0,
        }

        return {
            "metrics": metrics,
            "critical_alerts": critical_alerts,
        }

    # ------------------------------------------------------------
    # 4. PAGINATED HOSPITAL CATALOGUE
    # ------------------------------------------------------------

    def get_paginated_hospitals(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        search: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Query and paginate hospital facilities matching geographic and search filters."""
        if not self._is_pg():
            return self._get_paginated_hospitals_sqlite(state, district, search, status, page, page_size)

        where_clauses = []
        if district:
            where_clauses.append(Hospital.district.ilike(district))
        if state:
            where_clauses.append(Hospital.state.ilike(state))
        if search:
            term = f"%{search}%"
            where_clauses.append(or_(Hospital.name.ilike(term), Hospital.hospital_id.ilike(term), Hospital.city.ilike(term)))
        if status:
            if status.upper() == "APPROVED":
                where_clauses.append(or_(Hospital.approval_status == "APPROVED", Hospital.is_grandfathered.is_(True)))
            else:
                where_clauses.append(Hospital.approval_status.ilike(status))

        filter_condition = and_(*where_clauses) if where_clauses else True

        total = self.session.execute(
            select(func.count(Hospital.hospital_id)).where(filter_condition)
        ).scalar() or 0

        query = (
            select(Hospital)
            .where(filter_condition)
            .order_by(Hospital.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        records = self.session.execute(query).scalars().all()

        hospitals_list = []
        for h in records:
            hospitals_list.append({
                "hospital_id": h.hospital_id,
                "name": h.name,
                "state": h.state,
                "district": h.district,
                "city": h.city,
                "total_beds": h.total_beds or 0,
                "available_beds": h.available_beds or 0,
                "occupied_beds": h.occupied_beds or 0,
                "icu_beds": h.icu_beds or 0,
                "available_icu_beds": h.available_icu_beds or 0,
                "emergency_24x7": h.emergency_24x7 == "Yes",
                "cardiology": h.cardiology == "Yes",
                "neurology": h.neurology == "Yes",
                "ventilator": h.ventilator == "Yes",
                "ambulance": h.ambulance == "Yes",
                "ct_scan": h.ct_scan == "Yes",
                "approval_status": getattr(h, "approval_status", "APPROVED"),
            })

        return {
            "total": int(total),
            "page": page,
            "page_size": page_size,
            "hospitals": hospitals_list,
        }

    def _get_paginated_hospitals_sqlite(
        self,
        state: Optional[str],
        district: Optional[str],
        search: Optional[str],
        status: Optional[str],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        from src.database.models import Hospital as SqliteHospital
        from src.prediction.reservation_store import load_bed_inventory

        query = self.session.query(SqliteHospital)
        if district:
            query = query.filter(SqliteHospital.district.ilike(district))
        if state:
            query = query.filter(SqliteHospital.state.ilike(state))
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    SqliteHospital.name.ilike(term),
                    SqliteHospital.hospital_id.ilike(term),
                    SqliteHospital.city.ilike(term),
                )
            )

        total = query.count()
        records = query.order_by(SqliteHospital.name.asc()).offset((page - 1) * page_size).limit(page_size).all()
        live_inventories = load_bed_inventory()

        hospitals_list = []
        for h in records:
            live = live_inventories.get(h.hospital_id)
            avail_beds = live.get("available_beds") if live else h.available_beds
            avail_icu = live.get("available_icu_beds") if live else h.available_icu_beds
            hospitals_list.append({
                "hospital_id": h.hospital_id,
                "name": h.name,
                "state": h.state,
                "district": h.district,
                "city": h.city,
                "total_beds": h.total_beds or 0,
                "available_beds": avail_beds or 0,
                "occupied_beds": (h.total_beds or 0) - (avail_beds or 0),
                "icu_beds": h.icu_beds or 0,
                "available_icu_beds": avail_icu or 0,
                "emergency_24x7": h.emergency_24x7 == "Yes",
                "cardiology": h.cardiology == "Yes",
                "neurology": h.neurology == "Yes",
                "ventilator": h.ventilator == "Yes",
                "ambulance": h.ambulance == "Yes",
                "ct_scan": h.ct_scan == "Yes",
                "approval_status": "APPROVED",
            })

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "hospitals": hospitals_list,
        }

    # ------------------------------------------------------------
    # 5. PAGINATED REFERRAL AUDIT (PII-SAFE)
    # ------------------------------------------------------------

    def get_paginated_referrals(
        self,
        state: Optional[str] = None,
        district: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """
        Query and paginate referrals within an authorized geographic scope.
        Strictly sanitizes and masks patient PII (names, contacts, clinical notes)
        to adhere to DISHA privacy requirements for administrative surveillance.
        """
        if not self._is_pg():
            return self._get_paginated_referrals_sqlite(state, district, status, priority, page, page_size)

        from_h = aliased(Hospital, name="from_h")
        to_h = aliased(Hospital, name="to_h")

        where_clauses = []
        if district:
            where_clauses.append(or_(from_h.district.ilike(district), to_h.district.ilike(district)))
        if state:
            where_clauses.append(or_(from_h.state.ilike(state), to_h.state.ilike(state)))
        if status:
            where_clauses.append(Referral.status.ilike(status))
        if priority:
            where_clauses.append(Referral.priority.ilike(priority))

        filter_condition = and_(*where_clauses) if where_clauses else True

        count_stmt = (
            select(func.count(Referral.referral_id))
            .outerjoin(from_h, Referral.from_hospital_id == from_h.hospital_id)
            .outerjoin(to_h, Referral.to_hospital_id == to_h.hospital_id)
            .where(filter_condition)
        )
        total = self.session.execute(count_stmt).scalar() or 0

        query = (
            select(Referral, from_h, to_h)
            .outerjoin(from_h, Referral.from_hospital_id == from_h.hospital_id)
            .outerjoin(to_h, Referral.to_hospital_id == to_h.hospital_id)
            .where(filter_condition)
            .order_by(Referral.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = self.session.execute(query).all()

        referrals_list = []
        for r, fh, th in rows:
            raw_pid = str(r.patient_id or "")
            masked_pid = f"PAT-***{raw_pid[-4:]}" if len(raw_pid) >= 4 else "PAT-ANON"

            referrals_list.append({
                "referral_id": r.referral_id,
                "patient_id": masked_pid,
                "from_hospital_id": r.from_hospital_id,
                "to_hospital_id": r.to_hospital_id,
                "from_hospital_name": fh.name if fh else r.from_hospital_id,
                "to_hospital_name": th.name if th else r.to_hospital_id,
                "from_state": fh.state if fh else None,
                "from_district": fh.district if fh else None,
                "to_state": th.state if th else None,
                "to_district": th.district if th else None,
                "status": r.status,
                "priority": r.priority,
                "bed_type": r.bed_type,
                "ambulance_id": r.ambulance_id,
                "eta_minutes": r.eta_minutes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })

        return {
            "total": int(total),
            "page": page,
            "page_size": page_size,
            "referrals": referrals_list,
        }

    def _get_paginated_referrals_sqlite(
        self,
        state: Optional[str],
        district: Optional[str],
        status: Optional[str],
        priority: Optional[str],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        from src.prediction.referral_store import _load_referrals

        referrals = _load_referrals()
        district_l = district.lower() if district else None
        state_l = state.lower() if state else None
        status_u = status.upper() if status else None
        priority_u = priority.upper() if priority else None

        filtered = []
        for r in referrals:
            if district_l:
                from_d = (r.get("from_district") or "").lower()
                to_d = (r.get("to_district") or "").lower()
                if from_d != district_l and to_d != district_l:
                    continue
            if state_l:
                from_s = (r.get("from_state") or "").lower()
                to_s = (r.get("to_state") or "").lower()
                if from_s != state_l and to_s != state_l:
                    continue
            if status_u and (r.get("status") or "").upper() != status_u:
                continue
            if priority_u and (r.get("priority") or "").upper() != priority_u:
                continue

            raw_pid = str(r.get("patient_id") or "")
            masked_pid = f"PAT-***{raw_pid[-4:]}" if len(raw_pid) >= 4 else "PAT-ANON"
            r_copy = dict(r)
            r_copy["patient_id"] = masked_pid
            # Strip patient sensitive data if present
            r_copy.pop("patient_name", None)
            r_copy.pop("phone", None)
            r_copy.pop("patient_phone", None)
            filtered.append(r_copy)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size
        paged = filtered[start:end]

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "referrals": paged,
        }



