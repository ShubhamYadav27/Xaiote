import os

os.makedirs('app/workers', exist_ok=True)
with open(r'app/workers/alert_worker.py', 'w', encoding='utf-8') as f:
    f.write('''import asyncio
import logging
from datetime import datetime, timezone, timedelta
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, DBAPIError

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
            async with AsyncSessionLocal() as eval_session:
                async with eval_session.begin():
                    # Re-fetch the job
                    stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                    eval_job = (await eval_session.execute(stmt)).scalar_one()
                    
                    try:
                        # process_alert_job will mutate eval_job and the database
                        await process_alert_job(eval_session, eval_job)
                    except IntegrityError as e:
                        if "uq_active_alert_wo" in str(e) or "ck_alert_" in str(e):
                            # Deduplication -> NO_OP
                            eval_job.status = AlertEvaluationJobStatus.COMPLETED.value
                        else:
                            eval_job.status = AlertEvaluationJobStatus.FAILED.value
                            eval_job.error_detail = str(e)
                    except Exception as e:
                        logger.error(f"Alert evaluation failed: {e}")
                        if eval_job.attempt_count >= 3:
                            eval_job.status = AlertEvaluationJobStatus.FAILED.value
                            eval_job.error_detail = str(e)
                        else:
                            # Re-pending
                            eval_job.status = AlertEvaluationJobStatus.PENDING.value
                            eval_job.lease_until = None
''')
