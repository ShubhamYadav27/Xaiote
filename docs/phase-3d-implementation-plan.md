# Phase 3D — LLM Event Extraction Implementation Plan

Phase 3D creates untrusted `ExtractedEventCandidate` records.
Phase 3D does NOT:
- resolve entities
- create `ManufacturingEvent`
- calculate operational risk
- modify production records
- generate predictions
- generate recommendations

## 3D.1 Candidate domain model
* Add `ExtractedEventCandidate` to `app/models/communication.py`.
* Define foreign keys to `companies` and `communication_transcripts` (`UNIQUE` constraint on `transcript_id`).
* Add tracking fields: `processing_status` (PENDING, PROCESSING, COMPLETED, NEEDS_REVIEW, FAILED) and `validation_status` (NULL, VALID, NEEDS_REVIEW, INVALID).
* Add payload fields: `payload`, `raw_llm_response`, `human_correction_payload`, `corrected_by`, `corrected_at`, `correction_reason`.
* Add reproducibility fields: `provider`, `model`, `prompt_version`, `prompt_hash`, `schema_version`, `schema_hash`.
* Add observability/worker fields: `input_tokens`, `output_tokens`, `latency_ms`, `provider_request_id`, `worker_id`, `lease_until`, `attempt_count`, `last_error`.
* Add indexes on `processing_status` and `lease_until`.

## 3D.2 Alembic migration
* Generate `alembic revision --autogenerate -m "phase_3d_extraction"`.
* Verify the generated script maps the new table correctly and preserves constraints.

## 3D.3 Extraction schema
* Create `app/schemas/extraction.py`.
* Define strict bounds: string length limits, numeric bounds, and explicit Enums.
* Integrate field-level machine-testable provenance structures (`EXPLICIT`, `MODEL_DERIVED`, `UNKNOWN`) to distinguish observed facts from inferences.
* Reject empty strings as alternative representations for unknown; enforce `null` for missing data.

## 3D.4 LLM provider abstraction
* Implement the ONE canonical interface in `app/core/interfaces.py`:
```python
from pydantic import BaseModel

class ExtractionMetadata(BaseModel):
    transcript_id: str
    attempt_count: int
    provider_name_override: str | None = None

async def extract_event(
    transcript_text: str,
    schema: dict,
    prompt_instructions: str,
    metadata: ExtractionMetadata,
) -> ExtractedEventResult:
```
* Define `ExtractionMetadata` strictly. It securely provides required extraction/reproducibility context without permitting override of tenant identity, schema, safety instructions, authorization, or processing state.

## 3D.5 Provider adapter
* Implement `app/infrastructure/llm/openai_provider.py`.
* Map specific API errors strictly into `RETRYABLE`, `PERMANENT`, or `REQUIRES_REVIEW` states based on the contract.
* If provider usage is unavailable, set `input_tokens = NULL` and `output_tokens = NULL`. Zero is permitted only when the provider explicitly reports zero.

## 3D.6 Prompt & Version Registry
* Implement immutable configurations for `PROMPT_VERSION`, `SCHEMA_VERSION`, and calculate `prompt_hash` and `schema_hash` at startup.
* Define strict system prompt ensuring root causes are only extracted if explicitly stated, and that no relative timestamps are converted.

## 3D.7 Deterministic validation
* Implement deterministic schema checks using Pydantic.
* Reject oversized inputs. If transcript length exceeds `MAX_TRANSCRIPT_CHARS`:
  * Do NOT truncate.
  * Do NOT invoke the LLM.
  * Set `processing_status = NEEDS_REVIEW`.
  * Set `last_error = "OVERSIZED_INPUT"`.
  * Do not automatically retry.
  * Future chunking is out of scope.

## 3D.8 Durable extraction worker
* Create `app/workers/extraction_worker.py`.
* Implement the PostgreSQL worker lifecycle: Claim -> Commit -> LLM network call -> Finalize.
* In finalization, verify worker lease ownership to prevent stale workers from overwriting newer attempts.

## 3D.9 Idempotency & Database Integrity
* Support the **At-least-once LLM invocation + exactly-one persisted candidate record** model.
* Enforce `UNIQUE(transcript_id)`.

## 3D.10 Retry/recovery
* Establish `MAX_ATTEMPTS = 3`. 
* `attempt_count` tracks the number of external LLM invocations started.
* Increment on `RETRYABLE`. Terminal failure triggers immediately on `PERMANENT` errors. `REQUIRES_REVIEW` goes directly to `NEEDS_REVIEW`. No automatic retry for the latter two.

## 3D.11 Observability & Cost Tracking
* Persist tokens, latency, and request ID natively on the model.
* Strip any logging that prints full transcripts or API keys.

## 3D.12 Security & Tenant Isolation
* Ensure `company_id` is derived securely from the authenticated/canonical transcript context.
* Prevent LLM inputs or metadata from overriding authorization boundaries or schema definitions.

## 3D.13 Evaluation framework
* Implement `tests/eval/test_llm_extraction.py`.
* Implement `root_cause_explicitness_accuracy` metric. It must verify `EXPLICIT`, `MODEL_DERIVED`, and `UNKNOWN`.
* Measure field-level accuracy (`event_type`, `machine_reference`, `temporal-reference`, etc.) separately from Phase 3E metrics.
* Build Hindi, Hinglish, out-of-domain, and prompt injection specific test vectors.

## 3D.14 Integration tests
* Build `tests/test_extraction_worker.py`.
* Test claim concurrency, lease expiration, and stale worker finalization.
* Assert failure mappings and transition states (e.g., verifying `REQUIRES_REVIEW` is not treated as a transient retry).

## 3D.15 Acceptance verification
* Run the entire suite of quality gates (`pytest`, `black`, `ruff`, `mypy`, `alembic`).
* Confirm zero regression in Phase 3A-3C.

---
**PHASE 3D — ARCHITECTURE CORRECTED, AWAITING CTO FINAL REVIEW**
