"""Phase 3E: Entity Resolution Worker."""

import asyncio
import datetime
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.communication import ExtractedEventCandidate
from app.models.resolution import EntityResolutionResult
from app.services.resolution_engine import ResolutionEngine

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 5
LEASE_DURATION_SECONDS = 120


async def claim_pending_candidate(
    db: AsyncSession, worker_id: str
) -> ExtractedEventCandidate | None:
    now = datetime.datetime.now(datetime.timezone.utc)
    lease_until = now + datetime.timedelta(seconds=LEASE_DURATION_SECONDS)

    # We need an ExtractedEventCandidate where processing_status='COMPLETED'
    # AND NOT EXISTS in entity_resolution_results (or exists but is PENDING/failed with low attempts)
    # The instruction says: Select ExtractedEventCandidate where processing_status='COMPLETED' AND NOT EXISTS in entity_resolution_results.
    # We will create an EntityResolutionResult immediately to claim it, or update an existing one.

    # First, let's find one that doesn't have a result yet.
    # We can do this safely using INSERT ... ON CONFLICT DO NOTHING, or we can just claim it if we assume 1-to-1 processing.
    # Let's insert a pending result first if not exists?
    # Or just select candidate, then create result.

    # Actually, a better way is to lock the candidate, check if result exists, if not create result and process.
    # Let's lock the candidate.

    result = await db.execute(
        text(
            """
            SELECT e.id, e.company_id 
            FROM extracted_event_candidates e
            LEFT JOIN entity_resolution_results r ON e.id = r.candidate_id
            WHERE e.processing_status = 'COMPLETED'
              AND (
                  r.id IS NULL 
                  OR 
                  (r.overall_status IN ('PENDING', 'PROCESSING') AND r.lease_until < :now AND r.attempt_count < :max_attempts)
              )
            ORDER BY e.created_at ASC
            LIMIT 1
            FOR UPDATE OF e SKIP LOCKED
            """
        ),
        {"now": now, "max_attempts": MAX_ATTEMPTS},
    )
    row = result.first()
    if not row:
        return None

    candidate_id, company_id = row

    # Now get or create the result
    res_result = await db.execute(
        select(EntityResolutionResult).where(
            EntityResolutionResult.candidate_id == candidate_id
        )
    )
    er = res_result.scalars().first()

    if not er:
        er = EntityResolutionResult(
            candidate_id=candidate_id,
            company_id=company_id,
            overall_status="PROCESSING",
            worker_id=worker_id,
            lease_until=lease_until,
            attempt_count=0,
        )
        db.add(er)
    else:
        er.overall_status = "PROCESSING"
        er.worker_id = worker_id
        er.lease_until = lease_until

    await db.flush()

    res = await db.execute(
        select(ExtractedEventCandidate).where(
            ExtractedEventCandidate.id == candidate_id
        )
    )
    return res.scalars().first()


async def process_one_candidate(worker_id: str) -> bool:
    candidate = None

    async with AsyncSessionLocal() as db:
        try:
            candidate = await claim_pending_candidate(db, worker_id)
            if not candidate:
                await db.rollback()
                return False
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"Resolution Worker claim error: {exc}")
            return False

    candidate_id = candidate.id
    payload = candidate.payload
    company_id = candidate.company_id

    # Process
    try:
        async with AsyncSessionLocal() as db:
            engine = ResolutionEngine(db, company_id)
            resolution_states = await engine.process(payload)

            # Determine global status
            states = [
                resolution_states["work_order_state"],
                resolution_states["machine_state"],
                resolution_states["customer_state"],
                resolution_states["vendor_state"],
                resolution_states["product_state"],
            ]

            # COMPLETED if all are RESOLVED or REFERENCE_ABSENT; NEEDS_REVIEW otherwise
            if all(s in ["RESOLVED", "REFERENCE_ABSENT"] for s in states):
                overall = "COMPLETED"
            else:
                overall = "NEEDS_REVIEW"

            res_q = await db.execute(
                select(EntityResolutionResult).where(
                    EntityResolutionResult.candidate_id == candidate_id,
                    EntityResolutionResult.worker_id == worker_id,
                )
            )
            er = res_q.scalars().first()
            if er:
                er.attempt_count += 1
                er.overall_status = overall
                er.processing_status = "COMPLETED"  # same as overall for consistency? Instruction says: overall_status
                # We'll update both
                er.machine_state = resolution_states["machine_state"]
                er.work_order_state = resolution_states["work_order_state"]
                er.customer_state = resolution_states["customer_state"]
                er.vendor_state = resolution_states["vendor_state"]
                er.product_state = resolution_states["product_state"]

                er.machine_id = resolution_states["machine_id"]
                er.work_order_id = resolution_states["work_order_id"]
                er.customer_id = resolution_states["customer_id"]
                er.vendor_id = resolution_states["vendor_id"]
                er.product_id = resolution_states["product_id"]

                er.automated_audit = resolution_states

                if overall == "COMPLETED":
                    from app.models.manufacturing_event import CanonicalizationJob

                    job = CanonicalizationJob(
                        candidate_id=candidate_id,
                        company_id=er.company_id,
                        status="PENDING",
                    )
                    db.add(job)
            await db.commit()
        return True

    except Exception as exc:  # noqa: BLE001
        print("RESOLUTION WORKER EXCEPTION:", exc, flush=True)
        async with AsyncSessionLocal() as db:
            try:
                res_q = await db.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == candidate_id,
                        EntityResolutionResult.worker_id == worker_id,
                    )
                )
                er = res_q.scalars().first()
                if er:
                    er.attempt_count += 1
                    if er.attempt_count >= MAX_ATTEMPTS:
                        er.overall_status = "FAILED"
                        er.processing_status = "FAILED"
                    else:
                        er.overall_status = "PENDING"
                        er.processing_status = "PENDING"
                    er.last_error = str(exc)[:500]
                await db.commit()
            except Exception as inner_exc:  # noqa: BLE001
                await db.rollback()
                logger.error(f"Failed to update error state: {inner_exc}")
        return True


async def resolution_worker_loop() -> None:
    worker_id = str(uuid.uuid4())
    logger.info(f"Resolution worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_candidate(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Resolution Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
