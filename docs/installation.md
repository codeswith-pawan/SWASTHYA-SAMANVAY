# Installation & Local Setup Guide

**Project:** ArogyaSetu Grid — Unified Critical Care & Hospital Command Network (`SIH_Hospital_AI`)

This guide walks through setting up the complete ArogyaSetu Grid platform on a local machine for development, testing, and evaluation.

---

## 1. Prerequisites

Ensure the following tools are installed:
- **Python:** 3.10 to 3.14+ (tested on Python 3.14.3)
- **Node.js:** v18.18+ or v20+ (tested on Node v20/v22)
- **PostgreSQL:** Version 14, 15, 16, or 17 (or use SQLite for lightweight testing)
- **Git:** Version 2.30+
- **Redis (Optional):** Version 7+ (in-memory fallback is active when Redis is absent)

---

## 2. Clone the Repository

```bash
git clone https://github.com/codeswith-pawan/SIH-Hospital-AI.git
cd SIH-Hospital-AI
```

---

## 3. Backend Setup (FastAPI)

### Step 3.1: Create a Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS / Linux:
source .venv/bin/activate
# On Windows (cmd.exe):
.venv\Scripts\activate.bat
# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### Step 3.2: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3.3: Configure Environment Variables

```bash
cp .env.example .env
```

Review `.env`:
- By default, `DATABASE_URL=sqlite:///data/hospital_app.db` allows instant local testing without configuring PostgreSQL.
- For full PostgreSQL testing, set:
  ```env
  DATABASE_URL=postgresql://postgres:password@localhost:5432/arogyasetu_local
  ```

### Step 3.4: Seed the Database (Optional)

```bash
# Seed multi-district hospitals across Bihar and key regional hubs
python3 scripts/seed_regional_hospital_network.py
```

### Step 3.5: Start the Backend Server

```bash
# Start backend on http://localhost:8000 (or port 8050)
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify backend health:
```bash
curl http://localhost:8000/health/ready
# Expected: {"ready": true, "database": {"status": "HEALTHY"}}
```

Interactive API documentation will be available at:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 4. Frontend Setup (Next.js 16)

Open a new terminal window:

```bash
cd SIH-Hospital-AI/frontend

# Install dependencies
npm install

# Build or run development server
npm run dev
```

The frontend application will be live at:
- **URL:** [http://localhost:3000](http://localhost:3000)

---

## 5. Running Tests

### Backend Tests (pytest)
```bash
# Run complete test suite (427 tests)
pytest -v
```

### Frontend Typecheck & Build
```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## 6. Default Administrative & Hospital Logins

In development mode with seeded regional data, test credentials follow this format:
- **Hospital Login (`/portal/hospital/login`):**
  - Username: `gh99927` (Purnea Hospital) or `gh_bih_pat_01` (AIIMS Patna)
  - Password: `Hospital@123`
- **District Login (`/portal/district/login`):**
  - Username: `amritsar_district_admin`
  - Password: `District@123`
- **State Login (`/portal/state/login`):**
  - Username: `punjab_admin`
  - Password: `State@123`
- **Central Login (`/portal/central/login`):**
  - Username: `central_admin`
  - Password: `Central@123`
