# Phase 3 Architecture
**Shop-Floor Communication & Event Intelligence**

## 1. Scope & Objectives
**In Scope:** Durable ingestion of shop-floor communication (WhatsApp), Speech-to-Text (STT), LLM-based structured event extraction, deterministic Entity Resolution, and the creation of canonical `ManufacturingEvent` records backed by raw evidence.

**Strictly Out of Scope:** Predictive ML, IoT, root-cause analysis, risk scoring, predictive maintenance, alerts, vector databases/embeddings, and Celery/Redis infrastructure.

---

## 2. WhatsApp Webhook Security & Tenant Binding
The system will never trust payload-supplied tenant IDs. The canonical security pipeline is:
`UNTRUSTED WEBHOOK PAYLOAD` → `SIGNATURE VERIFICATION` → `REGISTERED INTEGRATION IDENTIFICATION` → `TENANT RESOLUTION` → `SENDER AUTHORIZATION` → `PERSISTENCE`

1. **Signature Verification**: Validate `X-Hub-Signature` (or equivalent provider signature) using the registered webhook secret. Reject if invalid.
2. **Integration Identification**: Match the receiving WhatsApp Business Account ID to a registered `CompanyIntegration` record.
3. **Tenant Resolution**: The `CompanyIntegration` resolves the `company_id`.
4. **Sender Authorization**: Query the sender's phone number against the `Users` or `Contacts` table for that `company_id`. Reject if unmapped/unauthorized.
5. **Persistence**: Write the `CommunicationMessage` tied to the resolved `company_id`.

---

## 3. Evidence-First Storage Failure Semantics
The webhook endpoint executes a strict transaction boundary to ensure evidence preservation.
- **Transaction Boundary**: The incoming payload is saved to `CommunicationMessage` with state `RECEIVED`. If there is media, it is uploaded to MinIO first, and the object key is included in the DB transaction. If DB fails, an async cleanup task (or MinIO lifecycle rule) removes orphan objects. If MinIO fails, the DB transaction rolls back. 
- **Idempotency**: The `external_message_id` has a unique constraint per provider. Duplicate webhook deliveries hit a unique constraint violation and safely return `200 OK` (deduplication) without spawning duplicate processing.
- **200 OK Guarantee**: The webhook returns `200 OK` *only* after the PostgreSQL commit succeeds. 
- **Timeouts**: If media processing threatens the webhook timeout window (e.g., 5 seconds), the system will return `200 OK` immediately after persisting the text/metadata, and initiate async media fetching.

---

## 4. Processing Architecture (Phase 2 Boundaries)
**Decision**: Option A (PostgreSQL durable processing state + application worker/process) is selected.
- **Justification**: Introducing Redis/Celery violates Phase 2 minimalism and increases deployment overhead prematurely. Polling a `status` column (e.g., `RECEIVED` -> `PROCESSING`) using `asyncio` background tasks or a lightweight cron worker within the FastAPI container provides sufficient resilience, easy retry semantics, and full transactional observability for initial pilot volumes.
- **Separation**: Ingestion durability (Webhook -> DB) is strictly separated from Processing Execution (DB -> AI -> DB).

---

## 5. Entity Resolution Architecture
Embeddings and vector search are explicitly deferred. Resolution relies on deterministic rules:
1. **Exact Match**: Match canonical `external_id`, `order_number`, or `name`.
2. **Normalized Match**: Strip whitespace, lowercase, remove special characters.
3. **Bounded Fuzzy Matching**: (Optional) Levenshtein distance bounded by high thresholds.
4. **Unresolved**: No safe match exists.

**Entity-Specific Rules:**
- `WorkOrder`: Strictly resolve via exact `order_number` or `external_id`.
- `Machine`: Resolve via exact `name` or `external_id` bound to the `plant_id` of the sender.
- `Product`/`Customer`/`Vendor`: Resolve via exact normalized name or `external_id`.

**Matching Thresholds (Provisional Configuration):**
Exact Match = `RESOLVED`. If a single fuzzy candidate scores > 90%, it maps to `RESOLVED` (subject to pilot calibration). Candidates between 60%-90% or multiple competing 90%+ candidates resolve to `AMBIGUOUS` (triggers `REQUIRES_REVIEW`). 

---

## 6. Manufacturing Event Trust Boundary
The LLM outputs an `ExtractedEventCandidate`. This is **not** a canonical event.
The promotion to `ManufacturingEvent` requires passing the validation pipeline:
`RAW EVIDENCE` → `TRANSCRIPT` → `EXTRACTED CANDIDATE` → `VALIDATION` → `ENTITY RESOLUTION` → `BUSINESS VALIDATION` → `CANONICAL EVENT`

**Requirements for Promotion:**
- Schema validation passes (JSON conforms).
- Minimum required fields are present (Event Type, Description).
- All referenced entities resolve safely to `RESOLVED`.
- If *any* required entity (e.g., Work Order or Machine) resolves to `AMBIGUOUS` or `UNRESOLVED`, the event remains a candidate, is marked `REQUIRES_REVIEW`, and stops.

**Event Idempotency**: `source_message_id` uniquely maps to one `ManufacturingEvent`. A duplicate webhook does not create a new event. Legitimate updates via new messages create new events referencing the new message.

---

## 7. Review Queue Semantics
- **`REQUIRES_REVIEW`**: The pipeline completed but hit an `AMBIGUOUS` or `UNRESOLVED` entity, or a business validation failure.
- **Workflow**: Human opens UI → views raw evidence & transcript → views candidate JSON & suggested entity matches → explicitly selects the correct entity → System re-validates → Canonical Event is created.
- **Traceability**: `EntityResolutionAudit` captures the human's ID as the resolver, ensuring corrections are fully auditable.

---

## 8. Manufacturing Event Schema & Vocabulary
`Severity` represents observed shop-floor severity (e.g., "Line stopped"), not a predicted business impact risk.

**Core Event Types (Controlled Taxonomy):**
1. `MACHINE_FAILURE`: Machine breakdown (Requires `machine_id`).
2. `MATERIAL_SHORTAGE`: Missing raw material.
3. `QUALITY_ISSUE`: Defect detected.
4. `PRODUCTION_DELAY`: Generic operational delay.
5. `SAFETY_INCIDENT`: Safety issue reported.

**`ManufacturingEvent` Schema:**
- `id`, `company_id`, `plant_id` (derived from machine/sender).
- `event_type` (Enum), `description` (String), `severity` (Enum: LOW, MEDIUM, HIGH, CRITICAL).
- `estimated_downtime_minutes` (Integer, nullable).
- `machine_id` (Nullable), `work_order_id` (Nullable).
- `observed_at` (Datetime), `received_at` (Datetime), `created_at` (Datetime).
- `source_message_id` (FK to CommunicationMessage).
- `status` (OPEN, IN_REVIEW, CLOSED).

---

## 9. AI Observability
Every STT/LLM interaction logs an `AIObservabilityLog` containing:
`provider`, `model`, `prompt_version`, `schema_version`, `request_timestamp`, `completion_timestamp`, `latency_ms`, `total_tokens`, `status` (SUCCESS/FAILURE), `error_category`, `confidence_score` (if available).
**Exclusions**: API keys, Auth headers, and PII-laden raw payloads are strictly excluded from observability logging.

---

## 10. API Contracts & Frontend Scope
**API Contracts (Phase 1 Envelope standard):**
- `POST /api/v1/webhooks/whatsapp` (No auth required; uses signature).
- `GET /api/v1/communications` (Filters: status, dates; returns `CommunicationMessage`).
- `GET /api/v1/events/review-queue` (Returns candidates requiring review).
- `POST /api/v1/events/review/{candidate_id}` (Submits human entity overrides).

**Frontend Scope (Operational Intelligence UI):**
- **Communication Timeline**: Read-only timeline of raw messages and STT outputs.
- **Review Queue**: Interface for operators to correct ambiguous entity resolutions.
- **Event Timeline**: Verified canonical Manufacturing Events.
- **Strictly Excluded**: Dashboards predicting risk, downtime probability, or automated root-cause metrics.
