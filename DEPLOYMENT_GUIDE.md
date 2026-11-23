# SWASTHYA SAMANVAY — Production & Demo Deployment Guide
**Unified Critical Care & Hospital Coordination Platform**  
*Step-by-Step Architecture Setup: Vercel (Frontend), Render (Backend & Workers), PostgreSQL & Hosted Redis*

---

## 1. Architecture & Deployment Overview

The **SWASTHYA SAMANVAY** platform comprises three distinct operational tiers:

```mermaid
flowchart TD
    Client["Browser / Client (Desktop & Mobile)"] -->|HTTPS / Next.js| Vercel["Frontend Tier: Vercel\nNext.js 16 + React 19\nswasthya-samanvay.vercel.app"]
    Vercel -->|REST API / CORS| RenderAPI["Backend Tier: Render Web Service\nFastAPI (Python 3.11 / 3.14)\nswasthya-samanvay-api.onrender.com"]
    RenderAPI -->|TCP / SSL| Postgres["Database Tier: PostgreSQL 16+\n(Render PostgreSQL, Neon, or Supabase)"]
    RenderAPI -->|TCP / TLS| Redis["Cache & Distributed Revocation\n(Upstash Redis or Hosted Redis)"]
    RenderWorkers["Background Workers Tier\n(Outbox & Bed Expiry Workers)"] -->|Poll & Heartbeat| Postgres
    RenderWorkers -->|SMTP TLS| MailServer["Transactional Email Gateway\n(Gmail SMTP or Custom SMTP Relay)"]
```

---

## 2. Vercel Frontend Setup

### 2.1 Project Configuration
1. Log into your [Vercel Dashboard](https://vercel.com/) and click **Add New...** → **Project**.
2. Import your GitHub repository: `codeswith-pawan/SIH-Hospital-AI`.
3. Configure the build parameters:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click *Edit* and select `frontend`.
   - **Build Command:** `npm run build` (or leave default).
   - **Output Directory:** `.next` (default).
   - **Install Command:** `npm install` (default).

### 2.2 Environment Variables (Vercel)
Add the following environment variables under **Project Settings → Environment Variables**:

| Variable Name | Required | Example / Target Value | Description |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | **Yes** | `https://swasthya-samanvay-api.onrender.com` | Base URL of your live Render backend API (no trailing slash). |
| `NEXT_PUBLIC_API_BASE_URL` | Optional | `https://swasthya-samanvay-api.onrender.com` | Fallback alias for backend API base URL. |
| `NODE_ENV` | Optional | `production` | Production environment flag. |

---

## 3. Render Backend Setup

### 3.1 Web Service Configuration
1. Log into your [Render Dashboard](https://dashboard.render.com/) and click **New +** → **Web Service**.
2. Connect your GitHub repository: `codeswith-pawan/SIH-Hospital-AI`.
3. Configure the service settings:
   - **Name:** `swasthya-samanvay-api`
   - **Region:** Choose the region closest to your database (e.g. `Oregon (US West)` or `Frankfurt (EU)`).
   - **Branch:** `master`
   - **Root Directory:** Leave blank (repository root).
   - **Runtime:** `Python`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn src.api.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Instance Type:** `Free` (or `Starter` for persistent uptime).

### 3.2 Health Check Configuration on Render
- In **Advanced Settings**, set the **Health Check Path** to:
  ```text
  /health/live
  ```
  *(Render will probe this endpoint every few seconds; it returns HTTP 200 immediately upon ASGI app boot).*

---

## 4. PostgreSQL Database Provisioning & Migration

### 4.1 Provisioning (Render PostgreSQL or Neon / Supabase)
1. **Option A (Render Free PostgreSQL):**
   - In Render, click **New +** → **PostgreSQL**.
   - Name: `swasthya-samanvay-db`.
   - Database: `sih_hospital_prod`.
   - User: `sih_admin`.
   - Copy the **Internal Database URL** (for Render services) and **External Connection String** (for local CLI migration).
2. **Option B (Neon / Supabase Serverless Postgres):**
   - Create a free project and copy the `postgresql://...` connection string with `?sslmode=require`.

### 4.2 Safe Sequential Database Migration
Execute migrations in strict numerical order from your local terminal using the external connection string:

```bash
# Set your temporary migration target URL
export PROD_DB_URL="postgresql://user:password@host:port/database?sslmode=require"

# Apply migrations 001 through 006 sequentially
psql "$PROD_DB_URL" -f migrations/001_initial_postgresql_schema.sql
psql "$PROD_DB_URL" -f migrations/002_referral_workflow_and_notifications.sql
psql "$PROD_DB_URL" -f migrations/003_registration_system.sql
psql "$PROD_DB_URL" -f migrations/004_category_occupancy_counters.sql
psql "$PROD_DB_URL" -f migrations/005_worker_heartbeats.sql
psql "$PROD_DB_URL" -f migrations/006_workflow_notifications.sql
```

*(Alternatively, run the SQLAlchemy ORM bootstrap:)*
```bash
DATABASE_URL="$PROD_DB_URL" python -c "from src.database.pg_models import PgBase; from src.database.db_manager import get_engine; PgBase.metadata.create_all(get_engine()); print('All PostgreSQL tables initialized.')"
```

---

## 5. Redis Provisioning & Configuration

The application utilizes Redis for distributed JWT token revocation blocklisting and session cutoff synchronization across multiple instances.

### 5.1 Free Hosted Redis Setup (Upstash Redis)
1. Go to [Upstash](https://upstash.com/) and create a free Redis database.
2. Select the cloud region nearest to your Render backend.
3. Under the **Details** tab, copy the **Redis URL** (format: `rediss://default:password@hostname:port`).

### 5.2 Render Configuration
- Set `REDIS_URL` in your Render Environment Variables to the Upstash URL.
- If using free-tier single-instance Render where Redis is optional, set `REDIS_REQUIRED=false`. The application will utilize its thread-safe in-memory revocation cache.
- For true multi-node clustered deployments, set `REDIS_REQUIRED=true`.

---

## 6. Email & SMTP Configuration

### 6.1 Mode A: Demo Deployment (Simulated Emails & Instant Console OTP)
For a free demo deployment where real email delivery is not required:
- Set `ENVIRONMENT=demo` on Render.
- Set `SIH_EMAIL_BACKEND=simulated`.
- Set `SIH_OTP_PROVIDER=SIMULATED`.
- *Result:* The backend will boot cleanly, OTPs and activation links will be logged to the Render service logs, and no external SMTP provider is needed.

### 6.2 Mode B: Production Live Delivery (Gmail SMTP)
To deliver real verification emails and OTPs to user inboxes:
1. Generate a **Google App Password**:
   - Go to [Google Account Security](https://myaccount.google.com/security).
   - Enable **2-Step Verification**.
   - Navigate to **App passwords** (`https://myaccount.google.com/apppasswords`).
   - Create an app named `Swasthya Samanvay` and copy the 16-character code (e.g. `abcd efgh ijkl mnop`).
2. Set the following environment variables on Render:
   - `ENVIRONMENT=production`
   - `SIH_EMAIL_BACKEND=smtp`
   - `SIH_OTP_PROVIDER=EMAIL`
   - `SMTP_HOST=smtp.gmail.com`
   - `SMTP_PORT=587`
   - `SMTP_USERNAME=pawanbussiness108@gmail.com`
   - `SMTP_PASSWORD=abcdefghijklmnop` *(your 16-char app password without spaces)*
   - `SMTP_FROM_EMAIL=pawanbussiness108@gmail.com`
   - `SMTP_USE_TLS=true`

---

## 7. CORS Origin Configuration

To prevent browser Cross-Origin Resource Sharing (CORS) rejections:
1. In `src/api/main.py`, the backend automatically allows any Vercel preview or production domain matching:
   ```text
   ^https://(swasthya-samanvay|arogyasetu-grid)(-[a-zA-Z0-9_-]+)?\.vercel\.app$
   ```
2. In the Render environment settings, configure `CORS_ORIGINS` to include your exact frontend URL:
   ```text
   CORS_ORIGINS=https://swasthya-samanvay.vercel.app,http://localhost:3000
   ```
3. Set `PORTAL_BASE_URL` on Render to your frontend URL:
   ```text
   PORTAL_BASE_URL=https://swasthya-samanvay.vercel.app
   ```
   *(This ensures account activation and password reset emails generate links pointing to the live frontend).*

---

## 8. Health Check Verification & Diagnostics

Once deployed, verify backend health using `curl` or a web browser:

1. **Liveness Probe:**
   ```bash
   curl -i https://<your-render-backend-url>/health/live
   ```
   *Expected Response:* HTTP `200 OK` with JSON `{"status": "alive"}`.

2. **Readiness Probe:**
   ```bash
   curl -i https://<your-render-backend-url>/health/ready
   ```
   *Expected Response:* HTTP `200 OK` with JSON:
   ```json
   {
     "ready": true,
     "database": {"status": "HEALTHY", "dialect": "postgresql"},
     "redis": {"status": "HEALTHY"},
     "environment": "demo"
   }
   ```

3. **Public API Endpoint:**
   ```bash
   curl -i https://<your-render-backend-url>/api/registration/applications/stats/public
   ```
   *Expected Response:* HTTP `200 OK` with public platform statistics.

---

## 9. Free-Tier Limitations & Operational Constraints

> [!WARNING]
> Please note the following constraints when deploying to free cloud tiers:

1. **Render Free Web Service Sleep Mode:**
   - Free Render web services automatically spin down (sleep) after **15 minutes of inactivity**.
   - The first request after a sleep period can experience a **30 to 50 second cold-start latency**.
   - *Mitigation:* Use a free external uptime monitor (such as UptimeRobot or Cron-job.org) to ping `/health/live` every 10 minutes.
2. **Ephemeral Document Storage:**
   - On Render's free tier, local disk storage (`/tmp/sih_hospital_documents`) is ephemeral and resets on restart.
   - *Mitigation:* For permanent document storage across restarts, install `boto3` and configure AWS S3 / Cloudflare R2 bucket credentials via `SIH_STORAGE_BACKEND=s3`, `SIH_S3_BUCKET`, `SIH_S3_ACCESS_KEY`, and `SIH_S3_SECRET_KEY`, or attach a persistent Render disk volume to `/var/lib/sih/documents`.
3. **Render Free PostgreSQL Retention:**
   - Render's free PostgreSQL instances expire after 30 days unless upgraded.
   - *Mitigation:* For persistent demo hosting, use Neon Serverless Postgres or Supabase free tier, which do not expire active projects.

---

## 10. Troubleshooting Guide

| Symptom / Error | Root Cause | Exact Resolution |
| :--- | :--- | :--- |
| **CORS policy error in browser console** | `CORS_ORIGINS` does not match the exact frontend URL scheme/domain. | Add `https://<your-vercel-domain>.vercel.app` to `CORS_ORIGINS` on Render (no trailing slash). |
| **503 Service Unavailable on `/health/ready`** | Backend cannot connect to PostgreSQL or Redis. | Verify `DATABASE_URL` credentials and ensure `?sslmode=require` is appended if using remote Postgres. |
| **Startup Crash with `CRITICAL PRODUCTION CONFIGURATION INVARIANT`** | `ENVIRONMENT=production` was set while using `SIH_EMAIL_BACKEND=simulated`. | Either set `ENVIRONMENT=demo` for simulated mode, or provide full Gmail SMTP credentials. |
| **JWT Invalid or Expired Token on login** | `JWT_SECRET_KEY` was regenerated or is mismatched across instances. | Ensure `JWT_SECRET_KEY` is explicitly set to a static 64-character secret in Render environment variables. |
| **404 Not Found on API routes** | `NEXT_PUBLIC_API_URL` on Vercel is pointing to `localhost`. | Set `NEXT_PUBLIC_API_URL=https://<your-backend>.onrender.com` in Vercel settings and trigger a **Redeploy**. |
