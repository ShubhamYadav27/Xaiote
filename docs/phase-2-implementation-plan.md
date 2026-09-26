# XAIOTE — PHASE 2 IMPLEMENTATION PLAN

*This plan breaks down the Data Foundation into strictly sequential sub-phases. No Phase 2 code will be written until this plan is explicitly authorized by the CTO.*

---

## Sub-phase 1: Master Data Models & Persistence
**Objective:** Define the canonical database tables for Customers, Vendors, Machines, and Products using the frozen minimal schema.
* **Files Affected:** `app/models/masters.py`
* **Database Changes:** Create tables `customers`, `vendors`, `machines`, `products`. Apply `(company_id, external_id)` unique constraints for canonical identity.
* **Tests:** Unit tests verifying SQLAlchemy model creation, nullable boundaries, and unique constraints.
* **Acceptance Criteria:** Alembic migration generated successfully and applies cleanly. Tenant foreign keys verified.

## Sub-phase 2: Work Order Model & Persistence
**Objective:** Define the production anchor, strictly limited to Xaiote's required intelligence fields.
* **Files Affected:** `app/models/work_order.py`
* **Database Changes:** Create table `work_orders` with FKs to `plants`, `products`, `customers`, and `machines`. Include `order_number`, `quantity`, `due_date`, `status`, `planned_production_info`, `production_progress`, `external_id`, and `source_import_job_id`. Unique constraint on `(company_id, plant_id, order_number)`.
* **Tests:** SQLAlchemy relationship and referential integrity tests.
* **Acceptance Criteria:** Alembic migration succeeds. Schema matches the frozen architecture document.

## Sub-phase 3: Import State Machine & Audit Models
**Objective:** Establish the PostgreSQL-backed source of truth for the import lifecycle and row-level traceability.
* **Files Affected:** `app/models/imports.py`
* **Database Changes:** 
  * Create `import_jobs` table (`status` enum: RECEIVED, VALIDATING, PROCESSING, COMPLETED, COMPLETED_WITH_ERRORS, FAILED), `source_filename`, `file_hash`, tracking metrics.
  * Create `import_audits` table (`target_entity_id`, `status`, `error_reason`, `raw_payload_hash`, raw JSON payload for invalid/review records).
* **Tests:** State transition and constraint tests.
* **Acceptance Criteria:** Alembic migration succeeds.

## Sub-phase 4: Master Data & Work Order APIs
**Objective:** REST endpoints with strict pagination, filtering, and tenant isolation.
* **Files Affected:** `app/api/routes/masters.py`, `app/api/routes/work_orders.py`, `app/schemas/...`
* **APIs:** Paginated `GET /POST` for `customers`, `machines`, `vendors`, `products`, `work-orders`.
* **Tests:** API integration tests enforcing `current_company` isolation. (Company A cannot query Company B).
* **Acceptance Criteria:** Standard API envelope used (`{"data": ...}`). Swagger UI reflects pagination schemas.

## Sub-phase 5: Deterministic Ingestion Pipeline (Core)
**Objective:** Build the CSV streaming and processing logic bounded by the 25MB/50k row MVP envelope.
* **Files Affected:** `app/services/import_service.py`
* **Logic:** 
  * Stream lines from MinIO. Prevent identical `file_hash` processing.
  * Pydantic schema validation. Map missing foreign keys -> `INVALID` rows.
  * Execute Idempotent Postgres `UPSERT` batching logic based on Canonical Identities.
  * Progress `ImportJob` state machine explicitly (`VALIDATING` -> `PROCESSING` -> `COMPLETED`).
  * Row-level error logging to `import_audits`.
* **Tests:** CSV parsing tests with mock valid/invalid/duplicate datasets. Unknown reference failure tests.
* **Acceptance Criteria:** Deterministic processing: same file is skipped, same data is no-op'd, changed data updates canonical records without duplication.

## Sub-phase 6: Import APIs
**Objective:** Expose the ingestion pipeline over HTTP.
* **Files Affected:** `app/api/routes/imports.py`
* **APIs:** 
  * `POST /api/v1/imports/upload` (Returns `import_job_id` initialized to `RECEIVED`).
  * `GET /api/v1/imports/{job_id}` (Poll state machine).
  * `GET /api/v1/imports/{job_id}/audits` (Paginated errors).
* **Tests:** E2E API tests uploading a CSV file and querying the audit log.
* **Acceptance Criteria:** State transitions accurately reflect pipeline progress.

## Sub-phase 7: System E2E & Quality Gates
**Objective:** Final hardening and test completion.
* **Files Affected:** Entire test suite.
* **Tests:** 
  * Fresh DB `base` -> `head` migration test.
  * Full tenant isolation suite.
  * Phase 1 Auth Regression tests.
* **Acceptance Criteria:** `pytest`, `black`, `ruff`, and `mypy` all pass. No regressions on Phase 1 logic.

---

## Rollback Considerations
All database schema changes are managed via Alembic. In the event of a critical failure during a sub-phase migration, `alembic downgrade <previous_revision>` will cleanly remove the Phase 2 tables without affecting the Phase 1 Auth/Tenant foundation.
