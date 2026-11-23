# SWASTHYA SAMANVAY — Production Release Manifest

## Release Overview
- **Project**: SWASTHYA SAMANVAY (AI-Powered Smart Hospital Referral & Bed Management Grid)
- **Target Repository**: `https://github.com/codeswith-pawan/SIH-Hospital-AI.git`
- **Branch**: `master`
- **Release Objective**: Production-ready, clean, secure GitHub release containing only files required to build, test, and deploy the platform.

---

## 1. Selected Categories & Inclusion Rationale

| Category | Path / Pattern | Purpose & Rationale |
| :--- | :--- | :--- |
| **Backend Core & API** | `src/` | Complete FastAPI service layer, ORM models, routers, prediction pipeline, auth, and background workers. |
| **Frontend Application** | `frontend/` (excluding caches/node_modules) | Next.js 15 App Router interface, Tailwind dark command theme, bilingual i18n, reviewer and department portals. |
| **Database Migrations** | `migrations/` | Versioned PostgreSQL DDL migrations for fresh deployment setup. |
| **Test Suites** | `tests/` | 450+ unit, integration, and security regression tests with SQLite/in-memory isolation. |
| **Operations & Scripts** | `scripts/` | Database seeders, verification scripts, and migration utilities. |
| **Deployment Config** | `render.yaml`, `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.prod.yml` | Declarative cloud hosting manifests for Render and containerization. |
| **Documentation** | `README.md`, `DEPLOYMENT_GUIDE.md`, `DEPLOYMENT_CHECKLIST.md`, `DEPLOYMENT_ENV_TEMPLATE.md`, `docs/` | Comprehensive architectural, deployment, and onboarding documentation. |
| **Configuration Templates** | `.env.example`, `.env.production.example`, `frontend/.env.example` | Sanitized environment variable templates containing zero real credentials. |
| **Repository Rules** | `.gitignore`, `frontend/.gitignore`, `.dockerignore` | Hardened ignore patterns preventing accidental commit of local caches, secrets, and artifacts. |

---

## 2. Intentionally Excluded Files

The following files and directories are strictly excluded from the release via `.gitignore`:
1. **Real Secret & Config Files**: `.env`, `.env.local`, `.env.production`, `.env.*`.
2. **Local Database & Cache Files**: `data/*.db`, `data/runtime/`, `.pytest_cache/`, `*.pyc`, `__pycache__/`, `*.sqlite`.
3. **Dependencies & Build Outputs**: `node_modules/`, `frontend/.next/`, `frontend/out/`, `.venv/`, `.venv-*/`.
4. **Internal Audit & Phase Reports**: `PHASE_*.md`, `phase*.md`, `INVENTORY_ACCOUNTING_*.md`, `BREVO_SMTP_*.md`, etc.
5. **Operating System Artifacts**: `.DS_Store`, `Thumbs.db`.
6. **IDE & AI Assistant Artifacts**: `.vscode/`, `.idea/`, `.gemini/`, `.antigravity/`.
7. **Developer Stashes & Conflict Files**: Git stashes (`stash@{0}`), `* 2.*` duplicate copies, `*.backup`.

---

## 3. Security Checks Performed

- [x] **Automated Regex Secret Audit**: Scanned all tracked files for high-entropy tokens, AWS keys, Brevo keys, Google API keys, GitHub PATs, and private keys (0 found).
- [x] **Git History Audit**: Inspected recent commit diffs (`git log -p -50`) to verify no credentials entered historical commits (0 found).
- [x] **Environment Template Audit**: Verified that `.env.example`, `.env.production.example`, and `frontend/.env.example` contain strictly placeholder values (`your_mailjet_api_key_here`, `REPLACE_WITH_...`).
- [x] **Isolated Database Check**: Verified that test suite runs entirely with in-memory SQLite / mock databases without touching `sih_hospital_dev`.
- [x] **CORS & Domain Verification**: Confirmed allowed origins cover Vercel production frontend domains and Render backend URLs.

---

## 4. Test Commands Executed & Results

- **Backend Pytest Suite**:
  - Command: `.venv/bin/pytest -q`
  - Result: **452 passed, 0 failures, 0 errors** in 46.88s.
- **Frontend Type Checking & Build**:
  - Command: `cd frontend && npm run build`
  - Result: **Successfully compiled (30/30 pages static/dynamic) with 0 errors**.
- **Purnea Alias & Jurisdiction Suite**:
  - Command: `.venv/bin/pytest tests/test_purnea_alias_and_reviewer_queue.py`
  - Result: **2 passed, 0 failures** in 1.35s.

---

## 5. Known Limitations & Notes
- Outbound transactional emails on cloud deployment require Mailjet API keys (`MAILJET_API_KEY` / `MAILJET_SECRET_KEY`) or Gmail App Password configured in the host environment variables.
- Production PostgreSQL requires `pgcrypto` / `uuid-ossp` extensions enabled (handled by `001_initial_postgresql_schema.sql`).
