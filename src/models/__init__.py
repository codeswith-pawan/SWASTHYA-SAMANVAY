"""
SQLAlchemy ORM Models module for SWASTHYA SAMANVAY.
Exposes all relational and registration models including VerificationToken,
RegistrationApplication, Hospital, Bed, Referral, User, etc.
"""

from src.database.pg_models import (
    PgBase,
    Role,
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
    RegistrationDocument,
    ApprovalHistory,
    VerificationToken,
    ApplicationTrackingToken,
    AccountActivationToken,
    RegistrationEmailOutbox,
    PasswordResetToken,
    WorkerHeartbeat,
)
from src.database.database import Base as SqliteBase

# Primary Base for all relational models
Base = PgBase

__all__ = [
    "Base",
    "PgBase",
    "SqliteBase",
    "Role",
    "Hospital",
    "User",
    "Patient",
    "HospitalVisit",
    "Bed",
    "Referral",
    "BedReservation",
    "AuditLog",
    "Notification",
    "RegistrationApplication",
    "RegistrationDocument",
    "ApprovalHistory",
    "VerificationToken",
    "ApplicationTrackingToken",
    "AccountActivationToken",
    "RegistrationEmailOutbox",
    "PasswordResetToken",
    "WorkerHeartbeat",
]
