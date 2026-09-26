# Phase 3 Implementation Plan
**Shop-Floor Communication & Event Intelligence**

## Phase 3A: Communication Evidence Foundation
- **Objective**: Establish the durable evidence tables and storage mechanisms for raw communication payloads and media.
- **Scope**: Database schema for `CommunicationMessage`, `CommunicationAttachment`. MinIO object storage mapping.
- **Dependencies**: None.
- **Exclusions**: Webhook routing, LLMs.
- **Acceptance Criteria**: Alembic migrations pass. Unit tests verify DB constraints and MinIO storage abstraction integration.

## Phase 3B: WhatsApp Integration & Tenant Binding
- **Objective**: Implement the secure webhook receiver for WhatsApp Business API.
- **Scope**: `POST /api/v1/webhooks/whatsapp`. Signature verification (`X-Hub-Signature`). Tenant routing mapping WhatsApp number -> `CompanyIntegration` -> `company_id`. Webhook idempotency.
- **Dependencies**: Phase 3A.
- **Security**: Must reject unsigned payloads and unmapped sender numbers.
- **Exclusions**: Async queue processing, STT.
- **Acceptance Criteria**: Duplicate payloads return 200 without duplicate DB inserts. Unmapped senders return a safe error/ignore state.

## Phase 3C: Speech-to-Text (STT) Processing
- **Objective**: Implement the async transcription layer.
- **Scope**: `MessageTranscript` schema. Background worker (PostgreSQL-polled or asyncio background task) fetching `RECEIVED` audio messages. Integration with STT provider (e.g., Whisper).
- **Dependencies**: Phase 3B.
- **Exclusions**: Event extraction.
- **Acceptance Criteria**: Audio files successfully convert to text. AI Observability logs capture latency, provider, and model without leaking API keys.

## Phase 3D: LLM Event Extraction
- **Objective**: Extract structured JSON candidate events from transcripts or text messages.
- **Scope**: `ExtractedEventCandidate` schema. Strict Pydantic parsing of LLM output. AI Observability logging for prompt/schema versioning and token usage.
- **Dependencies**: Phase 3C.
- **Exclusions**: Entity Resolution. LLMs do not verify database constraints.
- **Acceptance Criteria**: Unstructured text translates to predefined JSON schema. Malformed JSON triggers bounded retries.

## Phase 3E: Deterministic Entity Resolution
- **Objective**: Map extracted text (e.g., "CNC 2") to canonical Phase 2 database entities (e.g., UUID of Machine).
- **Scope**: `EntityResolutionAudit` schema. Python-based deterministic matching rules (Exact, Normalized, Bounded Fuzzy). Ranking thresholds (RESOLVED, AMBIGUOUS, UNRESOLVED).
- **Dependencies**: Phase 2 Masters, Phase 3D.
- **Exclusions**: Vector databases, Embeddings.
- **Acceptance Criteria**: Strict exact-matches resolve automatically. Ambiguous matches safely route to `REQUIRES_REVIEW` and halt pipeline progression.

## Phase 3F: Canonical Manufacturing Event
- **Objective**: Promote valid candidates into trusted canonical business events.
- **Scope**: `ManufacturingEvent` schema. Event type vocabulary (e.g., `MACHINE_FAILURE`). Business logic gate ensuring all required entities are `RESOLVED` and provenance (`source_message_id`) is linked.
- **Dependencies**: Phase 3E.
- **Exclusions**: Predictive risk states.
- **Acceptance Criteria**: Fully resolved candidates become `ManufacturingEvents`. Missing/unresolved candidates are successfully queued. Event idempotency prevents duplicate creation.

## Phase 3G: Operational UI & Review Queue
- **Objective**: Surface the communication pipeline and manual review queue to the frontend operators.
- **Scope**: Internal APIs (`GET /api/v1/events/review-queue`, `POST /api/v1/events/review/{id}`). Frontend screens for Communication Timeline and Review Queue.
- **Dependencies**: Phase 3F.
- **Exclusions**: Analytics dashboards, Risk scoring UI.
- **Acceptance Criteria**: UI correctly respects tenant isolation. Operator can manually resolve an `AMBIGUOUS` machine to a valid Phase 2 ID, allowing the backend to successfully promote the candidate to a `ManufacturingEvent`.
