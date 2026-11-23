# SWASTHYA SAMANVAY — Production Deployment Checklist
**Final Operational Verification & Step-by-Step Execution Runbook**

---

## Stage 1: Pre-Deployment Verification (Local)

- [ ] **Backend Test Suite Validation:**
  ```bash
  ./.venv/bin/pytest -q
  # Must report: 432 passed (100% passing)
  ```
- [ ] **Security Regression Suite Validation:**
  ```bash
  ./.venv/bin/pytest tests/test_phase5_security_audit.py -vv
  # Must report: 5 passed (100% passing)
  ```
- [ ] **Frontend TypeScript Validation:**
  ```bash
  cd frontend && npx tsc --noEmit
  # Must exit with code 0 (zero errors)
  ```
- [ ] **Frontend Production Build Validation:**
  ```bash
  cd frontend && npm run build
  # Must compile all 29 routes successfully
  ```
- [ ] **Git Repository State Verification:**
  ```bash
  git status
  # Verify working tree cleanliness and ensure no private secrets or .env files are staged
  ```

---

## Stage 2: Database Provisioning & Schema Migration

- [ ] **Provision PostgreSQL Instance:**
  - Create database on Render, Neon, or Supabase.
  - Obtain the SSL-enabled connection string: `postgresql://user:password@host:port/database?sslmode=require`.
- [ ] **Run Sequential Schema Migrations (001 → 006):**
  ```bash
  export PROD_DB_URL="postgresql://user:password@host:port/database?sslmode=require"

  psql "$PROD_DB_URL" -f migrations/001_initial_postgresql_schema.sql
  psql "$PROD_DB_URL" -f migrations/002_referral_workflow_and_notifications.sql
  psql "$PROD_DB_URL" -f migrations/003_registration_system.sql
  psql "$PROD_DB_URL" -f migrations/004_category_occupancy_counters.sql
  psql "$PROD_DB_URL" -f migrations/005_worker_heartbeats.sql
  psql "$PROD_DB_URL" -f migrations/006_workflow_notifications.sql
  ```
- [ ] **Seed Base Roles & Master Records:**
  ```bash
  psql "$PROD_DB_URL" -c "INSERT INTO roles (id, description) VALUES ('HOSPITAL', 'Hospital Staff'), ('DISTRICT_ADMIN', 'District Admin'), ('STATE_ADMIN', 'State Admin'), ('CENTRAL_ADMIN', 'Central Admin') ON CONFLICT DO NOTHING;"
  ```
- [ ] **Verify Tables Created:**
  ```bash
  psql "$PROD_DB_URL" -c "\dt"
  # Confirm tables exist: hospitals, users, roles, patients, referrals, beds, bed_reservations, registration_applications, registration_documents, approval_history, registration_email_outbox
  ```

---

## Stage 3: Redis Provisioning (Optional for Demo / Required for Multi-Node)

- [ ] **Create Hosted Redis Database:**
  - Create free Redis database on Upstash or Render.
  - Copy the TLS connection URL: `rediss://default:password@host:port`.
- [ ] **Test Redis Connectivity:**
  ```bash
  redis-cli -u "rediss://default:password@host:port" ping
  # Must respond: PONG
  ```

---

## Stage 4: Backend Web Service Setup (Render)

- [ ] **Create Render Web Service:**
  - Name: `swasthya-samanvay-api`
  - Runtime: `Python`
  - Branch: `master`
  - Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
  - Start Command: `uvicorn src.api.main:app --host 0.0.0.0 --port $PORT`
  - Health Check Path: `/health/live`
- [ ] **Configure Render Environment Variables:**
  - `ENVIRONMENT=demo` *(or `production` if real SMTP configured)*
  - `PORTAL_BASE_URL=https://<your-app>.vercel.app`
  - `CORS_ORIGINS=https://<your-app>.vercel.app,http://localhost:3000`
  - `DATABASE_URL=postgresql://...`
  - `JWT_SECRET_KEY=<generate-64-char-random-key>`
  - `REDIS_URL=rediss://...` *(or leave blank if REDIS_REQUIRED=false)*
  - `REDIS_REQUIRED=false` *(or `true` if Redis provisioned)*
  - `SIH_EMAIL_BACKEND=simulated` *(or `smtp`)*
  - `SIH_OTP_PROVIDER=SIMULATED` *(or `EMAIL`)*
  - `SMTP_FROM_EMAIL=pawanbussiness108@gmail.com`
- [ ] **Trigger Initial Deploy & Monitor Logs:**
  - Verify ASGI server starts on `$PORT`.
  - Check log output for `"Production configuration audit PASSED"`.

---

## Stage 5: Frontend Web Service Setup (Vercel)

- [ ] **Create Vercel Project:**
  - Connect GitHub repository `codeswith-pawan/SIH-Hospital-AI`.
  - Framework Preset: `Next.js`.
  - Root Directory: `frontend`.
- [ ] **Configure Vercel Environment Variables:**
  - `NEXT_PUBLIC_API_URL=https://swasthya-samanvay-api.onrender.com`
  - `NEXT_PUBLIC_API_BASE_URL=https://swasthya-samanvay-api.onrender.com`
  - `NODE_ENV=production`
- [ ] **Deploy Vercel Project:**
  - Confirm build compiles cleanly without errors.
  - Note assigned production domain (e.g. `https://swasthya-samanvay.vercel.app`).
- [ ] **Sync Frontend Domain to Backend CORS:**
  - If the assigned Vercel URL differs from initial guess, update `CORS_ORIGINS` and `PORTAL_BASE_URL` on Render.

---

## Stage 6: Integration & End-to-End Smoke Testing

- [ ] **1. Test Backend Liveness Endpoint:**
  ```bash
  curl -i https://swasthya-samanvay-api.onrender.com/health/live
  # Must return: HTTP 200 {"status": "alive"}
  ```
- [ ] **2. Test Backend Readiness Endpoint:**
  ```bash
  curl -i https://swasthya-samanvay-api.onrender.com/health/ready
  # Must return: HTTP 200 with "ready": true
  ```
- [ ] **3. Test Public Application Stats:**
  ```bash
  curl -i https://swasthya-samanvay-api.onrender.com/api/registration/applications/stats/public
  # Must return: HTTP 200 with JSON stats
  ```
- [ ] **4. Test CORS Preflight Request:**
  ```bash
  curl -I -X OPTIONS https://swasthya-samanvay-api.onrender.com/health \
    -H "Origin: https://swasthya-samanvay.vercel.app" \
    -H "Access-Control-Request-Method: GET"
  # Must return: Access-Control-Allow-Origin: https://swasthya-samanvay.vercel.app
  ```
- [ ] **5. Test Frontend Portal Landing Page:**
  - Open `https://<your-app>.vercel.app` in browser.
  - Verify hero banner displays **SWASTHYA SAMANVAY**.
  - Toggle language between English and हिन्दी.
- [ ] **6. Test Registration Hub:**
  - Navigate to `/register` and `/register/hospital`.
  - Verify registration form loads without console errors.
- [ ] **7. Test Departmental Login:**
  - Navigate to `/portal` and `/portal/hospital/login`.
  - Verify form fields and error handling render properly.

---

## Stage 7: Operational Notes & Free-Tier Limitations

| Component | Free-Tier Behavior | Operational Impact | Recommended Action |
| :--- | :--- | :--- | :--- |
| **Render Web Service** | Spins down after 15 min inactivity | 30–50s initial cold-start delay | Ping `/health/live` every 10 min using an external monitor (e.g. UptimeRobot). |
| **Render PostgreSQL** | Free instances expire after 30 days | Data loss after 30 days | Use Neon Serverless Postgres or Supabase free tier for permanent non-expiring storage. |
| **Document Storage** | Ephemeral `/tmp` storage resets on restart | Uploaded PDFs disappear on service restart | For permanent document persistence, configure S3/Cloudflare R2 credentials. |
| **Simulated Email** | Simulated backend logs OTP to console | Users cannot receive emails in their inbox | Configure Google App Password with Gmail SMTP when live delivery is required. |
