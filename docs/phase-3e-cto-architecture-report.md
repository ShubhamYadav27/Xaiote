# Phase 3E - Entity Resolution Architecture Report

**Status:** PHASE 3E — ARCHITECTURE DRAFT COMPLETE, AWAITING CTO REVIEW

This report summarizes the finalized architecture and implementation plan for **Phase 3E: Entity Resolution** following the CTO Consistency Pass. 

## 1. Objective and Trust Boundary
Phase 3E establishes the deterministic Entity Resolution layer. Its purpose is to securely and deterministically map untrusted string references extracted by the LLM in Phase 3D (`ExtractedEventCandidate`) into safe, canonical Master Data identifiers (Machine, Work Order, Customer, Product, Vendor). 

Phase 3E is strictly a **READ-ONLY** mapping process. It does not modify Master Data, and it does not overwrite the original Phase 3D evidence payload.

## 2. Canonical Identity Enforcement
Phase 3E resolves against existing Phase 2 Master Data constraints without inventing new aliases or generic uniqueness rules:
*   **Customer**: `uq_customer_company_name`, `uq_customer_company_external_id`
*   **Vendor**: `uq_vendor_company_name`, `uq_vendor_company_external_id`
*   **Product**: `uq_product_company_name`, `uq_product_company_sku`
*   **Machine**: `uq_machine_company_plant_name`, `uq_machine_company_plant_external_id`
*   **Work Order**: `uq_work_order_company_plant_order_number`

## 3. Trusted Context and Scoping
*   **Tenant Scoping**: Sourced definitively from the evidence lineage (`communication_transcripts.company_id`). The LLM or user cannot override tenant scope. Cross-tenant queries are blocked at the database level.
*   **Plant Scoping**: MVP trusted plant context relies exclusively on a unique, exact Work Order match within the same extracted candidate. If this is unavailable, the resolver MUST conservatively mark Machine/Work Order resolutions as `AMBIGUOUS` or `UNRESOLVED`. It does not fall back to globally searching all plants.

## 4. Normalization Policy
Normalization aids matching but never overwrites the `original_reference`. It is entity-specific:
*   **Machine & Work Order**: Lowercase, trim outer whitespace, collapse internal whitespace, retain hyphens, retain underscores, strip only explicitly allowed trailing punctuation.
*   **Customer, Vendor, Product**: Lowercase, trim outer whitespace, collapse internal whitespace, retain punctuation completely.

## 5. Resolution Precedence & Fuzzy Logic
The deterministic decision logic executes in strict precedence:
1.  **`RAW_EXACT`**: Literal match. (If multiple matches exist due to legacy data anomalies -> `AMBIGUOUS`).
2.  **`NORMALIZED_EXACT`**: Match on normalized indexes.
3.  **`FUZZY`**: Bounded retrieval exclusively using PostgreSQL `pg_trgm` (`similarity()`). LLM, embeddings, and vector searches are prohibited. 
    *   Filters candidates where similarity `<` threshold.
    *   If 1 candidate `>=` threshold -> `RESOLVED`.
    *   If multiple candidates `>=` threshold, compute `margin = top_score - second_score`.
    *   If `margin > ambiguity_margin` -> `RESOLVED`.
    *   If `margin <= ambiguity_margin` -> `AMBIGUOUS`.
4.  **`UNRESOLVED`**: Zero matches met the threshold.

Thresholds are strictly **PROVISIONAL**, configurable, versioned, and auditable per entity (e.g., `provisional_machine_fuzzy_threshold: 0.85`).

## 6. State Machine
*   **Reference-Level States**: `RESOLVED`, `AMBIGUOUS`, `UNRESOLVED`, and `REFERENCE_ABSENT` (mapped from explicit nulls/empty strings).
*   **Overall Status Lifecycle**:
    *   `COMPLETED`: All extracted required references achieved `RESOLVED` or `REFERENCE_ABSENT`.
    *   `NEEDS_REVIEW`: At least one extracted reference achieved `AMBIGUOUS` or `UNRESOLVED`.
    *   `FAILED`: Internal system/DB failure.

## 7. Audit Immutability & Human Override
*   **Automated Audit**: Strictly immutable. Records input reference, normalized reference, considered candidate sets, methodology, scores, and resolver versions.
*   **Human Override**: Strictly **append-only**. Authenticated users issue a human resolution decision which appends their `reviewer_id`, selected canonical ID, reason, and timestamp. It never mutates Master Data or automated history.

## 8. Worker Concurrency and Idempotency
Phase 3E utilizes the durable PostgreSQL worker pattern via `SELECT ... FOR UPDATE SKIP LOCKED`. 
*   **Worker Execution**: Operates at-least-once with lease recovery semantics.
*   **Database Persistence**: Enforced exactly-one persistence via `UNIQUE(candidate_id)` on the resolution result table to prevent duplicate master mappings on worker crashes.

## 9. Explicit Non-Goals
Phase 3E exclusively produces entity resolution mapping. It does **not** implement:
*   `ManufacturingEvent` canonical generation.
*   Impact Engine, Risk Engine, Predictions, Recommendations, or Alerts.
*   IoT integration.
*   Phase 3F workflows.
