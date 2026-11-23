# SMTP Configuration & Email Delivery Guide

**Project:** SWASTHYA SAMANVAY — Hospital Coordination & Referral Platform (`SIH_Hospital_AI`)

---

## 1. Supported Email Backends

The platform supports two email modes configured via `SIH_EMAIL_BACKEND`:

1. **`simulated` (Default for Development):**
   - Logs email messages to stdout / logfiles and database outbox tables without attempting external network connections.
   - Ideal for local testing and CI/CD pipelines.

2. **`smtp` (Production Mode):**
   - Connects to an external SMTP relay (e.g. Brevo, SendGrid, Amazon SES, or custom hospital SMTP) over TLS (Port 587 or 465).

---

## 2. Setting Up Brevo (Sendinblue) SMTP Relay

1. Create a Brevo account at [brevo.com](https://www.brevo.com).
2. Navigate to **SMTP & API** → **SMTP** tab.
3. Generate a new SMTP key.
4. Configure your `.env` or production environment variables:
   ```env
   SIH_EMAIL_BACKEND=smtp
   SIH_OTP_PROVIDER=EMAIL
   SMTP_HOST=smtp-relay.brevo.com
   SMTP_PORT=587
   SMTP_USERNAME=pawanbussiness108@gmail.com
   SMTP_PASSWORD=your_brevo_smtp_key_here
   SMTP_FROM_EMAIL=pawanbussiness108@gmail.com
   SMTP_USE_TLS=true
   SMTP_TIMEOUT=15
   ```

---

## 3. Testing SMTP Connectivity

Execute the built-in healthcheck script to verify live SMTP delivery:

```bash
# Verify SMTP handshake and deliver a test message
python3 scripts/smtp_health_check.py --to test@example.com
```
