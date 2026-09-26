# Phase 3C - Speech-to-Text Foundation Architecture

## 1. Purpose & Scope
The Phase 3C architecture establishes a durable, provider-agnostic Speech-to-Text (STT) evidence layer. It transforms raw audio evidence into text transcripts while preserving the immutability of the original audio. 

**Strictly In-Scope**: Audio retrieval, STT abstraction, transcript persistence, crash recovery, Hindi/English evaluation.
**Strictly Out-of-Scope**: Semantic extraction, Work Order resolution, LLM predictions, Redis/Celery.

## 2. Audio Evidence & Immutability
The original `CommunicationAttachment` binary residing in MinIO remains completely immutable. 
The system will never overwrite the source audio. Instead, a new `CommunicationTranscript` entity will be created, holding a strict 1:1 foreign-key reference to the source attachment.

## 3. Data Model
```sql
TABLE communication_transcripts (
    id UUID PRIMARY KEY,
    company_id UUID NOT NULL REFERENCES companies(id),
    attachment_id UUID NOT NULL UNIQUE REFERENCES communication_attachments(id),
    
    -- Provenance
    provider VARCHAR NOT NULL,
    model VARCHAR NOT NULL,
    language VARCHAR,
    
    -- Transcripts (Human in the loop support)
    provider_transcript TEXT,
    corrected_transcript TEXT,
    correction_metadata JSONB,
    
    -- Telemetry
    confidence FLOAT,
    duration_seconds FLOAT,
    provider_request_id VARCHAR,
    
    -- Durable State Machine
    status VARCHAR NOT NULL DEFAULT 'PENDING', -- PENDING, PROCESSING, COMPLETED, NO_SPEECH, FAILED
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    lease_until TIMESTAMP WITH TIME ZONE,
    worker_id VARCHAR,
    
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
```
**Idempotency Guarantee**: The `UNIQUE(attachment_id)` constraint guarantees exactly one canonical transcript record per audio attachment, preventing duplicate database entries. Retries and telemetry are natively tracked on this single canonical record without needing a separate attempt table.

## 4. Processing Architecture (Durable PostgreSQL Queue)
Following the success of Phase 3B, Phase 3C will reuse the PostgreSQL-backed durable worker pattern.
FastAPI `BackgroundTasks`, Redis, and Celery are explicitly excluded.

**Worker Boundaries**:
* `media_worker.py`: Exclusively handles provider media retrieval and MinIO persistence. Upon successful persistence, it inserts a `CommunicationTranscript(status='PENDING')` in the same database transaction. It MUST NOT invoke STT.
* `stt_worker.py`: Exclusively handles audio validation, STT invocation, and transcript finalization.

**STT Worker Lifecycle**:
1. **Claim**: `SELECT ... WHERE status = 'PENDING' OR (status = 'PROCESSING' AND lease_until < NOW()) FOR UPDATE SKIP LOCKED`
2. **Lock**: Transition to `PROCESSING`, set `lease_until` and `worker_id`, then immediately `COMMIT`.
3. **Retrieve & Validate**: Stream audio headers from MinIO to validate MIME type, container, and duration.
4. **Transcribe**: Pass a bounded `AudioInput` stream abstraction to the STT Provider.
5. **Finalize**: Transition to `COMPLETED`, `NO_SPEECH`, or `FAILED`, verifying `worker_id` ownership.

## 5. Provider Abstraction & Strategy
The domain will rely on a generic, streaming interface to prevent full audio materialization in application memory:
```python
class AudioInput(BaseModel):
    stream: AsyncIterator[bytes]
    content_type: str
    filename: str
    size_bytes: int
    duration_seconds: float

class TranscriptResult(BaseModel):
    transcript: str
    confidence: float | None
    language: str | None
    duration_seconds: float | None
    provider_request_id: str | None

class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_input: AudioInput, metadata: dict) -> TranscriptResult:
        ...
```
**Configuration**: Providers are injected via environment configurations: `STT_PROVIDER`, `STT_MODEL`, `STT_API_KEY`. The domain will not hardcode specific model names (e.g., `whisper-1`).

**MVP Provider**: **OpenAI Whisper (API)**
* **Why**: High accuracy for mixed Indian shop-floor communication (Hinglish, Hindi, English), robust multi-lingual fallback.
* **Future Replacement**: The generic abstraction enables swapping to alternative providers (like Sarvam AI) purely by switching the configuration and adapter.

## 6. Audio Policies & Validation
Xaiote's domain policies are strictly separated from provider limitations.

**Xaiote Domain STT Policy**:
* `MAX_AUDIO_BYTES`: 50 MB (Matches Phase 3B attachment limit).
* `MAX_AUDIO_DURATION_SECONDS`: 900 seconds (15 minutes). Rationale: Standard WhatsApp maximum audio duration is roughly 15 minutes. Long-form podcast transcription is out of scope for shop-floor communication.
* `ALLOWED_AUDIO_FORMATS`: `[audio/ogg, audio/mp4, audio/aac, audio/wav, audio/amr, audio/mpeg]`. (Strictly accommodates all WhatsApp voice note codecs).

**Provider Adapter Constraints (e.g., Whisper)**:
* Provider-specific limits (e.g., Whisper enforces a 25MB limit) are handled INSIDE the provider adapter. If `AudioInput.size_bytes` exceeds the provider's limit, the adapter must utilize provider-specific mechanisms (like bounded temp files and chunking) to fulfill the contract, or raise a permanent failure if chunking is unsupported.

**Validation Strategy**:
We will not trust the client-provided MIME type alone. Validation occurs BEFORE provider invocation:
1. Check declared MIME type against `ALLOWED_AUDIO_FORMATS`.
2. Analyze actual media container metadata (using `mutagen` or `ffprobe`).
3. Extract actual `duration_seconds`. If unknown, malformed, or exceeds `900` seconds, reject immediately (permanent failure).

## 7. Failure Model & Recovery
* **Retryable Failures** (HTTP 429, 502, 503, 504, Timeout): Increment `retry_count`. Transition back to `PENDING` (or let lease expire).
* **Permanent Failures** (HTTP 400, 401, 403, 413, Unrecognized Audio, Unsupported Container, Validation Reject): Transition immediately to `FAILED`.
* **Empty Transcripts**: Successful provider processing that yields no speech is a distinct semantic state. Transition to `NO_SPEECH`. (Phase 3D will require this distinction).
* **Crash Recovery**: If the worker pod crashes during STT I/O, `lease_until` expires, and a live worker re-claims the row.

## 8. Security & AI Safety
* **AI Safety Boundary**: Transcripts represent raw communication evidence ONLY.
* **Isolation**: MinIO audio streams and transcripts are strictly scoped to the tenant's `company_id`.
* **Credentials**: STT API keys are never logged or exposed.

## 9. Evaluation Framework
**1. Engineering Test Fixtures**:
Small, deterministic synthetic/mock audio fixtures used in unit/integration tests to verify the pipeline, bounds, and failure states.

**2. STT Quality Evaluation Dataset**:
A separate, versioned, representative dataset used specifically to evaluate provider accuracy, latency, and cost. It covers:
* Languages: English, Hindi, Hinglish/code-switching.
* Vocabulary: Manufacturing terminology, machine names, work-order numbers, vendor names, abbreviations.
* Audio Profiles: Noisy environments, multiple speakers, various accents, short and long utterances.
*(Note: A 5–10 clip smoke dataset will be used initially as a development smoke dataset, serving as a placeholder for the comprehensive production-quality evaluation set).*
