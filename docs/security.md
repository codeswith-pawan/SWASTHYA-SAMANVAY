# Security Architecture & Operations Checklist

**Project:** SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform (`SIH_Hospital_AI`)

---

## 1. Security Principles & Architecture

SWASTHYA SAMANVAY enforces defense-in-depth across every layer of the platform:

1. **Role-Based Access Control (RBAC):**
   - Four distinct administrative scopes: `HOSPITAL`, `DISTRICT_ADMIN`, `STATE_ADMIN`, and `CENTRAL_ADMIN`.
   - Dedicated portal gateways enforce **Role-Mismatch Protection**, terminating unauthorized cross-tier sessions immediately.
2. **Password & Token Cryptography:**
   - User credentials hashed using PBKDF2 with SHA-256 and unique per-user cryptographic salts (`src/auth/auth_store.py`).
   - Constant-time string comparison (`hmac.compare_digest`) used during authentication to mitigate side-channel timing attacks.
   - JWT tokens signed using HS256 with short expiration windows (default: 60 minutes) and immediate revocation capabilities via Redis blocklisting.
3. **Defense Against Race Conditions:**
   - Bed reservation operations utilize explicit PostgreSQL row locks (`SELECT ... FOR UPDATE`) inside atomic database transactions to eliminate double-booking during concurrent referral requests.
4. **Document Upload Safeguards:**
   - Mandatory document size limits (max 10MB per file).
   - Strict MIME-type inspection (PDF, PNG, JPEG allowed; executable formats strictly rejected).
   - SHA-256 content checksumming prevents file tampering or duplicate submission spoofing.
5. **Patient Privacy & PHI Isolation:**
   - Public landing page and tracking interfaces do not expose any clinical history, patient identity, or diagnostic details.
   - Clinical intake and referral endpoints are restricted to verified hospital medical personnel.

---

## 2. Pre-Deployment Security Checklist

- [ ] `.env` and `.env.production` are strictly excluded from git tracking via `.gitignore`.
- [ ] No real database passwords, SMTP credentials, or JWT secrets exist in repository source code.
- [ ] `JWT_SECRET_KEY` in production has at least 32 cryptographically random characters.
- [ ] `ENVIRONMENT=production` is set in production runtime environments.
- [ ] CORS origins in production are restricted to explicit FQDN domains (no wildcard `*`).
- [ ] All uploaded document filenames are sanitized to prevent directory traversal attacks.
