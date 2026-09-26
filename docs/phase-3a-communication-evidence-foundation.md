# Phase 3A: Communication Evidence Foundation

## 1. Objective
Establish a durable, tenant-safe, auditable foundation for raw shop-floor communication and media (Phase 3A ONLY). This boundary ensures that evidence is safely preserved before any future AI processing occurs.

## 2. Storage & Consistency Semantics
PostgreSQL and Object Storage (MinIO) do *not* form a single distributed ACID transaction. Instead, the system relies on **compensating consistency / rollback semantics**.

**Failure Cases & Compensating Actions:**
- **DB record + object upload succeeds**: Both remain committed.
- **DB transaction fails before commit + object upload already occurred**: The application catches the database `IntegrityError` (or similar DB failure) and executes an explicit, compensating `delete_object` call to MinIO to remove the orphaned object.
- **Object upload fails + DB transaction has not committed**: The MinIO exception bubbles up, generating an HTTP 500. The Postgres transaction rolls back cleanly, leaving no canonical attachment record.
- **Duplicate message/attachment request**: The DB enforces an `IntegrityError` on the `external_message_id`. The application catches this safely, halts the upload, and returns a safe response (no duplicate processing).
- **Application failure between storage and DB operations**: If the node crashes precisely between MinIO success and Postgres commit, an orphan object remains in MinIO. These are benign and will be cleaned up by a future reconciliation job or MinIO lifecycle rule, guaranteeing zero silent evidence loss within the active application data model.

## 3. Idempotency Foundation
The `communication_messages` table enforces:
`UniqueConstraint("company_id", "source_channel", "external_message_id")`
This database-level constraint is the final authority. Simultaneous race conditions resulting in concurrent identical deliveries will hit this constraint, raising an `IntegrityError` which the API layer catches and safely deduplicates without causing a 500 error or redundant processing.

## 4. Tenant Security & Object Isolation
- **Tenant Derivation**: The `company_id` is exclusively derived from the authenticated JWT token (`current_user.company_id`). The client cannot specify a target company ID.
- **Cross-Tenant Access**: GET requests strictly filter by `company_id = current_user.company_id`.
- **Object Storage Keys**: MinIO keys are generated natively by the server. The client's `filename` is completely disregarded for key generation. The server assigns a UUID, yielding: `{company_id}/evidence/{message_id}/{attachment_id}{safe_extension}`.
- **Attachment Validation**: Attachments are strictly bounded to 50MB and validated against unsafe extensions (`.exe`, `.sh`, `.bat`, etc.) before any storage interaction. Path traversal characters in the client-provided filename are completely neutralized by the server-assigned UUID object key.

## 5. Scope Lock Confirmed
Phase 3A implements **evidence persistence only**.
It explicitly does NOT contain: WhatsApp Webhooks, STT, LLM, Pydantic Schema Extraction, Entity Resolution, ManufacturingEvents, Risk Scores, Redis, Celery, or Frontend modifications.
