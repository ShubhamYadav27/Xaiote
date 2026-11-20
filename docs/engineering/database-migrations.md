# Database Migration & Release Gate Procedures

## 1. Migration Framework Overview

Xaiote uses **Alembic 1.13.1** alongside asynchronous SQLAlchemy 2.0 to manage relational database schema versioning.

### Architecture Invariants:
1. **Source of Truth in Code:** Every schema alteration (tables, columns, indexes, foreign keys, constraints) must exist as a versioned migration script in `backend/alembic/versions/`.
2. **Linear History:** Alembic migrations must maintain a strict single-parent chain. Branching heads (`alembic merge`) are prohibited in production branches.
3. **Expand-Contract Schema Evolution:** High-availability deployments require non-breaking, backward-compatible schema changes:
   - **Expand:** Add new nullable columns or tables first; deploy updated code that writes to both old and new columns.
   - **Migrate:** Backfill data asynchronously.
   - **Contract:** Once all running containers are updated, drop deprecated columns in a subsequent release.

---

## 2. Complete Migration Chain (cacd70128399 -> f33a7c860f9c)

| Revision ID | Description / Feature Phase | Down Revision |
| :--- | :--- | :--- |
| `cacd70128399` | Initial core schema (Companies, Users) | `<base>` |
| `b290e8f19063` | Hash tokens table for secure refresh token handling | `cacd70128399` |
| `1821aae8b740` | Production schema initial definitions | `b290e8f19063` |
| `d83c6a2cad35` | Timezone-aware timestamp standardization | `1821aae8b740` |
| `c1b6f92d253b` | Phase 2A: Master data tables (Plants, Machines, Products, Vendors, Customers)| `d83c6a2cad35` |
| `f465d9d61ab3` | Phase 2B: Work orders and scheduling schema | `c1b6f92d253b` |
| `9eeb47bc61e7` | Phase 2C: Bulk CSV/Excel data import staging & audit | `f465d9d61ab3` |
| `110c40d6285f` | Phase 2D: Data quality & audit provenance fields | `9eeb47bc61e7` |
| `6e50084c4532` | Add communication models (messages, attachments) | `110c40d6285f` |
| `a1b2c3d4e5f6` | Phase 3B: WhatsApp webhook integration & authorized senders | `6e50084c4532` |
| `523c665bdcc9` | Phase 3B: Media worker leasing and worker_id locking | `a1b2c3d4e5f6` |
| `290a69f10cf6` | Phase 3C: Speech-to-Text transcripts & status machine | `523c665bdcc9` |
| `ca97df98ce66` | Phase 3D: LLM extraction candidates & prompt hashing | `290a69f10cf6` |
| `880c7f5ee9ee` | Phase 3E: Entity resolution results and confidence scores | `ca97df98ce66` |
| `ada97dcb9ea8` | Phase 3F: Canonical manufacturing events & temporal provenance | `880c7f5ee9ee` |
| `f655f17bd5b6` | Phase 3F: Event revisions and explicit human overrides | `ada97dcb9ea8` |
| `cdd596f33002` | Phase 4A: Production order impact models | `f655f17bd5b6` |
| `65d4578441d5` | Phase 4B: Work order risk history & transitions | `cdd596f33002` |
| `a7c8d9e0f1g2` | Phase 4C: Incident correlation & linking models | `65d4578441d5` |
| `a8c9d0e1f2g3` | Phase 4D: Root cause intelligence & assessments | `a7c8d9e0f1g2` |
| `0450dd418bde` | Phase 4D: Remediation suggestions | `a8c9d0e1f2g3` |
| `796b3dbb013e` | Phase 4E-2: Alert policies, rules, and instances | `0450dd418bde` |
| `16cea21c9002` | Phase 4E-3: Alert evaluation jobs queue | `796b3dbb013e` |
| `2a3b4c5d6e7f` | Phase 5A: Action instances and lifecycle policies | `16cea21c9002` |
| `3b4c5d6e7f8a` | Phase 5B: Prescriptive recommendation models | `2a3b4c5d6e7f` |
| `4c5d6e7f8a9b` | Identity & Plant authorization tables (`user_plants`) | `3b4c5d6e7f8a` |
| `5d6e7f8a9b0c` | Phase 5D: Execution gateway attempts | `4c5d6e7f8a9b` |
| `6e7f8a9b0c1d` | Phase 5E: External integrations registry | `5d6e7f8a9b0c` |
| `7f8a9b0c1d2e` | PostgreSQL `pg_trgm` extension & GiST similarity indexes | `6e7f8a9b0c1d` |
| `f33a7c860f9c` | Add alert evaluation job retry & audit records (HEAD) | `7f8a9b0c1d2e` |

---

## 3. The Production Migration Gate (Mandatory Release Sequence)

> [!CRITICAL]
> **Why Automatic Startup Migrations Are Prohibited:**
> Running `alembic upgrade head` inside container entrypoint scripts (e.g. `CMD ["sh", "-c", "alembic upgrade head && uvicorn ..."]`) is an anti-pattern in containerized production environments.
> When AWS ECS deploys a new task definition, it spawns multiple container replicas simultaneously. If 2-4 containers execute DDL migrations concurrently, PostgreSQL acquires table-level exclusive locks (`AccessExclusiveLock`), resulting in deadlock exceptions, corrupted `alembic_version` state, and startup crashes.

### Standard 10-Step Release Sequence

```mermaid
flowchart TD
    Step1["1. Build Docker image & tag with Git SHA"]
    Step2["2. Push image to Amazon ECR (xaiote-backend:sha)"]
    Step3["3. Run ONE isolated Alembic task (ECS RunTask)"]
    Step4{"4. Migration Task Successful?"}
    Step5["5. Update ECS Service (Canary Deployment)"]
    Step6["6. ECS launches new tasks; drains old tasks"]
    Step7{"7. Target Group Health Checks Passing?"}
    Step8["8. Run Production API Smoke Tests"]
    Step9["9. Promote Frontend Release on AWS Amplify"]
    Step10["10. Release Complete & Verified"]
    
    FailRollback["Abort Release & Rollback ECS Deployment"]

    Step1 --> Step2 --> Step3 --> Step4
    Step4 -->|Yes (DB at HEAD)| Step5 --> Step6 --> Step7
    Step4 -->|No (Error / Timeout)| FailRollback
    Step7 -->|Passing (HTTP 200)| Step8 --> Step9 --> Step10
    Step7 -->|Failing| FailRollback
```

---

## 4. Operational Migration Commands

Always execute Alembic from the `backend` directory where `alembic.ini` resides:

### 1. Check Current Migration Status
```powershell
cd c:\Xaiote\backend
alembic current
```
Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
f33a7c860f9c (head)
```

### 2. View Pending Migrations
```powershell
alembic heads
alembic history --verbose
```

### 3. Generate New Migration (Auto-generate)
When modifying SQLAlchemy declarative models in `app/models/`:
```powershell
alembic revision --autogenerate -m "add_custom_feature_table"
```
*Always inspect the generated file in `alembic/versions/` to verify DDL accuracy before applying.*

### 4. Execute Upgrade to HEAD
```powershell
alembic upgrade head
```

### 5. Rollback Single Revision
```powershell
alembic downgrade -1
```

---

## 5. Troubleshooting Migration Desynchronization

### Incident: Table Does Not Exist (UndefinedTableError)
- **Symptom:** API returns `500 Internal Server Error`; logs report `relation "<table_name>" does not exist`.
- **Root Cause:** Application code was deployed containing queries for new models, but the corresponding Alembic migrations were never applied to the production database cluster.
- **Resolution:**
  1. Inspect `alembic current` vs `alembic heads`.
  2. If the production database is behind HEAD, execute `alembic upgrade head`.
  3. Verify table existence and test the failing endpoint.
