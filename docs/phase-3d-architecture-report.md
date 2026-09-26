# Phase 3D Architecture Final Report

## Executive Summary
This report details the final Phase 3D — LLM Event Extraction architecture, completing the planning stage for safe, durable extraction of manufacturing events from trusted transcripts. 

**Status:** Architecture proposed, corrected, and awaiting final CTO approval.

## 1. Trust & Boundary Controls
* **Unstructured to Candidate ONLY:** Phase 3D creates untrusted `ExtractedEventCandidate` records. It explicitly does **NOT** resolve entities, create canonical `ManufacturingEvent` records, or evaluate operational risk.
* **LLM Tool Authority:** The LLM acts purely as a semantic interpreter. It has strictly NO database write access, NO entity-resolution authority, and NO risk mutation authority.
* **Idempotency & Processing:** Guarantees **At-least-once LLM invocation + exactly-one persisted candidate record**. Duplicate external calls are safely handled and absorbed by `UNIQUE(transcript_id)`.

## 2. Field-Level Provenance
To protect the integrity of manufacturing evidence, extracted fields carry explicit provenance tags:
* `EXPLICIT`: Observed/stated directly in the transcript.
* `MODEL_DERIVED`: An interpretation. Explicitly barred from being treated as confirmed manufacturing evidence (especially restricted for `root_cause_candidate`).
* `UNKNOWN`: Information is absent (represented strictly as `null`).

## 3. Worker Lifecycle & State Segregation
State tracking has been bifurcated to accurately represent the system state:
* **Processing Status** (Worker Execution): `PENDING` -> `PROCESSING` -> (`COMPLETED` | `NEEDS_REVIEW` | `FAILED`)
* **Validation Status** (Semantic Quality): `NULL` -> (`VALID` | `NEEDS_REVIEW` | `INVALID`)

A dedicated `attempt_count` (Max 3) dictates execution logic. Provider failures map directly to `RETRYABLE`, `PERMANENT`, or `REQUIRES_REVIEW` handling paths.

## 4. Constraint Hardening
* **Oversized Transcripts:** Strict rule enforced against silent truncation. Transcripts exceeding token/character limits are immediately flagged `NEEDS_REVIEW` with `OVERSIZED_INPUT`.
* **Token Observability:** Strict `NULL` persistence when provider usage reporting is absent. `0` is logged strictly if the provider explicitly reports `0`.
* **Cost & Observability:** Immutably preserved `prompt_hash` and `schema_hash` guarantee long-term evaluation reproducibility even as prompts evolve.

## 5. Evaluation Framework
Phase 3D evaluation operates completely decoupled from Phase 3E (Entity Resolution). Key metrics include:
* Field-level extraction accuracy.
* The bespoke `root_cause_explicitness_accuracy` metric testing the EXPLICIT vs MODEL_DERIVED barrier.
* Strict measurement of hallucination rate, schema-validity, prompt injection resilience, and multilingual support (Hindi, Hinglish, English).
