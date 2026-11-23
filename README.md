# SWASTHYA SAMANVAY
**Multi-Tier Hospital Onboarding, Live Bed Visibility & Inter-Facility Referral Coordination Platform**

[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://swasthya-samanvay.onrender.com/docs)
[![Frontend](https://img.shields.io/badge/Frontend-Next.js%2015%20%7C%20React%2019-000000?style=flat-square&logo=next.js&logoColor=white)](https://swasthya-samanvay-ujxm.vercel.app)
[![Database](https://img.shields.io/badge/Database-PostgreSQL%2016+-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/Tests-452%20Passing-success?style=flat-square)](tests/)
[![Bilingual](https://img.shields.io/badge/Language-English%20%7C%20हिन्दी-teal?style=flat-square)](https://swasthya-samanvay-ujxm.vercel.app)

---

## Live Deployments

- **Live Web Application (Vercel):** [https://swasthya-samanvay-ujxm.vercel.app](https://swasthya-samanvay-ujxm.vercel.app)
- **Production API Gateway (Render):** [https://swasthya-samanvay.onrender.com](https://swasthya-samanvay.onrender.com)
- **Interactive OpenAPI Documentation:** [https://swasthya-samanvay.onrender.com/docs](https://swasthya-samanvay.onrender.com/docs)
- **System Health Endpoint:** [https://swasthya-samanvay.onrender.com/health/live](https://swasthya-samanvay.onrender.com/health/live)

> **Demonstration Notice:** SWASTHYA SAMANVAY is an engineering prototype developed for technical demonstration, architectural evaluation, and academic presentation. It is not an officially operated Government of India healthcare portal and does not replace certified clinical emergency dispatch systems.

---

## Interface Preview

### 1. Department Portal Gateway & Role Selector
![Department Portal Gateway](docs/screenshots/01-landing-portal.png)
*Role-isolated departmental sign-in gateways for Hospital, District, State, and Central administrative tiers.*

### 2. Multi-Step Hospital Onboarding & Compliance Submission
![Hospital Onboarding & Accreditation](docs/screenshots/02-hospital-registration.png)
*Four-stage facility registration wizard with statutory document upload (Clinical License, Fire NOC) and hierarchy validation.*

### 3. District Health Operations Console
![District Health Operations Console](docs/screenshots/03-district-dashboard.png)
*District administrative surveillance displaying live bed occupancy, ICU capacity, active facilities, and accreditation queues.*

### 4. State Health Command & Regional Capacity Dashboard
![State Health Command & Capacity Dashboard](docs/screenshots/04-state-command-dashboard.png)
*State-level health command tracking cross-district patient movement, regional occupancy rates, and facility accreditations.*

### 5. Frontline Hospital Operations & Referral Desk
![Frontline Hospital Operations](docs/screenshots/05-hospital-referral-desk.png)
*Hospital operational console for real-time general/ICU bed allocation, patient admission intake, and inter-facility transfers.*

---

## What the Platform Does

SWASTHYA SAMANVAY addresses critical delays in inter-hospital patient transfers and emergency bed coordination through a secure, multi-tier digital architecture:

1. **Hospital Onboarding & Accreditation:** Structured self-registration for public and private healthcare facilities with statutory compliance document upload (Clinical License, Fire Safety NOC), anti-tamper SHA-256 checksum verification, and nodal officer validation.
2. **Three-Tier Jurisdiction Review:** Sequential governance approval workflow across **District ➔ State ➔ Central** administrative authorities with strict geographical access isolation.
3. **Automated Account Provisioning:** Upon central sign-off, system generates secure user accounts with 72-hour cryptographic activation links delivered via transactional email.
4. **Live Bed & Critical Care Accounting:** Real-time visibility into general, ICU, oxygen, and emergency beds across registered institutions.
5. **Atomic Bed Reservation Locks:** Immediate row-level reservation locks (`SELECT FOR UPDATE`) preventing race conditions, phantom availability, and double-booking during transit.
6. **Background Expiry Automation:** Dedicated background workers monitoring active reservations with automated 30-minute expiry windows to release unconfirmed beds.
7. **Condition-Based Referral Recommendation:** Clinical referral engine matching patient triage vitals, required medical specialties, emergency capabilities, and Haversine geographical distance.
8. **Jurisdiction-Isolated Role-Based Access Control:** Fine-grained authorization enforcing boundary checks so reviewers and hospital staff can only access facilities and patients within their authorized domain.
9. **Full Bilingual Localization:** Complete English and Hindi interface support across all public pages, registration workflows, and operational dashboards.

---

## End-to-End Operational Workflow

```
[ Frontline Hospital ]
        │
        ▼ 1. Self-Registration & Document Upload
  (Clinical License, Fire NOC, Nodal Officer Contact)
        │
        ▼ 2. District CMO Review (Jurisdiction Matching)
  (Physical Verification, Bed Inventory Validation)
        │
        ▼ 3. State Health Directorate Endorsement
  (Secondary Regulatory Compliance & Regional Mapping)
        │
        ▼ 4. Central Health Command Final Sign-Off
  (National Registry Enrollment & Credential Provisioning)
        │
        ▼ 5. Cryptographic Activation Link Delivered
  (72-hour PBKDF2 Password Setup via Mailjet / SMTP Outbox)
        │
        ▼ 6. Live Hospital Operations Active
  ┌────────────────────────────────────────────────────────┐
  │  • Real-time Bed & ICU Inventory Maintenance           │
  │  • Triage Intake & Condition-Based Referral Routing    │
  │  • Atomic 30-minute Bed Reservation Hold               │
  │  • Emergency Transfer Handoff & Arrival Confirmation   │
  └────────────────────────────────────────────────────────┘
```

1. **Registration:** Hospital fills institutional details, GPS coordinates, bed capacity, and uploads statutory compliance certificates.
2. **Review Pipeline:** The application moves strictly through `DISTRICT_REVIEW` ➔ `STATE_REVIEW` ➔ `CENTRAL_REVIEW`. Reviewers at each tier inspect documents, approve, request correction, or reject with auditable logging.
3. **Provisioning:** On central approval, an operational hospital account is provisioned with status `PENDING_ACTIVATION`. A single-use cryptographic token is dispatched via transactional email.
4. **Referral Routing:** Frontline staff initiating a transfer submit patient vitals, diagnosis, and required resources. The engine scores suitable network hospitals using distance, specialty matching, and real-time bed availability.
5. **Reservation & Transit:** The sending facility reserves an available bed with a 30-minute hold. The receiving facility confirms or declines; on arrival, the bed status transitions atomically to occupied.

---

## System Architecture

```mermaid
flowchart TB
    subgraph Clients["Presentation Layer (Desktop & Mobile)"]
        Browser["Next.js 15 Client<br/>(React 19, Tailwind CSS, TypeScript)<br/>swasthya-samanvay-ujxm.vercel.app"]
    end

    subgraph Edge["Hosting & Gateway"]
        Vercel["Vercel Edge Network"]
        Render["Render Web Service<br/>(FastAPI / Uvicorn)<br/>swasthya-samanvay.onrender.com"]
    end

    subgraph BackendServices["Core Application Services"]
        AuthSvc["Auth & RBAC Service<br/>(JWT, PBKDF2 Hashing)"]
        RegSvc["Registration & Audit Service<br/>(3-Tier Jurisdiction Routing)"]
        RefSvc["Referral & Matching Engine<br/>(Vitals, Acuity, Haversine)"]
        BedSvc["Bed Inventory Manager<br/>(Atomic Row-Level Locks)"]
        OutboxSvc["Transactional Outbox Engine<br/>(Asynchronous Event Delivery)"]
    end

    subgraph Workers["Background Asynchronous Workers"]
        ExpiryWorker["Reservation Expiry Worker<br/>(30-minute Hold Sweeper)"]
        EmailWorker["Outbox Dispatch Worker<br/>(Mailjet API v3.1 / SMTP)"]
    end

    subgraph DataStorage["Persistence & Cache"]
        Postgres[("PostgreSQL 16+ Database<br/>(Primary Relational Store)")]
        RedisStore[("Redis Cache<br/>(Rate Limiting & Revocation)")]
    end

    subgraph External["External Gateways"]
        MailjetGateway["Mailjet API v3.1 / Gmail SMTP<br/>(Activation & Reset Emails)"]
    end

    Browser -->|HTTPS / Next.js| Vercel
    Vercel -->|REST API / JSON| Render
    Render --> AuthSvc
    Render --> RegSvc
    Render --> RefSvc
    Render --> BedSvc
    Render --> OutboxSvc

    AuthSvc <--> Postgres
    RegSvc <--> Postgres
    RefSvc <--> Postgres
    BedSvc <--> Postgres
    OutboxSvc <--> Postgres

    AuthSvc -.-> RedisStore
    RefSvc -.-> RedisStore

    ExpiryWorker <-->|Poll & Expire| Postgres
    EmailWorker <-->|Drain Outbox| Postgres
    EmailWorker -->|HTTPS POST| MailjetGateway
```

---

## Technology Stack

| Layer | Technologies | Purpose |
|---|---|---|
| **Frontend Framework** | Next.js 15.5, React 19, TypeScript | Bilingual App Router, server-rendered components, client dashboards |
| **Styling & Icons** | Tailwind CSS v4, Lucide React | Dark command center theme, responsive grid layouts |
| **Backend Framework** | Python 3.11+, FastAPI, Pydantic v2 | High-performance asynchronous REST API gateway |
| **ORM & Database** | PostgreSQL 16+, SQLAlchemy 2.0 | Relational data persistence, connection pooling, ACID transactions |
| **Authentication** | JWT (`python-jose`), Passlib PBKDF2 | Stateless authentication, role-based access control, timed activation |
| **Caching & Security** | Redis (optional/supported) | Distributed token revocation, rate limiting |
| **Transactional Email** | Mailjet Send API v3.1, Standard SMTP | Reliable transactional email delivery over HTTPS and port 587 |
| **Testing Harness** | pytest, pytest-asyncio, Playwright | 450+ unit/integration tests, end-to-end browser automation |
| **Hosting & Cloud** | Vercel (Frontend), Render (Backend) | Globally distributed frontend, managed web service backend |

---

## Repository Structure

```text
SWASTHYA-SAMANVAY/
├── src/                          # FastAPI backend application
│   ├── api/                      # REST routers, authentication dependencies & middleware
│   │   ├── admin_routes.py       # District, State, and Central governance endpoints
│   │   ├── main.py               # Application entrypoint, CORS & lifespan lifecycle
│   │   ├── patient_routes.py     # Patient admission & clinical triage endpoints
│   │   ├── registration_routes.py# Onboarding, document upload & reviewer queue routes
│   │   └── schemas.py            # Pydantic v2 request/response schemas
│   ├── auth/                     # JWT tokens, PBKDF2 password hashing & rate limiters
│   ├── database/                 # SQLAlchemy ORM models, repository queries & seeds
│   │   ├── db_manager.py         # Database engine pooling & session management
│   │   ├── pg_models.py          # PostgreSQL tables (users, hospitals, referrals, beds)
│   │   ├── pg_repository.py      # Analytical metrics & jurisdiction aggregation queries
│   │   └── seed_network.py       # Baseline reference seed data (roles, review accounts)
│   ├── prediction/               # Clinical referral matching & reservation logic
│   ├── services/                 # Business logic services (registration, email, provisioning)
│   └── workers/                  # Asynchronous outbox worker & bed reservation expiry
├── frontend/                     # Next.js 15 full-stack frontend
│   ├── app/                      # Next.js App Router pages
│   │   ├── activate/             # Account activation & password creation
│   │   ├── portal/               # Departmental login portals (hospital, district, state, central)
│   │   ├── register/             # Hospital onboarding & application tracking
│   │   └── reviewer/             # Administrative application review workspace
│   ├── components/               # Reusable UI components & tier dashboards
│   │   ├── auth/                 # Department login components & role verification
│   │   ├── registration/         # Document uploaders, timelines, OTP modals
│   │   ├── reviewer/             # Reviewer queue table & application dossier modal
│   │   └── shared/               # Government headers, footers, stat cards, data tables
│   ├── lib/                      # Client API client, types, formatters & i18n localization
│   ├── next.config.ts            # Next.js configuration & standalone build settings
│   └── package.json              # Frontend npm dependencies
├── migrations/                   # Sequential PostgreSQL schema DDL migrations
├── tests/                        # Automated test suites (452 tests passing)
├── scripts/                      # Operational utilities, seeders & healthcheck tools
├── docs/                         # Technical documentation & operational runbooks
│   └── screenshots/              # Real live application screenshots
├── .env.example                  # Backend environment variable template
├── DEPLOYMENT_GUIDE.md           # Step-by-step production deployment guide
├── DEPLOYMENT_CHECKLIST.md       # Pre-flight and post-deployment checklist
├── render.yaml                   # Declarative Render blueprint
└── README.md                     # Repository documentation
```

---

## Local Development Setup

### Prerequisites
- Python 3.11+ (or Python 3.14)
- Node.js 18+ and npm
- PostgreSQL 15+ (or default SQLite test engine for local experiments)

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/codeswith-pawan/SIH-Hospital-AI.git
cd SIH-Hospital-AI

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install backend dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your local settings (default fallback uses SQLite if DATABASE_URL is unset)

# Run the backend API server (port 8050)
uvicorn src.api.main:app --reload --port 8050
```

The API documentation will be available at [http://localhost:8050/docs](http://localhost:8050/docs).

> **Safety Warning:** Ensure your local `.env` points to a dedicated development database. Never connect local development environments to live production databases.

### 2. Frontend Setup
```bash
# In a separate terminal, navigate to the frontend directory
cd frontend

# Install Node dependencies
npm install

# Copy environment template
cp .env.example .env.local
# Default points to http://localhost:8050 for local development

# Start Next.js development server (port 3000)
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## Production Deployment

The project is pre-configured for automated deployment on **Render** (FastAPI backend & PostgreSQL) and **Vercel** (Next.js frontend):

### Required Environment Variables

#### Backend (Render Dashboard)
| Variable | Required | Description | Example / Target Value |
|---|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL connection URI | `postgresql://user:pass@host:5432/dbname?sslmode=require` |
| `PORTAL_BASE_URL` | **Yes** | Deployed frontend origin | `https://swasthya-samanvay-ujxm.vercel.app` |
| `CORS_ORIGINS` | **Yes** | Allowed CORS origins (comma-separated) | `https://swasthya-samanvay-ujxm.vercel.app` |
| `JWT_SECRET_KEY` | **Yes** | Minimum 32-character cryptographic key | Random string (`secrets.token_urlsafe(48)`) |
| `SIH_EMAIL_BACKEND` | Optional | Email backend (`mailjet`, `smtp`, `mock`) | `mailjet` |
| `MAILJET_API_KEY` | Conditional | Mailjet Public API Key (if `SIH_EMAIL_BACKEND=mailjet`) | Valid Mailjet API Key |
| `MAILJET_SECRET_KEY` | Conditional | Mailjet Secret Key (if `SIH_EMAIL_BACKEND=mailjet`) | Valid Mailjet Secret Key |

#### Frontend (Vercel Project Settings)
| Variable | Required | Description | Example / Target Value |
|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | **Yes** | Public backend API URL | `https://swasthya-samanvay.onrender.com` |
| `NEXT_PUBLIC_API_URL` | Optional | Alias for backend API URL | `https://swasthya-samanvay.onrender.com` |

> **Cloud Free-Tier Notice:** Render free-tier web services enter sleep mode after 15 minutes of inactivity. Initial requests after dormancy may experience a 30–50 second cold-start spin-up delay.

---

## Automated Verification & Testing

Every commit is verified against backend test suites and frontend static type analysis:

### Backend Test Suite (452 Tests)
```bash
# Run pytest across all unit, integration, and security tests
pytest -q
```
*Current test status: **452 passed** in 46.88 seconds (0 failures, 0 errors) with isolated test databases.*

### Frontend Production Build & TypeScript Verification
```bash
cd frontend

# Verify strict TypeScript type compliance
npx tsc --noEmit

# Execute Next.js optimized production build
npm run build
```
*Current build status: **Successfully compiled (30/30 static and dynamic routes)** with 0 build errors.*

---

## Security Architecture & Design Controls

1. **Role-Based Access Control (RBAC):** Four discrete roles (`HOSPITAL`, `DISTRICT_ADMIN`, `STATE_ADMIN`, `CENTRAL_ADMIN`) enforce strict jurisdiction filters in database queries. A district reviewer in Purnea cannot access records from other districts.
2. **Password & Token Security:** Passwords hashed with PBKDF2-HMAC-SHA256 (310,000 rounds). Account activation tokens are single-use 72-hour SHA-256 hashes.
3. **Document Tamper Prevention:** Uploaded PDF and image files are checked for MIME integrity, size boundaries (< 10 MB), and cryptographic SHA-256 checksums.
4. **Race Condition Prevention:** Critical bed allocation uses PostgreSQL `SELECT ... FOR UPDATE` row locks to prevent simultaneous duplicate bookings across concurrent referral transfers.
5. **Audit Logging:** Every regulatory status transition generates immutable historical records (`approval_history`) capturing user ID, timestamp, tier, and client IP.

---

## Contribution & License

- **License:** No open-source license has been specified for this proprietary demonstration repository. All rights reserved.
- **Contributions:** Pull requests and issue reports should be opened against the `master` branch following standard semantic commits (`feat:`, `fix:`, `docs:`, `test:`).
- **Technical Inquiries:** Contact the maintainer at `pawanbussiness108@gmail.com`.
