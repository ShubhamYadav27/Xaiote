# Phase 3E Entity Resolution Architecture

## 1. Objective
This phase designs the deterministic Entity Resolution layer. Its purpose is to securely and deterministically map untrusted references extracted by Phase 3D (`ExtractedEventCandidate`) to canonical Master Data entities (Machine, Work Order, Customer, Product, Vendor). It must preserve a rigorous audit trail and fallback to human review when ambiguity arises.

## 2. Trusted Plant Context
Explicitly, trusted plant context for Machine and Work Order resolution originates from the following sources:
- **Current MVP Trusted Plant Context**: A unique exact Work Order match within the same extracted candidate establishes trusted plant context for Machine resolution.
- **Future/Optional Context**: If a `User` or `AuthorizedSender` becomes explicitly bound to a `plant_id` in a future schema/integration extension, that may provide trusted plant context. However, Phase 3E implementation must NOT assume such a field exists today.

**Fallback Behavior:**
If no trusted plant context exists:
- Do not search all plants globally with fuzzy matching.
- Do not select a machine based on highest score across plants.
- Do not invent plant context.
The resolution must immediately return `AMBIGUOUS` or `UNRESOLVED` according to collision/context rules.

## 3. Actual Phase 2 Canonical Identities
Phase 3E strictly utilizes the actual canonical identity constraints implemented in Phase 2. The resolution must clearly distinguish lookup fields from the unique constraints.

- **Customer**: `uq_customer_company_name`, `uq_customer_company_external_id`
- **Vendor**: `uq_vendor_company_name`, `uq_vendor_company_external_id`
- **Product**: `uq_product_company_name`, `uq_product_company_sku`
- **Machine**: `uq_machine_company_plant_name`, `uq_machine_company_plant_external_id`
- **Work Order**: `uq_work_order_company_plant_order_number`

Phase 3E only resolves against entities that physically exist within the applicable tenant/plant scope. Master records currently lack an explicit `is_active` boolean (excepting Work Order `status`); future master lifecycle semantics are outside this phase. No new uniqueness constraints or aliases are invented.

## 4. Entity-Specific Normalization Policies
There is one authoritative normalization policy. Normalization is a matching aid only; `original_reference` must always remain preserved.

- **Machine & Work Order**: 
  - Lowercase.
  - Trim outer whitespace.
  - Collapse internal whitespace.
  - Retain hyphens.
  - Retain underscores.
  - Strip only explicitly allowed trailing punctuation.
- **Customer, Vendor, Product**:
  - Lowercase.
  - Trim outer whitespace.
  - Collapse internal whitespace.
  - Retain punctuation entirely (e.g., "Inc.", "LLC").

## 5. Formalized Fuzzy Decision Logic & Matching Precedence
The resolution result must explicitly distinguish matching methods. The deterministic decision logic executes in the following precedence:

1. **RAW_EXACT**: Evaluate exact original reference against canonical fields.
   - If exactly one valid candidate exists → `RESOLVED`.
   - If multiple exact candidates exist → `AMBIGUOUS`.
2. **NORMALIZED_EXACT**: If no raw exact candidate exists, evaluate `normalized_reference` against normalized canonical fields.
   - If exactly one normalized candidate exists → `RESOLVED`.
   - If multiple normalized candidates exist → `AMBIGUOUS`.
3. **FUZZY**: If no normalized match exists, retrieve only bounded candidates within tenant/plant scope utilizing PostgreSQL `pg_trgm` (`similarity()`). No embeddings, vector search, or LLM resolution are permitted.
   - Filter candidates where similarity `<` entity-specific provisional threshold.
   - If zero candidates remain → `UNRESOLVED`.
   - If one candidate remains `>=$` threshold → `RESOLVED`.
   - If multiple candidates remain `>=$` threshold:
     - Calculate `top_score`.
     - Calculate `second_score`.
     - Calculate `margin = top_score - second_score`.
     - If `margin >` entity-specific ambiguity margin → `RESOLVED` (selecting top_score).
     - Otherwise (margin `<=` ambiguity margin) → `AMBIGUOUS`.

## 6. Threshold Configuration
Fuzzy thresholds must be explicitly marked as **PROVISIONAL**, entity-specific, configurable, versioned, and auditable. Empirical evaluation is required before production calibration.
- `provisional_machine_fuzzy_threshold`: 0.85
- `provisional_machine_ambiguity_margin`: 0.15
- `provisional_work_order_fuzzy_threshold`: 0.90
- `provisional_work_order_ambiguity_margin`: 0.10

## 7. Reference-Level States
- `RESOLVED`: Safe deterministic entity mapping completed successfully.
- `AMBIGUOUS`: Multiple candidate results exist within the acceptable ambiguity margin or exact collisions occurred.
- `UNRESOLVED`: Valid candidate extracted, but zero matches met the threshold limit.
- `REFERENCE_ABSENT`: Extracted LLM payload explicitly returned a null, empty string, or whitespace-only value. A null reference is not an unresolved reference.

## 8. Overall Status Lifecycle
Defines deterministic rules for the `ExtractedEventCandidate`'s overall resolution phase:
- `COMPLETED`: All extracted required references (Machine, Work Order, Customer, etc.) achieved `RESOLVED` or `REFERENCE_ABSENT` states.
- `NEEDS_REVIEW`: At least one extracted reference resulted in `AMBIGUOUS` or `UNRESOLVED`.
- `FAILED`: Hard system/DB failure during resolution.

*Examples:*
- Machine resolved, WO resolved, Customer resolved → `COMPLETED`
- Machine resolved, WO unresolved, Customer resolved → `NEEDS_REVIEW`
- Machine resolved, WO absent, Customer resolved → `COMPLETED`
- Machine ambiguous, WO resolved, Customer resolved → `NEEDS_REVIEW`
- No references present → `COMPLETED`

## 9. Partial Resolution Contract
Only a reference explicitly marked `RESOLVED` may be consumed as a canonical entity reference. `AMBIGUOUS` and `UNRESOLVED` references must never silently resolve. Partial resolution state is preserved for audit and review.

## 10. Audit Immutability Model
The automated resolution decision must be strictly immutable. Human review must not mutate master data or overwrite the automated decision. 

**Automated Resolution Record:**
- `input_reference`, `normalized_reference`, `entity_type`
- `candidate_set` (Array of candidate IDs), `candidate_scores`, `selected_candidate_id`
- `matching_method`, `threshold`, `ambiguity_margin`
- `resolver_version`, `configuration_version`, `timestamp`, `decision`

**Human Review Record (Append-Only):**
- `authenticated_reviewer_id`
- `previous_resolution_state`
- `human_selected_canonical_entity`
- `reason`, `timestamp`, `review_action`, `review_version`

Human review MUST NOT modify Customer, Vendor, Product, Machine, or Work Order master records. It simply appends a new human resolution decision.

## 11. Human Review Security
Human override must explicitly verify:
- Authenticated actor -> Authorized role.
- Selected entity -> Same company -> Correct plant scope where applicable.
- Canonical entity physically exists.
The reviewer must not be able to resolve a Machine to another tenant or plant.

## 12. Processing Lifecycle & Idempotency
Phase 3E utilizes the proven PostgreSQL durable worker pattern from Phase 3C/3D (`PENDING`, `PROCESSING`, `COMPLETED`, `NEEDS_REVIEW`, `FAILED`).
- Uses `SELECT ... FOR UPDATE SKIP LOCKED` for lease semantics, worker ownership, and stale worker recovery.
- **Idempotency Rule**: Worker processing remains at-least-once. Database uniqueness (`UNIQUE(candidate_id)`) guarantees exactly one persisted resolution result per candidate. A crash after external processing may cause repeated processing attempts, but must not create duplicate canonical resolution-result rows.

## 13. Phase 3D Compatibility
Phase 3D remains frozen. Phase 3E exclusively READS `ExtractedEventCandidate`. Phase 3E must NOT modify the original LLM payload, raw transcript, raw communication evidence, or create/mutate master records.
