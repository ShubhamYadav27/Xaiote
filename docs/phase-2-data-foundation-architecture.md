# XAIOTE — PHASE 2 DATA FOUNDATION ARCHITECTURE

## 1. Product North Star (Frozen)
Xaiote is strictly: **Structured Manufacturing Data + Shop-Floor Communication → Manufacturing Event → Root Cause → Affected Order → Impact → Risk → Management Action**. 
Phase 2 solely exists to build the trustworthy structured-data foundation for this future flow. 
**Explicit Non-Scope:** ERP, MES, accounting, payroll, inventory ERP, MRP, full BOM, IoT, PLC/machine control, predictive maintenance, ML prediction, generic BI, generic AI assistant.

## 2. Minimal Entity Model
The core domain is restricted to answering: *Which company/plant → which order → which customer/product → which machine/vendor → what production state?*
* **Masters**: Customer, Vendor, Product, Machine
* **Production Anchor**: Work Order
* **Traceability**: Import Job, Import Audit

*Note: Billing, accounting, and full physical-address modeling are strictly excluded from Phase 2.*

## 3. Database Schema & Fields
All tables utilize `id` (UUID PK), `company_id` (FK), `created_at` (UTC timezone-aware), and `updated_at`.
* **customers**: `name`, `external_id`
* **vendors**: `name`, `external_id`
* **products**: `name`, `sku`, `external_id`
* **machines**: `plant_id` (FK), `name`, `category`, `external_id`
* **work_orders**: 
  * `plant_id` (FK)
  * `customer_id` (FK, nullable)
  * `product_id` (FK)
  * `machine_id` (FK, nullable)
  * `order_number` (String, required)
  * `quantity` (Numeric)
  * `planned_production_info` (JSONB/String, nullable)
  * `due_date` (DateTime)
  * `status` (String/Enum)
  * `production_progress` (Numeric/JSONB, nullable)
  * `external_id` (String)
  * `source_import_job_id` (FK - Provenance)
* **import_jobs**: `status` (Enum), `source_filename`, `file_hash`, `total_rows`, `valid_rows`, `invalid_rows`
* **import_audits**: `import_job_id` (FK), `source_row_number`, `target_entity_id`, `status`, `error_reason`, `raw_payload_hash`

## 4. Import Identity vs. Canonical Identity
**Canonical Record Identity (Deduplication Logic):**
* Customer/Product/Vendor: `(company_id, external_id)`
* Machine: `(company_id, plant_id, external_id)`
* Work Order: `(company_id, plant_id, order_number)`
*If `external_id` is nullable (e.g. manual entry), uniqueness falls back to exact name/SKU per tenant.*

**Import Identity (Provenance Logic):**
Every imported fact must trace back to its origin via:
* `import_job_id`
* `source_filename` & `source_file_hash`
* `source_row_number` & `import_timestamp`
*This answers: "Which import created or changed this manufacturing fact?"*

## 5. Repeated Import Semantics
* **Same Canonical Identity + Same Values**: Deterministically ignored. Recorded as an idempotent no-op (unchanged).
* **Same Canonical Identity + Changed Values**: Record is updated. `import_audits` logs the mutation, updating the source provenance link.
* **Same File Uploaded Twice**: Rejected/skipped early. The system detects duplicates using `source_file_hash`.
* **Different File, Same Business Records**: Canonical identity (`external_id` / `order_number`) safely updates the existing records without duplicating.

## 6. Import State Machine Architecture
FastAPI `BackgroundTasks` are **excluded** as the canonical architecture due to lack of durability.
**Source of Truth:** PostgreSQL-backed `ImportJob` state machine.
**Lifecycle**: `RECEIVED` → `VALIDATING` → `PROCESSING` → `COMPLETED` (or `COMPLETED_WITH_ERRORS`, `FAILED`).
**Evolution Path**: Phase 2 will execute these states synchronously or via a lightweight persisted loop for MVP simplicity, designed specifically so a Redis/Celery worker can seamlessly consume the `PROCESSING` state in future iterations.

## 7. Data Quality & Reference Handling
* **VALID**: Cleanly mapped, persisted as a trusted production fact.
* **INVALID**: Missing required data, malformed constraints, or **Unknown References**. If an import references an unknown Product/Machine, it is deterministically rejected as INVALID. The system will *not* silently create stub master records.
* **NEEDS_REVIEW**: Flagged for human review (persisted to audit, but not main production tables).

## 8. Raw Source Traceability
To ensure provenance without logging sensitive PII raw data unnecessarily:
* Retained Metadata: `import_job_id`, `file_hash`, `row_number`, `filename`, `timestamp`, `validation_status`, `target_entity_id`, `error_reason`.
* Raw Payload Retention: Raw JSON payloads are retained *only* for INVALID/NEEDS_REVIEW rows inside `import_audits` to allow debugging/retry. VALID rows do not duplicate raw data storage, relying on the canonical tables.

## 9. API Contract
Standard envelope (`{"data": {...}}` / `{"error": {...}}`). 
List endpoints (`GET`) strictly include Pagination (limit/offset), Filtering, and Sorting.
* `GET/POST /api/v1/customers`
* `GET/POST /api/v1/vendors`
* `GET/POST /api/v1/products`
* `GET/POST /api/v1/machines`
* `GET/POST /api/v1/work-orders`
* `POST /api/v1/imports/upload`
* `GET /api/v1/imports/{job_id}` & `.../audits`

## 10. Multi-Tenancy & Authorization
Phase 1 isolation applies universally. Client-provided `company_id` is never trusted. All repositories derive `company_id` directly from the authenticated JWT `current_company`. Explicit cross-tenant access tests are mandatory for all endpoints.

## 11. Performance Envelope (Phase 2 MVP)
* **Max CSV Size**: 25MB limit.
* **Max Row Count**: 50,000 rows per file.
* **Parsing Strategy**: Chunked/Streaming parsing (e.g. 1000 rows per block).
* **Insert Strategy**: Postgres `UPSERT` (`INSERT ... ON CONFLICT DO UPDATE`) executed in batches.
* **Timeout Behavior**: Processing bounded by reasonable HTTP timeouts (if synchronous) or DB lock timeouts.

## 12. Test Plan
* **CRUD**: Full lifecycle for Masters & Work Orders.
* **Validation**: Rejecting missing columns, invalid data types, malformed CSVs.
* **Tenant Isolation**: Cross-tenant injection blocking for all entities.
* **Idempotency & Repeats**: Same file re-upload (rejected), duplicate rows (merged), changed records (updated).
* **Unknown References**: Asserts that rows referencing fake SKUs/Machines cleanly fail into `INVALID` states.
* **State Transitions**: Tests `ImportJob` lifecycle progression.
* **Migrations**: Fresh DB `base` -> `head` tests.
* **Phase 1 Regressions**: Ensure auth/JWT functionality remains unbroken.

## 13. CTO DECISIONS FROZEN
* **North Star Adherence**: Xaiote remains an intelligence layer, NOT an ERP.
* **Minimal Entities**: Only Customer, Vendor, Product, Machine, WorkOrder, ImportJob, ImportAudit.
* **No PII/Accounting**: Billing, HR, Accounting schemas are forbidden.
* **Import State Truth**: PostgreSQL is the single source of truth for import state (no Celery/Redis yet).
* **No Silent Fakes**: Unknown foreign key references result in `INVALID` rows, never silently generated masters.
* **Idempotency Focus**: Updates must be deterministic, preventing record duplication based on `external_id` and `order_number`.
* **API Envelopes**: Strict `{"data": ...}` and `{"error": ...}` responses.
