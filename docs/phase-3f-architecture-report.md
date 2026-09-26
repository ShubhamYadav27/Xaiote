# XAIOTE CTO PHASE 3F ARCHITECTURE REVIEW

## A. Corrected trust boundary
The trust boundary between Phase 3E (Resolution) and Phase 3F (Canonical Event) strictly divides **Inference** from **Fact**. 
A `ManufacturingEvent` acts as the canonical fact layer. It prevents unstructured, probabilistic, or LLM-derived guesses from masquerading as confirmed operational data downstream. Any retained inference (e.g., extracted severity, root cause candidates) must be encapsulated with explicit provenance demarcations preventing silent adoption by downstream risk or impact engines.

## B. Corrected ManufacturingEvent model
**Identity**:
- `id`: UUID (Primary Key)
- `company_id`: UUID (Foreign Key to Company)
- `plant_id`: UUID (Nullable, Foreign Key to Plant)
- `candidate_id`: UUID (Unique Foreign Key strictly mapping 1:1 to `EntityResolutionResult.candidate_id`)
- `event_idempotency_key`: String (Unique per company, based on technical origin to prevent duplicate ingestions)

**Confirmed/Canonical Fields**:
- `canonical_event_type`: Enum
- `canonical_event_type_provenance`: Enum
- `description`: String
- `severity`: Enum
- `severity_provenance`: Enum
- `root_cause`: String
- `root_cause_provenance`: Enum
- `reported_downtime_minutes`: Integer
- `quantity_affected`: Integer
- `canonical_occurrence_timestamp`: Datetime (Nullable)
- `temporal_provenance`: Enum

**Inference/Candidate Fields**:
- `extracted_severity_candidate`: String (Direct from LLM extraction)
- `extracted_root_cause_candidate`: String (Direct from LLM extraction)

**Processing/Lifecycle Fields (Business State Only)**:
- `event_status`: Enum (`CANONICAL`, `SUPERSEDED`, `REJECTED`)
- `superseded_by_event_id`: UUID (Nullable, Self-FK)
- `correlation_id`: UUID (Nullable, grouping identifier for future Incident mapping)

*(Processing state is separated into a durable canonicalization job record. See Section N).*

## C. Severity provenance
Phase 3D `severity_candidate` cannot automatically become canonical severity.
Canonical `severity` must carry explicit provenance tracking its origin:
- `EXPLICIT` (Explicitly stated by operator/reporter)
- `MODEL_DERIVED` (Inferred by the LLM, kept as inference)
- `HUMAN_CONFIRMED` (Verified by an authorized user)
- `UNKNOWN` (No severity determinable)
Only explicit or human-confirmed severity can act as canonical fact. Model-derived severity is stored purely as inference (`extracted_severity_candidate`).

## D. Event-type provenance
Phase 3D `event_type` is an LLM classification, not inherently verified.
Phase 3F introduces `canonical_event_type` and `canonical_event_type_provenance`.
A Phase 3D classification maps to a Canonical Event Type only when deterministic rules (or human review) validate it against the required reference matrix. The origin is tracked identically to severity (`EXPLICIT`, `MODEL_DERIVED`, `HUMAN_CONFIRMED`, `UNKNOWN`).

## E. Root-cause provenance
To prevent LLM hallucinations from corrupting root cause metrics, `root_cause` must carry explicit provenance:
- `EXPLICIT` (Operator explicitly stated the cause)
- `MODEL_DERIVED` (LLM inference; stored solely in `extracted_root_cause_candidate`)
- `HUMAN_CONFIRMED` (Validated by personnel)
- `UNKNOWN`

## F. Required/optional reference matrix
For every extracted event type (all 8 from Phase 3D), reference behaviors are strictly governed. 
- Required unresolved or ambiguous: Suspends to `NEEDS_REVIEW`.
- Optional unresolved or ambiguous: Proceeds to `CANONICAL` with NULL for that entity.
- Plant-less canonicalization: Permitted ONLY if Plant is "Optional" and remains unresolvable.

| Phase 3D Event Type | Machine | Work Order | Plant | Customer | Product | Vendor |
|---------------------|---------|------------|-------|----------|---------|--------|
| `MACHINE_FAILURE` | Required | Optional | Optional | Absent | Absent | Absent |
| `DOWNTIME` | Required | Optional | Optional | Absent | Absent | Absent |
| `MATERIAL_SHORTAGE` | Optional | Optional | Optional | Absent | Optional | Required |
| `QUALITY_ISSUE` | Optional | Required | Optional | Optional | Required | Absent |
| `MAINTENANCE_ISSUE` | Required | Optional | Optional | Absent | Absent | Optional |
| `PRODUCTION_DELAY` | Optional | Required | Optional | Absent | Optional | Absent |
| `SAFETY_INCIDENT` | Optional | Optional | Required | Absent | Absent | Absent |
| `OTHER` | Optional | Optional | Optional | Optional | Optional | Optional |

## G. Plant conflict rules
Plant contextual derivation is deterministic and global fallback is forbidden.
1. If Work Order Plant and Machine Plant agree → Valid.
2. If Work Order Plant and Machine Plant conflict → `NEEDS_REVIEW`.
3. If only Work Order exists → Inherit Work Order Plant.
4. If only Machine exists → Inherit Machine Plant.
5. If neither exists → Plant remains NULL (only if the event class explicitly permits plant-less events; otherwise `NEEDS_REVIEW`).
Silent selection of a conflicting plant is strictly prohibited.

## H. Deduplication/correlation semantics
Silent merging of events based on `(event_type + machine_id + time_window)` is unsafe and rejected.
- **Technical Duplicate**: Handled via idempotency keys at the ingestion/extraction boundary.
- **Business Correlation**: Multiple distinct reports (e.g., operator via audio, supervisor via text) remain distinct `ManufacturingEvent` records. They are correlated using a `correlation_id` pointer to a future Incident.
- **Event Update**: Represents supersession. A later event explicitly updating an earlier event sets the `superseded_by_event_id` pointer, ensuring the original report remains immutable.

## I. Event vs Incident boundary
`ManufacturingEvent` represents a single canonicalized report/fact from a specific source.
A future `Incident` represents the actual physical occurrence on the shop floor.
Many `ManufacturingEvents` may correlate to one `Incident`.
```text
Event A (Operator Audio) ─┐
Event B (Supervisor Text) ┼→ future Incident (The broken spindle)
Event C (Maintenance Log) ┘
```
Phase 3F implements `ManufacturingEvent` and correlation pointers, but the `Incident` entity remains OUT OF SCOPE.

## J. Resolution identity
The trust chain maps strictly through existing primary keys:
```text
ManufacturingEvent (FK: candidate_id)
    ↓
EntityResolutionResult (PK: candidate_id)
    ↓
ExtractedEventCandidate (PK: id)
    ↓
CommunicationTranscript (PK: id)
```
`ManufacturingEvent.candidate_id` serves as the rigid 1:1 uniqueness constraint enforcing idempotency.

## K. Tenant naming
The architecture will strictly adhere to `company_id` matching Phase 1–3E frozen foundation conventions. `tenant_id` will not be introduced.

## L. Temporal provenance
The `canonical_occurrence_timestamp` must track its deterministic origin via `temporal_provenance`:
- `EXPLICIT_TIMESTAMP`
- `DETERMINISTIC_RELATIVE_REFERENCE`
- `HUMAN_CONFIRMED`
- `UNKNOWN`
Ambiguous references ("kal") remain in `event_time_reference` and result in `UNKNOWN` temporal provenance with a NULL canonical timestamp.

## M. Event lifecycle
- `VALIDATING`: Evaluating Phase 3E resolution against required matrix via canonicalization worker.
- `CANONICAL`: Safely verified fact exposed downstream.
- `REJECTED`: Permanently invalidated.
- `SUPERSEDED`: Replaced by a newer corrected event.

## N. Processing/business state separation
We choose **OPTION B** (Separate canonicalization job/work record) augmented with **Option A — Transactional job creation** for the handoff to ensure absolute durability. 

The ManufacturingEvent contains only the business event_status. The worker processing state (PENDING, PROCESSING, COMPLETED, FAILED) is delegated to a separate durable CanonicalizationJob queue record.

**Transactional Handoff Guarantee**:
The handoff from Phase 3E to Phase 3F must never depend on a best-effort listener, FastAPI BackgroundTasks, or in-memory events. It is enforced as a single atomic database transaction:
- When the automated Phase 3E worker completes, it updates EntityResolutionResult to COMPLETED **and** inserts CanonicalizationJob(PENDING) in the exact same COMMIT.
- When human review occurs on a NEEDS_REVIEW record, the authenticated service updates the EntityResolutionResult to COMPLETED **and** inserts CanonicalizationJob(PENDING) in the exact same COMMIT.

**Failure Guarantees**:
- **Case 1**: Resolution completes and transaction commits. → CanonicalizationJob exists durably.
- **Case 2**: Resolution transaction rolls back. → No completed resolution and no orphan job is created.
- **Case 3**: Process crashes after commit. → Job remains PENDING in the database, and the Phase 3F polling worker will eventually process it.
- **Case 4**: Worker crashes during processing. → Lease expires and another worker safely retries.
- **Case 5**: Two workers race. → candidate_id uniqueness guarantees only one ManufacturingEvent is successfully inserted.
- **Case 6**: Human review resolves a NEEDS_REVIEW candidate. → The completion and canonicalization handoff are grouped atomically; both are durable upon commit.

## O. Evidence lineage
Lineage remains unbroken and deterministically traceable from `ManufacturingEvent.candidate_id` up the primary key chain to the raw `CommunicationMessage`. No evidence is duplicated or orphaned.

## P. Worker architecture
A dedicated PostgreSQL polling worker targeting the `CanonicalizationJob` queue implementing `FOR UPDATE SKIP LOCKED`. No Redis, Celery, or external queues are necessary.

## Q. Database architecture
- Table: `manufacturing_events`
- Primary Key: `id` (UUID)
- Company Scoping: `company_id` (UUID, Indexed)
- Resolution Relationship: `candidate_id` (UUID, UNIQUE FK)
- Plant Scope: `plant_id` (UUID)
- Canonical References: `machine_id`, `work_order_id`, `customer_id`, `product_id`, `vendor_id`
- Provenance Fields: `canonical_event_type_provenance`, `severity_provenance`, `root_cause_provenance`, `temporal_provenance`
- Status: `event_status` (VARCHAR)
- Supersession/Correlation: `superseded_by_event_id` (UUID FK), `correlation_id` (UUID)
- Audit: `audit_trail` (JSONB)

- Table: `canonicalization_jobs`
- Status: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`

## R. Transaction boundaries
The Canonicalization Worker executes a single atomic transaction:
1. `SELECT FOR UPDATE SKIP LOCKED` on `CanonicalizationJob`.
2. Evaluate Matrix rules against the underlying `EntityResolutionResult`.
3. `INSERT INTO manufacturing_events`.
4. `UPDATE canonicalization_jobs SET status = 'COMPLETED'`.
5. `COMMIT`.
Network calls under locks are prohibited. 

## S. API boundary
Future implementation will require:
- `GET /api/v1/events`
- `GET /api/v1/events/{id}`
- `POST /api/v1/events/{id}/supersede`
All APIs enforce tenant boundaries using authenticated tokens mapping to `company_id`.

## T. Security
Tenant isolation via `company_id` is absolute. Cross-company canonicalization is inherently blocked by `candidate_id` UUID lineage validation spanning down to the authenticated `CommunicationMessage`.

## U. Observability
Logging records sequential transitions and execution latency. Raw NLP candidate text and explicit evidence values remain strictly outside application logs to prevent PII/sensitive data leakage.

## V. Test strategy
Exhaustive matrix tests required covering:
- **Matrix compliance**: Missing required entities suspend to `NEEDS_REVIEW`; missing optional proceed to `CANONICAL`.
- **Plant derivation**: Cases 1-5 ensuring explicit conflict suspension.
- **Idempotency**: Concurrent worker collision handles 1:1 `candidate_id` constraint safely.
- **Provenance integrity**: Model inferences never populate canonical fields without `MODEL_DERIVED` flags.

## W. Future compatibility
The `correlation_id` and strict `event_status` allow future Phase 3G Risk, Impact, and Prediction engines to aggregate events into Incidents without requiring structural mutation of `ManufacturingEvent`.

## X. Explicit non-goals
No implementation of ManufacturingEvent, Incident, Risk Engine, impact calculations, automated root-cause ML, predictions, alerts, or vector search. Phase 1-3E code remains untouched.

## Y. Updated ADRs
- **Severity Trust**: Strict provenancing prevents inferred severity from becoming operational fact.
- **Deduplication**: Technical idempotency separated from semantic business correlation (future Incidents) to preserve historical reporting granularity.
- **Plant Conflict**: Deterministic rejection of conflicting derivations prevents silent location hallucinations.
- **Resolution Identity**: Unified around `candidate_id` to strictly respect Phase 3E data mapping.

## Z. Open questions
- Define exact criteria for triggering human-review resolution of conflicting plant identifiers spanning disparate extraction payloads.

---
PHASE 3F — ARCHITECTURE READY FOR CTO APPROVAL
