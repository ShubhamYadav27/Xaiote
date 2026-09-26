import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.communication import ExtractedEventCandidate
from app.models.manufacturing_event import (
    CanonicalizationJob,
    CanonicalizationJobStatus,
    EventStatus,
    ManufacturingEvent,
    ProvenanceType,
    TemporalProvenance,
)
from app.models.masters import Machine
from app.models.resolution import EntityResolutionResult
from app.models.work_order import WorkOrder
from app.services.impact_generator import evaluate_impacts_for_event

logger = logging.getLogger(__name__)
POLL_INTERVAL_SECONDS = 1


async def process_one_job(worker_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        # 1. Claim job using SKIP LOCKED
        job_q = await db.execute(
            select(CanonicalizationJob)
            .where(
                or_(
                    CanonicalizationJob.status == CanonicalizationJobStatus.PENDING,
                    and_(
                        CanonicalizationJob.status
                        == CanonicalizationJobStatus.PROCESSING,
                        CanonicalizationJob.lease_until < now,
                    ),
                )
            )
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = job_q.scalars().first()

        if not job:
            return False

        job.status = CanonicalizationJobStatus.PROCESSING
        job.worker_id = worker_id
        job.lease_until = now + timedelta(minutes=5)
        job.attempt_count += 1

        # COMMIT CLAIM BEFORE PROCESSING
        await db.commit()

        job_id = job.id
        candidate_id = job.candidate_id

    # 2. Processing
    try:
        async with AsyncSessionLocal() as db:
            # Re-fetch job
            j_res = await db.execute(
                select(CanonicalizationJob).where(CanonicalizationJob.id == job_id)
            )
            job = j_res.scalars().first()
            if not job or job.worker_id != worker_id:
                return True  # Stale worker, skip processing

            # Fetch resolution and candidate
            er_res = await db.execute(
                select(EntityResolutionResult).where(
                    EntityResolutionResult.candidate_id == candidate_id
                )
            )
            er = er_res.scalars().first()

            cand_res = await db.execute(
                select(ExtractedEventCandidate).where(
                    ExtractedEventCandidate.id == candidate_id
                )
            )
            cand = cand_res.scalars().first()

            if not er or not cand:
                raise ValueError("Missing resolution or candidate")

            payload: dict = cand.payload or {}
            event_type = payload.get("event_type", "OTHER")

            # Reference Matrix
            matrix = {
                "EQUIPMENT_FAILURE": {
                    "machine": "Required",
                    "work_order": "Optional",
                    "plant": "Optional",
                },
                "DOWNTIME": {
                    "machine": "Required",
                    "work_order": "Optional",
                    "plant": "Optional",
                },
                "MATERIAL_SHORTAGE": {
                    "machine": "Optional",
                    "work_order": "Optional",
                    "plant": "Optional",
                    "vendor": "Required",
                },
                "QUALITY_ISSUE": {
                    "machine": "Optional",
                    "work_order": "Required",
                    "plant": "Optional",
                    "product": "Required",
                },
                "MAINTENANCE_ISSUE": {
                    "machine": "Required",
                    "work_order": "Optional",
                    "plant": "Optional",
                },
                "PRODUCTION_DELAY": {
                    "machine": "Optional",
                    "work_order": "Required",
                    "plant": "Optional",
                },
                "SAFETY_INCIDENT": {"plant": "Required"},
                "OTHER": {},
            }
            reqs = matrix.get(event_type, {})

            # Plant Derivation
            wo_plant_id = None
            if er.work_order_id:
                wo_res = await db.execute(
                    select(WorkOrder.plant_id).where(WorkOrder.id == er.work_order_id)
                )
                wo = wo_res.first()
                if wo:
                    wo_plant_id = wo[0]

            m_plant_id = None
            if er.machine_id:
                m_res = await db.execute(
                    select(Machine.plant_id).where(Machine.id == er.machine_id)
                )
                m = m_res.first()
                if m:
                    m_plant_id = m[0]

            derived_plant_id = None
            if wo_plant_id and m_plant_id:
                if wo_plant_id != m_plant_id:
                    # Conflict!
                    # Revert ER to NEEDS_REVIEW, job to FAILED
                    er.overall_status = "NEEDS_REVIEW"
                    job.status = CanonicalizationJobStatus.FAILED
                    job.last_error = (
                        "Plant conflict: WO and Machine belong to different plants"
                    )
                    await db.commit()
                    return True
                else:
                    derived_plant_id = wo_plant_id
            elif wo_plant_id:
                derived_plant_id = wo_plant_id
            elif m_plant_id:
                derived_plant_id = m_plant_id

            # Matrix Evaluation
            states = {
                "machine": er.machine_state,
                "work_order": er.work_order_state,
                "customer": er.customer_state,
                "product": er.product_state,
                "vendor": er.vendor_state,
            }
            for ent, req in reqs.items():
                if ent == "plant":
                    if req == "Required" and not derived_plant_id:
                        er.overall_status = "NEEDS_REVIEW"
                        job.status = CanonicalizationJobStatus.FAILED
                        job.last_error = "Missing required Plant"
                        await db.commit()
                        return True
                else:
                    if req == "Required" and states.get(ent) != "RESOLVED":
                        er.overall_status = "NEEDS_REVIEW"
                        job.status = CanonicalizationJobStatus.FAILED
                        job.last_error = f"Missing required {ent}"
                        await db.commit()
                        return True

            # Passed matrix and conflicts -> Create Canonical Event

            # Temporal
            time_ref = payload.get("event_time_reference")
            can_time = None
            temp_prov = TemporalProvenance.UNKNOWN
            if time_ref:
                try:
                    can_time = datetime.fromisoformat(time_ref)
                    temp_prov = TemporalProvenance.EXPLICIT_TIMESTAMP
                except ValueError:
                    temp_prov = TemporalProvenance.UNKNOWN

            # Provenance
            # Model-derived MUST NOT silently become canonical.
            # So canonical fields are NULL, candidates get populated.
            sev_cand = payload.get("severity")
            rc_cand = payload.get("root_cause")

            ev = ManufacturingEvent(
                company_id=er.company_id,
                plant_id=derived_plant_id,
                candidate_id=candidate_id,
                event_idempotency_key=str(uuid.uuid4()),
                canonical_event_type=event_type,
                canonical_event_type_provenance=ProvenanceType.MODEL_DERIVED,
                description=payload.get("event_description"),
                severity=None,
                severity_provenance=ProvenanceType.UNKNOWN,
                root_cause=None,
                root_cause_provenance=ProvenanceType.UNKNOWN,
                extracted_severity_candidate=sev_cand,
                extracted_root_cause_candidate=rc_cand,
                event_time_reference=time_ref,
                canonical_occurrence_timestamp=can_time,
                temporal_provenance=temp_prov,
                event_status=EventStatus.CANONICAL,
            )

            db.add(ev)
            await db.flush()
            await evaluate_impacts_for_event(db, ev.id, ev.company_id)
            job.status = CanonicalizationJobStatus.COMPLETED
            await db.commit()
            return True

    except Exception as exc:  # noqa: BLE001
        logger.error(f"Worker Error: {exc}")
        async with AsyncSessionLocal() as db:
            j_res = await db.execute(
                select(CanonicalizationJob).where(CanonicalizationJob.id == job_id)
            )
            job = j_res.scalars().first()
            if job:
                job.status = CanonicalizationJobStatus.FAILED
                job.last_error = str(exc)
                await db.commit()
        return True


async def canonicalization_worker_loop():
    worker_id = str(uuid.uuid4())
    logger.info(f"Canonicalization worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_job(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Canonicalization Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
