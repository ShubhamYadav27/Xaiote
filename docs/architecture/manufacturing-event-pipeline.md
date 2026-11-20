# Manufacturing Event & Canonicalization Pipeline

## 1. Pipeline Overview

The Xaiote Manufacturing Event Pipeline is an asynchronous, transactional state machine designed to transform unstructured shop-floor communications into deterministic, canonical manufacturing events.

The pipeline spans seven durable processing stages:
1. **Ingress & Handshake:** Meta WhatsApp Webhook receives raw message; verifies HMAC signature; persists envelope.
2. **Evidence Worker:** Parses communication payload; creates media attachment records or direct text transcripts.
3. **Media Worker:** Downloads media from Meta Cloud API; validates bounded byte size; streams to MinIO/S3.
4. **Speech-to-Text Worker:** Validates audio headers via `mutagen`; enforces duration constraints; transcribes via Sarvam AI.
5. **Extraction Worker:** Calls LLM with strict JSON schema; records prompt/schema cryptographic provenance.
6. **Entity Resolution Worker:** Resolves natural language references to physical plant master entities via trigram similarity.
7. **Canonicalization Worker:** Performs cross-entity integrity checks; generates canonical event; evaluates work order impact and incident correlation.

---

## 2. End-to-End Pipeline Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Floor Operator
    participant Meta as Meta WhatsApp Cloud API
    participant Webhook as FastAPI Webhooks (/api/v1/webhooks/whatsapp)
    participant DB as PostgreSQL 15 (Supabase)
    participant Storage as MinIO / S3 Object Storage
    participant MediaW as Media Worker (asyncio)
    participant STTW as STT Worker (asyncio)
    participant Sarvam as Sarvam AI (saaras:v4)
    participant ExtrW as Extraction Worker (asyncio)
    participant LLM as OpenAI (gpt-4o-mini)
    participant ResolvW as Resolution Worker (asyncio)
    participant CanonW as Canonicalization Worker (asyncio)
    participant ImpactSvc as Impact & Incident Service

    Operator->>Meta: Sends voice note ("CNC 2 spindle failed, 8 hrs downtime")
    Meta->>Webhook: POST webhook payload (HMAC-SHA256 signature in header)
    Webhook->>Webhook: Verify HMAC signature using Fernet-decrypted secret
    Webhook->>DB: Check authorized_senders & whatsapp_integrations
    Webhook->>DB: INSERT INTO communication_messages (status='RECEIVED')
    Webhook-->>Meta: HTTP 200 OK (Instant acknowledgment)

    loop Evidence Worker Loop (FOR UPDATE SKIP LOCKED)
        DB->>MediaW: Claim message (status='RECEIVED')
        MediaW->>DB: INSERT INTO communication_attachments (status='MEDIA_PENDING')
        MediaW->>DB: UPDATE communication_messages SET status='EVIDENCE_PERSISTED'
    end

    loop Media Worker Loop
        DB->>MediaW: Claim attachment (status='MEDIA_PENDING')
        MediaW->>Meta: GET media URL & download audio bytes
        MediaW->>Storage: PUT object (bucket: xaiote-evidence, key: media/{id})
        MediaW->>DB: UPDATE attachment status='MEDIA_PERSISTED'
        MediaW->>DB: INSERT INTO communication_transcripts (status='PENDING')
    end

    loop STT Worker Loop
        DB->>STTW: Claim transcript (status='PENDING')
        STTW->>Storage: GET audio stream into bounded temp file
        STTW->>STTW: Validate duration & MIME via mutagen
        alt Duration > 30 seconds
            STTW->>DB: UPDATE transcript status='NEEDS_REVIEW' (UNSUPPORTED_DURATION)
        else Duration <= 30 seconds
            STTW->>Sarvam: POST /speech-to-text (saaras:v4)
            Sarvam-->>STTW: Return transcript text & detected language
            STTW->>DB: UPDATE transcript status='COMPLETED', provider_transcript=text
            STTW->>DB: INSERT INTO extracted_event_candidates (status='PENDING')
        end
    end

    loop Extraction Worker Loop
        DB->>ExtrW: Claim candidate (status='PENDING')
        ExtrW->>LLM: POST chat/completions (Structured JSON Schema)
        LLM-->>ExtrW: Extracted entities (event_type, machine_ref, downtime)
        ExtrW->>DB: UPDATE candidate status='COMPLETED', payload=data, prompt_hash=h
    end

    loop Resolution Worker Loop
        DB->>ResolvW: Claim completed candidate
        ResolvW->>DB: Execute ResolutionEngine (pg_trgm search on machines & work orders)
        ResolvW->>DB: INSERT INTO entity_resolution_results (resolved_machine_id, status='RESOLVED')
        ResolvW->>DB: INSERT INTO canonicalization_jobs (status='PENDING')
    end

    loop Canonicalization Worker Loop
        DB->>CanonW: Claim canonicalization_job (status='PENDING')
        CanonW->>CanonW: Validate plant consistency & entity matrix
        CanonW->>DB: INSERT INTO manufacturing_events (status='CANONICAL')
        CanonW->>ImpactSvc: evaluate_impacts_for_event(event_id)
        ImpactSvc->>DB: INSERT INTO production_order_impacts
        ImpactSvc->>DB: Correlate into active INCIDENT & trigger Risk re-evaluation
        CanonW->>DB: UPDATE canonicalization_jobs status='COMPLETED'
    end
```

---

## 3. Worker State Machines & Transitions

Every worker in the pipeline adheres to an atomic, crash-resilient leasing pattern.

### 1. The PostgreSQL Skip-Locked Pattern
```sql
SELECT id FROM communication_attachments
WHERE (status = 'MEDIA_PENDING' OR (status = 'MEDIA_PROCESSING' AND lease_until < :now))
  AND retry_count < :max_retries
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED;
```
- **Atomicity:** Multiple worker threads or container replicas never process the same item simultaneously.
- **Worker Lease:** Each worker claims an item by setting `worker_id` and a lease timestamp (`lease_until = now() + 60s`).
- **Immediate Claim Commit:** The lease is committed immediately to release the table row lock prior to entering blocking network I/O.
- **Automatic Crash Recovery:** If a container crashes or is terminated mid-flight, another worker automatically re-claims the item once `lease_until < now()`.
- **Poison Pill Mitigation:** Items increment `retry_count` on failure. If `retry_count >= 3`, the item transitions to `*_FAILED` or `NEEDS_REVIEW` and halts retries.

---

## 4. Entity Disambiguation & Matrix Evaluation

Before creating a canonical event, the `CanonicalizationWorker` checks the required entity matrix for the identified event type:

| Event Type | Plant Requirement | Machine Requirement | Work Order Requirement | Behavior if Missing |
| :--- | :--- | :--- | :--- | :--- |
| **`MACHINE_FAILURE`** | **Required** | **Required** | Optional | Revert to `NEEDS_REVIEW` |
| **`PROCESS_DEVIATION`**| **Required** | Optional | **Required** | Revert to `NEEDS_REVIEW` |
| **`TOOL_WEAR`** | **Required** | **Required** | Optional | Revert to `NEEDS_REVIEW` |
| **`MATERIAL_SHORTAGE`**| **Required** | Not Applicable | **Required** | Revert to `NEEDS_REVIEW` |

### Plant Consistency Check
If a Work Order resolves to Plant A, but the spoken Machine resolves to Plant B, the pipeline detects a cross-plant conflict:
- The job transitions to `FAILED`.
- The resolution result is marked `NEEDS_REVIEW` with `last_error = "Plant conflict: WO and Machine belong to different plants"`.
- Prevents cross-contamination of physical plant records.

---

## 5. Downstream Impact & Incident Correlation

Once a `ManufacturingEvent` is inserted with status `CANONICAL`:

### 1. Impact Assessment (`ImpactGenerator`)
- Identifies active work orders running on the impacted machine or planned within the downtime window.
- Generates `ProductionOrderImpact` records with status `POTENTIAL`.
- Quantifies estimated delay minutes and scrap quantities based on standard machine run-rates.

### 2. Incident Correlation (`IncidentService`)
- Checks for an existing active `Incident` on the same machine and plant within a 4-hour temporal window.
- If an active incident exists, links the new event via `incident_events` (status `LINKED`).
- If no active incident exists, creates a new `Incident` with status `ACTIVE`.

### 3. Work Order Risk Re-evaluation (`RiskEvaluator`)
- Compares work order planned end dates against backward-scheduled production delays.
- If projected completion exceeds customer commitment dates, transitions work order risk from `PREDICTED_ON_TIME` -> `AT_RISK` -> `CRITICAL_DELAY`.
- Records atomic risk transition in `work_order_risk_history`.

### 4. Alert Policy Evaluation (`AlertWorker`)
- Enqueues an `AlertEvalJob` to evaluate tenant notification policies.
- Evaluates rules against severity thresholds and plant assignment, generating `AlertInstance` records.
