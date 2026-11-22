# Background Workers & Daemon Operations

**Project:** ArogyaSetu Grid — Unified Critical Care & Hospital Command Network (`SIH_Hospital_AI`)

---

## 1. Overview of Background Daemons

ArogyaSetu Grid operates two specialized background daemon processes to maintain system consistency and reliable message delivery:

1. **Transactional Outbox Worker (`src/workers/outbox_worker.py`)**:
   - Dispatches queued email notifications (referral updates, verification notices, activation links).
   - Polls the `email_outbox` table using leasing locks (`locked_at`, `lease_seconds=300`) to guarantee exactly-once/at-least-once delivery semantics across distributed instances.
   - Implements exponential backoff retries (up to 5 attempts).

2. **Reservation Expiry Worker (`src/workers/reservation_expiry_worker.py`)**:
   - Audits active bed reservations whose fulfillment window has lapsed.
   - Automatically returns reserved beds to the active inventory pool and updates the referral record state to `EXPIRED`.

---

## 2. Running Workers

### Running via Virtual Environment
```bash
# Start Outbox Worker
python3 -m src.workers.outbox_worker

# Start Reservation Expiry Worker
python3 -m src.workers.reservation_expiry_worker
```

### Running via Docker Compose
Both workers run as dedicated containerized services in `docker-compose.prod.yml`:
```yaml
outbox_worker:
  build:
    context: .
    dockerfile: Dockerfile.backend
  command: python3 -m src.workers.outbox_worker
  depends_on:
    - postgres

reservation_expiry_worker:
  build:
    context: .
    dockerfile: Dockerfile.backend
  command: python3 -m src.workers.reservation_expiry_worker
  depends_on:
    - postgres
```
