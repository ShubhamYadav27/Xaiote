# Phase 3D — LLM Event Extraction Architecture

## 1. Purpose and Trust Boundary

Phase 3D creates untrusted `ExtractedEventCandidate` records from natural language manufacturing communication (transcripts).

**Phase 3D does NOT:**
- resolve entities (e.g., mapping "CNC 2" to a DB UUID)
- create canonical `ManufacturingEvent` records
- calculate authoritative operational risk
- modify production records
- generate predictions
- generate recommendations

**LLM Tool Authority:**
The LLM acts purely as an interpreter. It has NO database write access, NO entity-resolution authority, NO master-data mutation authority, NO ManufacturingEvent creation authority, NO risk mutation authority, and NO customer communication authority.

## 2. Extraction Schema Hardening & Field-Level Provenance

The LLM will produce a strict, versioned JSON output matching a Pydantic schema. 

**Machine-Testable Provenance Structure:**
To allow automated tests and the application to distinguish observed facts from model inference, extracted fields use an explicit provenance structure combining the extracted value and a provenance tag:
- `EXPLICIT`: Observed/stated value from the transcript.
- `MODEL_DERIVED`: Model-derived interpretation. Must NEVER be treated as observed manufacturing evidence.
- `UNKNOWN`: The information is absent or cannot be established. Value is `null`.

**Schema Fields & Constraints:**
* `event_type` (Enum): `MACHINE_FAILURE`, `DOWNTIME`, `MATERIAL_SHORTAGE`, `QUALITY_ISSUE`, `MAINTENANCE_ISSUE`, `PRODUCTION_DELAY`, `SAFETY_INCIDENT`, `OTHER`
* `event_description` (String, max 500 chars)
* `machine_reference`, `work_order_reference`, `customer_reference`, `product_reference`, `vendor_reference` (Structured Provenance String or `null`)
* `issue_category` (Structured Provenance String, max 50 chars, or `null`)
* `root_cause_candidate` (Structured Provenance String, max 200 chars, or `null`): Must be `EXPLICIT` only when the transcript explicitly states the cause. `MODEL_DERIVED` must never be presented as confirmed manufacturing facts or observed root causes. `UNKNOWN` when the cause is absent.
* `downtime_minutes` (Structured Provenance Integer >= 0, or `null`)
* `severity_candidate` (Enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, `UNKNOWN`, or `null`): LLM severity is an extraction candidate, NOT authoritative operational risk. Canonical risk remains a later deterministic application-layer responsibility.
* `quantity_affected` (Structured Provenance Integer >= 0, or `null`)
* `event_time_reference` (String, max 100 chars, or `null`): Must remain a literal temporal reference (e.g., "abhi", "kal", "2 ghante pehle"). Do not silently convert relative time to an absolute timestamp inside the LLM.
* `model_confidence` (Float, 0.0 to 1.0): This is a model-reported confidence signal and is NOT a calibrated probability.

**Missing/Unknown Data Semantics:**
Empty strings (`""`) must not be used as an alternative representation for unknown. 

## 3. Data Model & Database Constraints

```python
class ExtractedEventCandidate(Base):
    __tablename__ = "extracted_event_candidates"
    id = Column(String, primary_key=True)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    transcript_id = Column(String, ForeignKey("communication_transcripts.id"), unique=True, nullable=False)
    
    # State tracking
    processing_status = Column(String, nullable=False, default="PENDING")
    validation_status = Column(String, nullable=True)
    
    # Reproducibility
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    prompt_hash = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)
    schema_hash = Column(String, nullable=True)
    
    # Outputs
    payload = Column(JSONB, nullable=True)
    raw_llm_response = Column(Text, nullable=True)
    
    # Human Review
    human_correction_payload = Column(JSONB, nullable=True)
    corrected_by = Column(String, nullable=True)
    corrected_at = Column(DateTime(timezone=True), nullable=True)
    correction_reason = Column(Text, nullable=True)
    
    # Cost & Observability
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    provider_request_id = Column(String, nullable=True)
    
    # Worker & Recovery
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String, nullable=True)
```

**Database Constraints Strategy:**
* `UNIQUE(transcript_id)` guarantees exactly-one persisted candidate record per transcript.
* `FOREIGN KEY(company_id)` to `companies.id`.
* `FOREIGN KEY(transcript_id)` to `communication_transcripts.id`.
* Database indexes on `processing_status` and `lease_until` to optimize worker polling.
* Tenant identity (`company_id`) is strictly inherited from the trusted `CommunicationTranscript`.

## 4. Processing Status vs Validation Status

These fields maintain strict separation between execution lifecycle and semantic acceptability.

**Processing Statuses (Execution Lifecycle):**
* `PENDING`: Candidate ready to be picked up.
* `PROCESSING`: Worker has claimed the row.
* `COMPLETED`: LLM extraction finished and parsed successfully (does not mean validation passed).
* `NEEDS_REVIEW`: Sent for review due to execution boundary issues (e.g., oversized input, provider refusal).
* `FAILED`: Terminal failure (exhausted attempts or permanent error).

**Validation Statuses (Semantic Acceptability):**
* `NULL`: Initial state before validation execution.
* `VALID`: Payload passed all schema bounds and domain determinism.
* `INVALID`: Schema violations or deterministic rule violations.
* `NEEDS_REVIEW`: Flagged by application policy (e.g., suspicious model behavior).

A successfully executed extraction may have `processing_status = COMPLETED` alongside `validation_status = NEEDS_REVIEW`.

**Human Review Semantics:**
Human correction MUST preserve the original model output. Corrections are stored in `human_correction_payload`, `corrected_by`, `corrected_at`, and `correction_reason`. Original fields are never overwritten.

## 5. Idempotency & Worker Recovery

**At-least-once LLM invocation + exactly-one persisted candidate record.**

`UNIQUE(transcript_id)` guarantees exactly one persisted candidate record, NOT exactly-once external provider invocation. 
`attempt_count` tracks the number of external LLM invocations actually started. `MAX_ATTEMPTS = 3`.

**Worker Lifecycle:**
1. **Claim:** `SELECT FOR UPDATE SKIP LOCKED` where `processing_status = 'PENDING'` OR `(processing_status = 'PROCESSING' AND lease_until < NOW())`.
2. **Commit:** Set `processing_status = 'PROCESSING'`, `worker_id`, `lease_until`. Commit the transaction immediately.
3. **LLM Call:** Execute network request entirely outside of database row locks. A worker crash after this step but before finalization will result in lease expiration and another provider invocation after lease recovery. This is acceptable.
4. **Finalize:** Begin new transaction, verify worker lease ownership, record outputs, update status, and commit.

## 6. Provider Abstraction & Contract

**Canonical Interface:**
The ONE canonical interface for extraction is:
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
    pass
```

**ExtractionMetadata:**
`ExtractionMetadata` is a strongly typed structure. Its explicit purpose is to provide the provider with necessary reproducibility context and routing parameters without acting as an uncontrolled instruction channel.
* `transcript_id`: Used for logging and tracing the origin of the extraction request natively within the provider infrastructure if required.
* `attempt_count`: Indicates if this is a retry attempt, allowing provider adapters to fallback or adjust network timeouts dynamically.
* `provider_name_override`: Allows safe A/B model routing for experiments without impacting the domain interface.

It must NOT be capable of overriding:
* tenant identity
* extraction schema
* system safety instructions
* application authorization
* processing state

**Provider Failure Mapping:**
* **RETRYABLE** (HTTP 429, HTTP 5xx, timeout, network failure): 
  - Increment `attempt_count`. 
  - Retry only while `attempt_count < MAX_ATTEMPTS`. 
  - After `MAX_ATTEMPTS`, `processing_status = FAILED`.
* **PERMANENT** (HTTP 400, 401, 403, unsupported structured output): 
  - `processing_status = FAILED`. 
  - No automatic retry.
* **REQUIRES_REVIEW** (provider refusal, malformed structured output, incomplete structured output): 
  - `processing_status = NEEDS_REVIEW`. 
  - No automatic retry. Tests explicitly verify this avoids transient retry loops.

## 7. Transcript Constraints & Security

**Oversized Transcript:**
If transcript length exceeds MAX_TRANSCRIPT_CHARS:
* Do NOT truncate.
* Do NOT invoke the LLM.
* Set processing_status = NEEDS_REVIEW.
* Set last_error = "OVERSIZED_INPUT".
* Do not automatically retry.
* Future chunking is out of scope.

**Prompt Injection Defense:**
Transcript is treated purely as untrusted user input inside the `user` message.

**Token Observability:**
We persist `input_tokens`, `output_tokens`, `latency_ms`, `provider_request_id`, `model`, and `provider`. 
If provider usage is unavailable:
input_tokens = NULL
output_tokens = NULL

Zero is permitted only when the provider explicitly reports zero.

## 8. Evaluation Framework

A comprehensive evaluation suite separates extraction metrics from Phase 3E entity resolution.

**Field-level Accuracy Metrics:**
* `event_type` accuracy
* `machine_reference`, `work_order_reference`, `customer_reference`, `product_reference`, `vendor_reference` accuracy
* `issue_category` accuracy
* `root_cause_explicitness_accuracy`
  It must verify:
  EXPLICIT: The transcript explicitly states the root cause.
  MODEL_DERIVED: The value is an interpretation/inference and must never be treated as observed evidence.
  UNKNOWN: The transcript does not establish a root cause.
* `downtime` and `quantity` accuracy
* `temporal-reference` accuracy
* `severity-candidate` accuracy

**System Metrics:**
* Hallucination rate
* Schema-validity rate

**Test Vectors:**
* English, Hindi, and Hinglish.
* Dense manufacturing terminology.
* Ambiguous language and missing information.
* Out-of-domain messages.
* Prompt injection attacks.
