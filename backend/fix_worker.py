import os

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
            try:
                async with AsyncSessionLocal() as eval_session:
                    async with eval_session.begin():
                        stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                        eval_job = (await eval_session.execute(stmt)).scalar_one()
                        
                        await process_alert_job(eval_session, eval_job)
            except IntegrityError as e:
                # Handle rollback gracefully
                async with AsyncSessionLocal() as fail_session:
                    async with fail_session.begin():
                        stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                        fail_job = (await fail_session.execute(stmt)).scalar_one()
                        if "uq_active_alert_wo" in str(e) or "ix_alert_instances_dedup" in str(e):
                            fail_job.status = AlertEvaluationJobStatus.COMPLETED.value
                        else:
                            fail_job.status = AlertEvaluationJobStatus.FAILED.value
                            fail_job.error_detail = str(e)
            except Exception as e:
                logger.error(f"Alert evaluation failed: {e}")
                async with AsyncSessionLocal() as fail_session:
                    async with fail_session.begin():
                        stmt = select(AlertEvaluationJob).where(AlertEvaluationJob.id == job_id)
                        fail_job = (await fail_session.execute(stmt)).scalar_one()
                        if fail_job.attempt_count >= 3:
                            fail_job.status = AlertEvaluationJobStatus.FAILED.value
                            fail_job.error_detail = str(e)
                        else:
                            fail_job.status = AlertEvaluationJobStatus.PENDING.value
                            fail_job.lease_until = None
''')

with open(r'app/services/alert_evaluator.py', 'r', encoding='utf-8') as f:
    t = f.read()

# Remove the try/except IntegrityError from inside the evaluator so it bubbles up.
t = t.replace('        try:\n', '')
t = t.replace('            if action == MatrixAction.CREATE:\n', '        if action == MatrixAction.CREATE:\n')
t = t.replace('''    except IntegrityError:
        job.status = AlertEvaluationJobStatus.COMPLETED.value
        await db.rollback()
        # It's a duplicate alert for the same family and target due to partial index.
''', '')
# Fix indentation globally
lines = t.split('\n')
new_lines = []
for l in lines:
    if l.startswith('            new_alert = AlertInstance'):
        l = '        new_alert = AlertInstance'
    elif l.startswith('            ') and 'except IntegrityError:' not in l:
        new_lines.append(l[4:])
        continue
    new_lines.append(l)

with open(r'app/services/alert_evaluator.py', 'w', encoding='utf-8') as f:
    f.write('\n'.join(new_lines))
