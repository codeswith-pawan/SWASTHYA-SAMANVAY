# Database Architecture, Schema Migrations & Recovery

**Project:** ArogyaSetu Grid — Unified Critical Care & Hospital Command Network (`SIH_Hospital_AI`)

---

## 1. Supported Storage Engines

1. **Production (PostgreSQL 15+ Cluster):**
   - Implements full ACID transactions, connection pooling (`pool_size=20`, `max_overflow=10`, `pool_recycle=1800`), and explicit row-level locking (`SELECT ... FOR UPDATE`) for concurrent bed reservation safety.
   - Tested and verified on PostgreSQL 15, 16, and 17.
2. **Development / Lightweight Fallback (SQLite):**
   - SQLite (`data/hospital_app.db`) is supported for rapid local prototyping without external service dependencies.

---

## 2. Schema Structure & Migrations

The relational schema is versioned under `migrations/`:

- `migrations/001_initial_postgresql_schema.sql`: Core hospital network, inpatient beds, clinical patients, and inter-hospital referral tables.
- `migrations/002_referral_workflow_and_notifications.sql`: Live operational notifications, transactional outbox (`email_outbox`), and reservation expiry audit logs.
- `migrations/003_hierarchical_registration_and_review.sql`: Structured 3-tier registration dossiers, document verification records, nodal officer OTP audits, and credential provisioning tracking.

### Applying Migrations to PostgreSQL
```bash
# Execute initial schema migration
psql -d "$DATABASE_URL" -f migrations/001_initial_postgresql_schema.sql
psql -d "$DATABASE_URL" -f migrations/002_referral_workflow_and_notifications.sql
psql -d "$DATABASE_URL" -f migrations/003_hierarchical_registration_and_review.sql
```

---

## 3. Key Relational Tables

| Table Name | Description | Key Indexes / Invariants |
|:---|:---|:---|
| `hospitals` | Facility metadata, geo-coordinates, tier classification | `hospital_id` (PK), `state`, `district`, `pincode` |
| `hospital_bed_inventory` | Available, reserved, and occupied ICU/general beds | `hospital_id` (FK), row locks on reservation |
| `referrals` | Full patient referral state machine history | `referral_id` (PK), `from_hospital_id`, `to_hospital_id`, `status` |
| `registration_applications` | Tier I/II/III onboarding dossiers | `application_id` (PK), `application_number` (UNIQUE), `status` |
| `application_documents` | Uploaded certifications, SHA-256 checksums | `document_id` (PK), `application_id` (FK), `verification_status` |
| `email_outbox` | Transactional outbox event store | `id` (PK), `status` (PENDING/SENT/FAILED), `locked_at` |

---

## 4. Backup & Disaster Recovery Procedures

### 4.1 Automated Backup Utility
```bash
# Execute full database and document backup
./scripts/backup_database.sh
```

**Output Artifacts (`data/backups/`):**
- `sih_db_[TIMESTAMP].dump`: Compressed custom-format `pg_dump` with TOC.
- `sih_documents_[TIMESTAMP].tar.gz`: Compressed archive of all applicant documents.
- `sih_backup_[TIMESTAMP].sha256`: SHA-256 verification checksum.

### 4.2 Controlled Restore Procedure
```bash
# Safety check: Never restore to sih_hospital_dev
./scripts/restore_database.sh data/backups/sih_db_[TIMESTAMP].dump target_database_name
```
