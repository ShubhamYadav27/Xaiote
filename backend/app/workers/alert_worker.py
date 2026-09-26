import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.alerts import AlertEvaluationJob, AlertEvaluationJobStatus
from app.services.alert_evaluator import process_alert_job

logger = logging.getLogger(__name__)

async def run_alert_worker(max_iterations: int = 100):
    worker_id = str(uuid.uuid4())
    
    for _ in range(max_iterations):
        async with AsyncSessionLocal() as session:
            # Transaction A: Claim Job
            async with session.begin():
                stmt = (
                    select(AlertEvaluationJob)
                    .where(
                        (AlertEvaluationJob.status == AlertEvaluationJobStatus.PENDING.value)
                        | (
                            (AlertEvaluationJob.status == AlertEvaluationJobStatus.PROCESSING.value)
                            & (AlertEvaluationJob.lease_until < datetime.now(timezone.utc))
                        )
                    )
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                
                result = await session.execute(stmt)
                job = result.scalar_one_or_none()
                
                if not job:
                    await asyncio.sleep(0.5)
                    continue
                
                job.status = AlertEvaluationJobStatus.PROCESSING.value
                job.worker_id = worker_id
                job.lease_until = datetime.now(timezone.utc) + timedelta(minutes=5)
                job.attempt_count += 1
                job_id = job.id
            
            # Transaction B: Evaluate
            try:
                async with AsyncSessionLocal() as eval_session, eval_session.begin():
                    stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                    eval_job = (await eval_session.execute(stmt)).scalar_one()
                    
                    await process_alert_job(eval_session, eval_job)
            except IntegrityError as e:
                # Handle rollback gracefully
                async with AsyncSessionLocal() as fail_session, fail_session.begin():
                    stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                    fail_job = (await fail_session.execute(stmt)).scalar_one()
                    if "uq_active_alert_wo" in str(e) or "ix_alert_instances_dedup" in str(e):
                        fail_job.status = AlertEvaluationJobStatus.COMPLETED.value
                    else:
                        fail_job.status = AlertEvaluationJobStatus.FAILED.value
                        fail_job.error_detail = str(e)
            except Exception as e:  # noqa: BLE001
                logger.error(f"Alert evaluation failed: {e}")
                async with AsyncSessionLocal() as fail_session, fail_session.begin():
                    stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                    fail_job = (await fail_session.execute(stmt)).scalar_one()
                    if fail_job.attempt_count >= 3:
                        fail_job.status = AlertEvaluationJobStatus.FAILED.value
                        fail_job.error_detail = str(e)
                    else:
                        fail_job.status = AlertEvaluationJobStatus.PENDING.value
                        fail_job.lease_until = None
