# Incident Management & On-Call Runbooks

## 1. Incident Severity Matrix

| Severity Level | Definition | Target Response (MTTA) | Target Resolution (MTTR) | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **SEV-1 (Critical)** | Complete platform unavailability; API returning 5xx globally; database unreachable. | `< 15 minutes` | `< 1 hour` | ECS task crash loop, database pool exhaustion, DNS outage. |
| **SEV-2 (Major)** | Core ingestion pipeline halted; WhatsApp voice notes not transcribing; dashboard failure. | `< 30 minutes` | `< 4 hours` | STT provider failure, Alembic migration desync, S3 upload failure. |
| **SEV-3 (Moderate)** | Degraded performance; non-blocking worker delays; single plant data desync. | `< 2 hours` | `< 24 hours` | Low confidence disambiguation backlog, minor report query timeout. |
| **SEV-4 (Minor)** | Minor UI cosmetic defect; non-critical telemetry gap. | Next business day | Next release cycle | Typo in email notification, badge styling discrepancy. |

---

## 2. On-Call Runbook 1: Production 500 Outage & Rapid Recovery

### Trigger:
CloudWatch alarm `RollbackAlarm` fires or automated monitoring reports consecutive HTTP 500 responses on `/api/v1/incidents`.

### Procedure:
1. **Acknowledge Pager:** Mark incident acknowledged in on-call scheduler.
2. **Execute Terminal Smoke Test:**
   ```powershell
   python c:\Xaiote\backend\test_regression.py
   ```
3. **Capture Immediate Logs:**
   ```powershell
   aws logs tail /ecs/xaiote-backend --since 15m --region ap-south-1 > error_log.txt
   ```
4. **Determine Failure Domain:**
   - **Case A: Database Schema Error (`UndefinedTableError`)**
     - Cause: Backend deployed ahead of database migrations.
     - Action: Execute `cd c:\Xaiote\backend; alembic upgrade head`.
   - **Case B: Bad Container Build / Fatal Startup Crash**
     - Cause: Unhandled runtime dependency or environment variable missing.
     - Action: Revert ECS task definition to prior stable revision (see [Rollback Runbook](../infrastructure/rollback-and-recovery.md)).
5. **Verify Resolution:** Run `test_regression.py` and confirm all 200 OK statuses.

---

## 3. On-Call Runbook 2: Sarvam STT Provider Outage & Failover

### Trigger:
Sarvam AI REST API reports 502/503/504 errors or returns persistent authentication failures, causing transcripts to transition to `FAILED`.

### Procedure:
1. **Check Sarvam Cloud Status:** Verify if Sarvam AI platform is experiencing widespread service disruption.
2. **Execute Dynamic Provider Failover to OpenAI Whisper:**
   - Open AWS Secrets Manager: `xaiote/production-aAx408`.
   - Update configuration parameters:
     ```json
     {
       "STT_PROVIDER": "openai",
       "STT_MODEL": "whisper-1",
       "STT_API_KEY": "sk-proj-..."
     }
     ```
   - Trigger rolling update on ECS service to pick up new configuration:
     ```powershell
     aws ecs update-service --cluster default --service xaiote-backend --force-new-deployment --region ap-south-1
     ```
3. **Re-queue Failed Transcripts:**
   Reset transcripts that failed during the outage window:
   ```sql
   UPDATE communication_transcripts
   SET status = 'PENDING', retry_count = 0, last_error = NULL
   WHERE status = 'FAILED' AND created_at > NOW() - INTERVAL '2 hours';
   ```
   *The STT worker will automatically claim and process them using the Whisper fallback.*

---

## 4. On-Call Runbook 3: Database Connection Pool Exhaustion

### Trigger:
Logs report `asyncpg.exceptions.TooManyConnectionsError` or `pool_size exceeded`.

### Procedure:
1. **Verify Connection String:**
   Supabase provides two port options:
   - **Port 5432:** Direct connection or transaction pooler (recommended for asyncpg).
   - **Port 6543:** Session pooler.
2. **Inspect Active Connection Count in PostgreSQL:**
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
3. **Kill Idle Leaked Connections:**
   ```sql
   SELECT pg_terminate_backend(pid) 
   FROM pg_stat_activity 
   WHERE state = 'idle' AND state_change < NOW() - INTERVAL '15 minutes';
   ```
4. **Tune Application Connection Limits:**
   In `backend/app/infrastructure/database/session.py`, ensure connection pool sizes are tuned within Supabase tier limits.

---

## 5. On-Call Runbook 4: Poison Pill Queue Clearing

### Trigger:
A corrupt audio file or malformed WhatsApp payload repeatedly crashes a background worker upon being claimed.

### Procedure:
1. Locate the failing record ID from the error stack trace:
   ```powershell
   aws logs tail /ecs/xaiote-backend --since 30m --region ap-south-1 | findstr "Worker Error"
   ```
2. Manually transition the poison record to `NEEDS_REVIEW` in PostgreSQL:
   ```sql
   UPDATE communication_attachments
   SET status = 'MEDIA_FAILED', retry_count = 99, 
       last_error = 'Quarantined by on-call engineer: malformed container header'
   WHERE id = '<FAILING_RECORD_ID>';
   ```
3. Verify that the worker loop automatically resumes processing the remainder of the queue.
