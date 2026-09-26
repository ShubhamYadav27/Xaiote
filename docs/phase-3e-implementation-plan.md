# Phase 3E Implementation Plan

**STATUS: PLAN ONLY. NO IMPLEMENTATION HAS COMMENCED.**

## 1. Files Inspected
- `app/models/masters.py`
- `app/models/work_order.py`
- `app/models/communication.py`
- `app/models/user.py`
- `app/models/whatsapp.py`
- `app/schemas/extraction.py`
- `app/workers/extraction_worker.py`
- `app/core/prompts.py`

## 2. Existing Constraints Inherited
- `uq_work_order_company_plant_order_number`
- `uq_customer_company_name`, `uq_customer_company_external_id`
- `uq_vendor_company_name`, `uq_vendor_company_external_id`
- `uq_product_company_name`, `uq_product_company_sku`
- `uq_machine_company_plant_name`, `uq_machine_company_plant_external_id`
- `extracted_event_candidates.transcript_id` (Unique lineage constraints)

## 3. Implementation Sequence (Proposed)

### Step 1: Data Model Creation
- Define immutable `EntityResolutionAudit` mapping automated resolution (input, normalized, threshold, method, scores, version, decision).
- Define append-only `HumanReviewAudit` mapping human resolution decisions (reviewer ID, selected ID, previous state, timestamp, reason).
- Enforce `UNIQUE(candidate_id)` to guarantee exactly one persisted resolution result per candidate, while worker processing remains at-least-once.

### Step 2: Database Migration
- Generate Alembic migration.
- (To be executed only after implementation unlocked)

### Step 3: Resolution Engine Logic
- Create `app/services/resolution_engine.py`.
- Implement `normalize_string()` using strict, entity-specific rules defined in the architecture (retaining hyphens/underscores for machines/work orders, retaining all punctuation for customers/products/vendors).
- Implement `RAW_EXACT` natively against database.
- Implement `NORMALIZED_EXACT` against normalized expressions.
- Implement strictly scoped `FUZZY` searches utilizing PostgreSQL `pg_trgm` (`similarity()`) exclusively.
- Implement configurable, versioned, entity-specific PROVISIONAL thresholds (e.g., `0.85`, `0.90`) and margin formulas (e.g. `margin > ambiguity_margin`).
- Hard-code explicit plant-context derivation strictly from an exact Work Order match within the candidate, failing back safely to `AMBIGUOUS`/`UNRESOLVED`.

### Step 4: Worker Loop Implementation
- Create `app/workers/resolution_worker.py` utilizing the durable `SELECT ... FOR UPDATE SKIP LOCKED` pattern (`PENDING`, `PROCESSING`, `COMPLETED`, `NEEDS_REVIEW`, `FAILED`).
- Process candidates sequentially, determining `REFERENCE_ABSENT`, `RESOLVED`, `AMBIGUOUS`, or `UNRESOLVED` states per reference.
- Calculate overall status based on deterministic aggregation (e.g., single `AMBIGUOUS` forces overall `NEEDS_REVIEW`).

### Step 5: Test Strategy & Coverage
Before acceptance, tests must explicitly cover:
- `raw exact`: Direct literal match.
- `normalized exact`: Normalization succeeds based on explicit entity rules.
- `entity-specific normalization`: Asserts WO dashes are preserved while trailing spaces are collapsed.
- `tenant isolation`: Cross-tenant visibility blocks matches.
- `plant isolation`: Machine limits cleanly to derived plant_id.
- `missing plant context`: Proves fallback securely defaults to `UNRESOLVED`/`AMBIGUOUS` without globally searching fuzzy matches.
- `fuzzy acceptance`: A single candidate safely clears threshold and margin parameters.
- `fuzzy ambiguity`: Two candidates clash within margin boundary.
- `exact-match collision`: Two exact matches collide, throwing `AMBIGUOUS` directly.
- `null reference`: Maps cleanly to `REFERENCE_ABSENT`.
- `empty reference`: Maps cleanly to `REFERENCE_ABSENT`.
- `unresolved reference`: Meaningful extraction yields 0 matches.
- `partial resolution`: Partially resolved references securely yield overall `NEEDS_REVIEW`.
- `human review authorization`: Proves tenant boundary blocking on manual review.
- `human review lineage preservation`: Validates append-only history without overwriting original automation.
- `concurrent resolution`: Polling guarantees exact-one DB persistence despite at-least-once processing attempts.
- `stale worker`: Lease expiration recovers candidate safely.
- `idempotency`: DB constraints explicitly block duplicates.
- `resolver configuration/version audit`: Validates correct persistent versions on audit JSON.

## 4. Explicit Non-Goals
Confirming Phase 3E unequivocally excludes implementation of:
- `ManufacturingEvent` canonical generation.
- Impact Engine calculations.
- Risk Engine logic.
- Predictions or ML-based Recommendations.
- Alerts / Predictive Maintenance.
- Vector search, embeddings, LLM-based logic.
- IoT integration/pipelines.
- Phase 3F Logic.
- Mutating original LLM payloads or Master Data records.

---
**PHASE 3E — ARCHITECTURE CONSISTENCY PASS COMPLETE, AWAITING CTO ACCEPTANCE**
