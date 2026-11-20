from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import (
    AlertEvaluationJob,
    AlertEvaluationJobStatus,
    AlertEvaluationJobRetryAudit
)

async def retry_failed_alert_evaluation_job(
    db: AsyncSession,
    job_id: str,
    company_id: str,
    actor_id: str,
    reason: str,
    user_plant_id: str | None = None
) -> AlertEvaluationJob:
    
    # Atomic lookup with lock
    stmt = select(AlertEvaluationJob).where(
        AlertEvaluationJob.id == job_id,
        AlertEvaluationJob.company_id == company_id
    )
    if user_plant_id:
        stmt = stmt.where(AlertEvaluationJob.plant_id == user_plant_id)
        
    stmt = stmt.with_for_update()
    
    job = (await db.execute(stmt)).scalar_one_or_none()
    
    if not job:
        raise HTTPException(status_code=404, detail="AlertEvaluationJob not found")
        
    if job.status != AlertEvaluationJobStatus.FAILED.value:
        raise HTTPException(status_code=400, detail="Only FAILED jobs can be retried")
        
    # Check for duplicate active job for the same target (concurrency protection beyond the lock)
    # The lock protects this specific job, but we also want to ensure we don't have another
    # PENDING/PROCESSING job for the exact same target if idempotency rules demand it.
    # However, the AlertEvaluator creates unique jobs per state transition.
    
    # Audit trail
    audit = AlertEvaluationJobRetryAudit(
        job_id=job.id,
        company_id=job.company_id,
        actor_id=actor_id,
        previous_state=job.status,
        new_state=AlertEvaluationJobStatus.PENDING.value,
        original_error=job.error_detail,
        retry_reason=reason
    )
    db.add(audit)
    
    # Atomic transition
    job.status = AlertEvaluationJobStatus.PENDING.value
    job.error_detail = None
    job.lease_until = None
    job.worker_id = None
    job.updated_at = datetime.now(timezone.utc)
    
    return job
