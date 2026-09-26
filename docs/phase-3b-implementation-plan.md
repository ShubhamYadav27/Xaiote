# Phase 3B: WhatsApp Webhook Implementation Plan

## Overview
This execution plan guides the safe integration of the Meta WhatsApp Webhook into the Phase 3A Evidence Foundation. 

## Implementation Sequence
3B.1 **Integration Model**: Create `WhatsAppIntegration` and `AuthorizedSender` models & Alembic migrations.
3B.2 **Credential Security Boundary**: Implement AES-based authenticated encryption logic for in-DB credentials.
3B.3 **Meta Webhook Verification**: Implement the `GET` hub challenge handshake.
3B.4 **Raw-Body HMAC Verification**: Build dependency ensuring HMAC-SHA256 evaluation on raw request bytes *before* JSON parsing.
3B.5 **Tenant Binding**: Logic to map `phone_number_id` to `company_id`.
3B.6 **Sender Authorization**: Logic to validate incoming E.164 numbers.
3B.7 **Durable Webhook Evidence Envelope**: Route logic to persist raw message metadata, decoupling media downloads from the HTTP 200 response.
3B.8 **Text Evidence Persistence**: Map text payloads to `CommunicationMessage` and return 200.
3B.9 **Media Reference Persistence**: Map media metadata to `CommunicationMessage` (status: `EVIDENCE_PERSISTED`).
3B.10 **Async Media Retrieval**: Implement background loop/task to perform authenticated Meta Media API GET requests via strict Media ID lookup.
3B.11 **MinIO Attachment Persistence**: Stream media bounds-checking (50MB) directly to MinIO.
3B.12 **Idempotency / Retry / Recovery**: Ensure media retries do not duplicate attachments; ensure webhook retries safely hit DB constraints.
3B.13 **Observability**: Apply structural logging without sensitive credentials or raw payloads.
3B.14 **Security Testing**: Execute the comprehensive 21-point test matrix.
3B.15 **End-to-End Acceptance**: Run standard project quality gates.

## Comprehensive Test Plan (Acceptance Gates)
Explicitly verify the following scenarios via `pytest`:
A. HMAC computed against exact raw request body
B. Invalid signature -> 401
C. Missing signature -> 401
D. Malformed signature -> 401
E. Valid signature -> Processing proceeds
F. Unknown integration -> 404
G. Unauthorized sender -> 200 OK (Safely dropped)
H. Revoked sender -> 200 OK (Safely dropped)
I. Concurrent duplicate webhook -> 200 OK, 1 canonical row
J. Provider retry -> 200 OK, 1 canonical row
K. Text message ingestion success
L. Voice/Media message ingestion (envelope persistence)
M. Media retrieval timeout -> 500 equivalent in background, retryable state
N. Media provider failure -> retryable state
O. MinIO failure -> rollback attachment DB reference
P. Application restart after durable envelope -> background job recovers media retrieval
Q. Duplicate media retrieval -> idempotent attachment check
R. Malicious/arbitrary media URL attempt -> explicitly blocked/ignored by design
S. Oversized media -> safely aborted during stream
T. Unsupported media type -> gracefully rejected
U. Cross-tenant integration attempt -> bounded explicitly by DB resolution

## Final Quality Gates
Prior to completion, Phase 3B must pass:
1. `pytest -v`
2. `black --check .`
3. `ruff check .`
4. `mypy --config-file mypy.ini .`
5. `alembic current == heads`

## Unresolved Decisions
- Standard execution tooling for asynchronous "background processing state" in Phase 3B.10 (e.g., FastAPI BackgroundTasks vs an explicitly polled Postgres-backed processing queue, deferring to the Phase 2 minimalistic approach preferred by the CTO).
