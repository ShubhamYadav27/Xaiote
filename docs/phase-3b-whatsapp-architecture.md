# Phase 3B: WhatsApp Webhook Architecture

## 1. Provider Decision
For the Phase 3B MVP, **Meta WhatsApp Cloud API** is selected as the standard provider.
- **Payload Differences**: Meta provides nested JSON with changes arrays containing `messages` or `statuses`.
- **Signatures**: Verified via `X-Hub-Signature-256` HMAC-SHA256 hash using the App Secret.
- **Media Retrieval**: Meta requires an authenticated GET request to their media API using the payload's Media ID and a System User Access Token.
- **Retry Semantics**: Meta retries webhooks for up to 7 days with exponential backoff if a non-200 response occurs.

## 2. Integration Model
A domain model `WhatsAppIntegration` binds provider identity to a tenant.
**Model**: `WhatsAppIntegration`
- `id`: UUID
- `company_id`: UUID (Foreign Key)
- `external_business_account_id`: String (Meta WABA ID)
- `phone_number_id`: String (Meta Phone Number ID)
- `status`: String (ACTIVE, INACTIVE)
- `app_secret_encrypted`: String (Authenticated encrypted secret)
- `access_token_encrypted`: String (Authenticated encrypted token)
- Timestamps

## 3. Webhook Security & Raw-Body HMAC Verification
1. **Raw-Body HMAC Verification**: Signature verification MUST operate on the exact raw HTTP request body bytes. The sequence is strictly: `Raw HTTP body bytes -> HMAC-SHA256(app_secret, raw_body) -> constant-time signature comparison -> JSON parsing`. JSON must never be parsed/reserialized prior to signature verification.
2. **Missing/Invalid Signature**: Rejected immediately with HTTP 401.
3. **Replay Protection**: Timestamps inside payloads allow staleness checks, but strict idempotency naturally neutralizes replays.
4. **Payload Trust**: The payload `company_id` (if injected) is explicitly ignored. Routing relies entirely on the webhook's `phone_number_id`.

## 4. Tenant Binding
Tenant isolation is securely resolved:
1. Webhook payload contains `metadata.phone_number_id`.
2. DB Query: `SELECT company_id FROM whatsapp_integrations WHERE phone_number_id = ? AND status = 'ACTIVE'`.
3. If no match (Unknown Integration), return 404 (do not leak existence).
4. The resolved `company_id` strictly boundaries the Phase 3A ingestion layer.

## 5. Sender Authorization
**Model**: `AuthorizedSender`
- `id`: UUID, `company_id`: UUID, `phone_number`: String (E.164 normalized), `status`: String (AUTHORIZED, REVOKED).

**Semantics**: Only authorized senders can ingest evidence. 
- **UNKNOWN / REVOKED SENDER**: A 200 OK is returned to Meta (safely terminating the provider retry loop), but the payload is explicitly dropped. No `CommunicationMessage` or `CommunicationAttachment` is created. No user is automatically created. Minimal audit telemetry is logged (`UNAUTHORIZED_SENDER`).

## 6. Durable Webhook Evidence Envelope
Webhook HTTP 200 acknowledgments are decoupled from third-party media downloads. 
The webhook durably persists the **envelope** immediately:
- `external_message_id`, `company_id`, `sender_identity`, `raw_payload`, `received_timestamp`, and provider media references.
Once this envelope is committed to PostgreSQL, the webhook immediately returns `200 OK`. 

## 7. Media Retrieval Model & Security
Media retrieval happens asynchronously *after* the durable envelope is committed.
1. **Security**: Webhook media ID dictates the lookup. The application constructs an authenticated Meta API call using the Media ID. It **never** fetches arbitrary URLs provided by the client payload (preventing SSRF).
2. **Media Limits**: Streaming retrieval enforces a strict technical maximum of 50MB (Meta audio limit is 16MB). Unsupported media types or files exceeding size limits are aborted mid-stream.
3. **Processing**: Stream -> Validate Size/Type -> MinIO -> Phase 3A `CommunicationAttachment`.

## 8. Failure State Model (Message vs Attachment)
**Communication Message State**:
- `RECEIVED`: Durable text envelope persisted.
- `EVIDENCE_PERSISTED`: Durable media envelope persisted, awaiting background media retrieval.

**Media Attachment State**:
- `MEDIA_PENDING`: Background worker queued.
- `MEDIA_PROCESSING`: Currently downloading/streaming.
- `MEDIA_PERSISTED`: MinIO persistence and linking complete.
- `MEDIA_FAILED`: Provider error, timeout, or size violation. Retryable through durable state.

## 9. Secret Encryption Boundary
For the Phase 3B MVP, application-level authenticated encryption (e.g., Fernet) secures credentials in the database.
- Key material is environment-injected (`SECRET_ENCRYPTION_KEY`).
- Clear separation: Database encryption at rest vs Application credential management.
- AES encryption alone does not provide a complete Secret Manager solution (KMS integration is deferred to production hardening).
- No plaintext credentials, no raw credential logging, and no source-controlled secrets.

## 10. Idempotency & Retry Model
- **Provider Retry**: Reuses Phase 3A's canonical `(company_id, source_channel, external_message_id)`. Concurrent duplicates hit a DB `IntegrityError`, falling back to returning 200 OK.
- **Media Retry**: If media retrieval fails, background state polling handles the retry. It explicitly queries existing attachments to prevent duplicate media generation for the same `external_message_id`.

## 11. Explicit Scope Exclusions
Phase 3B implements **verified source ingestion and media retrieval only**.
Absolutely NO: STT, Whisper, LLM, OpenAI SDK, extraction, entity resolution, fuzzy matching, embeddings, ManufacturingEvent, root cause, risk scoring, ML, recommendations, alerts, IoT, predictive maintenance, Redis, or Celery.
