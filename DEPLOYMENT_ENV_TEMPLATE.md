# SWASTHYA SAMANVAY — Deployment Environment Variables Template
**Complete Master Environment Variable Reference for Vercel, Render, Docker & Cloud Hosts**

---

> [!CAUTION]
> **NEVER** commit real passwords, tokens, API keys, or private secrets to version control.
> Use the placeholder templates below to configure your deployment platforms.

---

## 1. Frontend Environment Variables (Vercel)

Set these variables in the **Vercel Dashboard → Settings → Environment Variables**:

```bash
# ------------------------------------------------------------------------------
# VERCEL FRONTEND CONFIGURATION
# ------------------------------------------------------------------------------

# Public backend API endpoint (Mandatory)
# Format: Full HTTPS URL to your Render web service without trailing slash
NEXT_PUBLIC_API_URL=https://REPLACE_WITH_YOUR_RENDER_BACKEND_URL.onrender.com

# Fallback alias for API endpoint (Recommended for consistency)
NEXT_PUBLIC_API_BASE_URL=https://REPLACE_WITH_YOUR_RENDER_BACKEND_URL.onrender.com

# Node environment flag
NODE_ENV=production
```

---

## 2. Backend Environment Variables (Render Web Service)

Set these variables in the **Render Dashboard → Environment**:

```bash
# ==============================================================================
# SWASTHYA SAMANVAY — RENDER BACKEND MASTER CONFIGURATION
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. APPLICATION RUNTIME & NETWORKING
# ------------------------------------------------------------------------------

# Application mode: 'demo' (for free tier with simulated email) or 'production' (requires real SMTP)
ENVIRONMENT=demo

# Server binding (Render automatically supplies PORT; HOST should be 0.0.0.0)
HOST=0.0.0.0
# PORT is automatically injected by Render (default 8000 for local/Docker)

# Live Frontend URL (used to generate activation and password reset links)
PORTAL_BASE_URL=https://REPLACE_WITH_YOUR_VERCEL_FRONTEND_URL.vercel.app

# Allowed CORS Origins (comma-separated, without trailing slashes)
CORS_ORIGINS=https://REPLACE_WITH_YOUR_VERCEL_FRONTEND_URL.vercel.app,http://localhost:3000

# ------------------------------------------------------------------------------
# 2. DATABASE CONFIGURATION (PostgreSQL)
# ------------------------------------------------------------------------------

# Master PostgreSQL Connection URI
# Format: postgresql://[user]:[password]@[host]:[port]/[database]?sslmode=require
DATABASE_URL=postgresql://sih_admin:REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/sih_hospital_prod?sslmode=require

# Database Connection Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=5
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# ------------------------------------------------------------------------------
# 3. DISTRIBUTED CACHE & SESSION REVOCATION (Redis)
# ------------------------------------------------------------------------------

# Hosted Redis Connection URI (e.g. Upstash Redis)
# Format: rediss://default:[password]@[host]:[port]
REDIS_URL=rediss://default:REPLACE_WITH_REDIS_PASSWORD@REPLACE_WITH_REDIS_HOST:6379

# Enforce Redis connectivity at startup (set to false for free single-instance demo)
REDIS_REQUIRED=false

# ------------------------------------------------------------------------------
# 4. AUTHENTICATION & JWT CRYPTOGRAPHY
# ------------------------------------------------------------------------------

# Master Secret Key for signing JWT access tokens (Minimum 32 characters; 64 recommended)
# Generate via: python3 -c "import secrets; print(secrets.token_urlsafe(48))"
JWT_SECRET_KEY=REPLACE_WITH_64_CHARACTER_RANDOM_CRYPTOGRAPHIC_KEY_STRING

# Cryptographic signing algorithm (locked to HS256)
JWT_ALGORITHM=HS256

# Operational hospital staff token expiration in minutes (default: 60)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60

# Public applicant registration session token expiration in minutes (default: 1440 = 24h)
APPLICANT_JWT_EXPIRE_MINUTES=1440

# ------------------------------------------------------------------------------
# 5. EMAIL GATEWAY & OTP PROVIDER
# ------------------------------------------------------------------------------

# Email backend: 'simulated' (for demo logs), 'mailjet' (HTTPS API for cloud/Render), or 'smtp' (for real live delivery)
SIH_EMAIL_BACKEND=simulated

# OTP verification channel: 'SIMULATED' (for demo logs) or 'EMAIL' (for SMTP/Mailjet dispatch)
SIH_OTP_PROVIDER=SIMULATED

# Mailjet HTTPS Send API v3.1 Configuration (Required ONLY if SIH_EMAIL_BACKEND=mailjet)
# Ideal for Render Free Tier where outbound SMTP ports (25, 465, 587) are blocked.
MAILJET_API_KEY=REPLACE_WITH_YOUR_MAILJET_API_KEY
MAILJET_SECRET_KEY=REPLACE_WITH_YOUR_MAILJET_SECRET_KEY

# SMTP Gateway Configuration (Required ONLY if SIH_EMAIL_BACKEND=smtp)
# For Gmail: Use smtp.gmail.com with port 587 and a 16-character Google App Password
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=pawanbussiness108@gmail.com
SMTP_PASSWORD=REPLACE_WITH_16_CHAR_GMAIL_APP_PASSWORD
SMTP_FROM_EMAIL=pawanbussiness108@gmail.com
SMTP_USE_TLS=true
SMTP_TIMEOUT=10

# ------------------------------------------------------------------------------
# 6. TRANSACTIONAL OUTBOX WORKER
# ------------------------------------------------------------------------------

# Outbox polling interval in seconds
OUTBOX_POLL_INTERVAL=5.0

# Batch size per processing loop
OUTBOX_BATCH_SIZE=10

# Worker lease timeout in seconds before stale jobs are reclaimed
OUTBOX_LEASE_TIMEOUT_SECONDS=300

# Maximum delivery retry attempts before moving to DEAD_LETTER
OUTBOX_MAX_RETRIES=5

# ------------------------------------------------------------------------------
# 7. DOCUMENT STORAGE & SECURITY
# ------------------------------------------------------------------------------

# Local mount or temporary storage directory for uploaded accreditation PDFs/images
STORAGE_BASE_DIR=/tmp/sih_hospital_documents

# Maximum allowable file upload size in megabytes
MAX_DOCUMENT_SIZE_MB=25

# Antivirus scan verification (SimulatedScanner in demo; ClamAV in production)
ENABLE_MALWARE_SCAN=true

# S3 / Cloudflare R2 / MinIO Storage (Optional; default is 'local')
# Requires 'boto3' installed in environment
# SIH_STORAGE_BACKEND=s3
# SIH_S3_BUCKET=swasthya-samanvay-documents
# SIH_S3_ENDPOINT_URL=https://REPLACE_WITH_R2_OR_S3_ENDPOINT_URL
# SIH_S3_ACCESS_KEY=REPLACE_WITH_S3_ACCESS_KEY
# SIH_S3_SECRET_KEY=REPLACE_WITH_S3_SECRET_KEY
```

---

## 3. Environment Variable Validation Matrix

| Variable | Platform | Required in Demo? | Required in Production? | Failure Mode if Missing / Invalid |
| :--- | :--- | :---: | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | Vercel | **Yes** | **Yes** | Frontend defaults to `http://localhost:8050`, causing network errors on live site. |
| `ENVIRONMENT` | Render | **Yes** | **Yes** | Defaults to `development`. If set to `production` without SMTP, startup aborts with `RuntimeError`. |
| `DATABASE_URL` | Render | **Yes** | **Yes** | Defaults to local SQLite file; in production, PostgreSQL is mandatory. |
| `JWT_SECRET_KEY` | Render | **Yes** | **Yes** | In production, strings < 32 characters or default strings abort startup immediately. |
| `CORS_ORIGINS` | Render | **Yes** | **Yes** | Browser blocks cross-origin API calls with CORS headers mismatch error. |
| `PORTAL_BASE_URL` | Render | **Yes** | **Yes** | Activation and password reset links in emails point to `http://localhost:3000`. |
| `REDIS_URL` | Render | No | Recommended | If `REDIS_REQUIRED=true`, missing Redis URL halts startup. |
| `SIH_EMAIL_BACKEND` | Render | No (`simulated`) | **Yes (`smtp`)** | In `production`, setting `simulated` triggers startup validation failure. |
| `SMTP_PASSWORD` | Render | No | **Yes** | Email delivery fails with authentication error. |
