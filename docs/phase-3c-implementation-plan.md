# Phase 3C - Speech-to-Text Implementation Plan

## 1. Sequence

1. **3C.1 Transcript Domain Model**
   * Implement `CommunicationTranscript` SQLAlchemy model.
   * Add `PENDING`, `PROCESSING`, `COMPLETED`, `NO_SPEECH`, `FAILED` state enums.
   * Establish `attachment_id` 1:1 foreign key.
2. **3C.2 Migration**
   * Generate and apply Alembic migration for the `communication_transcripts` table.
3. **3C.3 STT Provider Interface**
   * Create `app/core/interfaces.py` -> `SpeechToTextProvider` ABC.
   * Define `AudioInput` (stream, size, duration) and `TranscriptResult` schema.
4. **3C.4 Provider Adapter**
   * Implement `app/infrastructure/stt/whisper_provider.py`.
   * Configure dynamically via `STT_PROVIDER`, `STT_MODEL`, `STT_API_KEY`.
   * Enforce provider-specific size bounds (25MB chunking or failure) internally.
5. **3C.5 Audio Validation**
   * Implement `validate_audio_for_stt(attachment)` using mutagen/ffprobe.
   * Enforce domain policies: max 50MB, max 900 seconds, explicitly allowed containers.
6. **3C.6 Processing State Machine & 3C.7 Durable Processing Mechanism**
   * Create `app/workers/stt_worker.py`.
   * Implement `SELECT FOR UPDATE SKIP LOCKED` claim logic.
7. **3C.8 Transcript Persistence**
   * Update `media_worker.py` exclusively to trigger `PENDING` transcript creation upon successful audio media persistence (without invoking STT).
8. **3C.9 Idempotency & 3C.10 Retry/Recovery**
   * Handle 4xx vs 5xx STT errors to dictate `retry_count` bumps vs permanent failures.
9. **3C.11 Observability**
   * Add structured logging (duration, latency, `provider_request_id`), redacting secrets.
10. **3C.12 Security**
    * Add `test_tenant_isolation_transcript` ensuring `company_id` binds STT streams safely.
11. **3C.13 Evaluation Datasets**
    * Differentiate deterministic engineering fixtures (unit tests) from the representative STT Quality Evaluation Dataset.
12. **3C.14 Integration Tests**
    * `test_stt_worker.py`: Provider boundaries, validation failures, concurrent swarms.
13. **3C.15 Acceptance Verification**
    * Run the complete A-Z test suite and verification gates for CTO acceptance.

## 2. Test Plan

**Security & Isolation**
* `test_tenant_isolation_transcript`: Cross-tenant reads are blocked.
* `test_credential_secrecy`: STT API keys are injected via env vars and never logged.

**Audio Validation**
* `test_valid_audio`: Audio correctly transitions to `COMPLETED`.
* `test_oversized_audio_domain`: >50MB or >900s immediately marked `FAILED` (permanent).
* `test_oversized_audio_provider`: Adapter correctly rejects or chunks if between adapter bound (25MB) and domain bound (50MB).
* `test_unsupported_codec`: `image/jpeg` ignores STT altogether.
* `test_malformed_container`: Corrupt metadata immediately rejected (`FAILED`).

**Provider Behavior**
* `test_provider_success`: Standard end-to-end processing.
* `test_provider_timeout`: httpx Timeout yields retryable `PENDING`.
* `test_provider_5xx_failure`: HTTP 503 yields retryable `PENDING`.
* `test_provider_4xx_failure`: HTTP 400 yields permanent `FAILED`.
* `test_empty_transcript`: Provider returns empty text -> `NO_SPEECH`.

**Durable State**
* `test_duplicate_stt_processing`: Concurrent workers claim only one instance.
* `test_crash_recovery_stt`: `lease_until` expiration permits re-claim.
* `test_stt_retry_exhaustion`: 3 consecutive retryable failures yield permanent `FAILED`.

## 3. Acceptance Gates
* `pytest -v` (100% pass)
* `black --check .` (0 issues)
* `ruff check .` (0 issues)
* `mypy --config-file mypy.ini .` (0 issues)
* `alembic` (heads clean)
* Docker runtime fully healthy
* Evaluation dataset processed successfully.
