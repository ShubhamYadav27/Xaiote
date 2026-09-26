import pytest

from app.models.alerts import AlertEvaluationJob, AlertEvaluationJobStatus
from app.services.alert_evaluator import process_alert_job


@pytest.mark.asyncio
async def test_t19_t20_t21_incident_boundary(db_session):
    # Job with target_incident_id should be rejected
    job = AlertEvaluationJob(company_id="c1", target_incident_id="inc1")
    db_session.add(job)
    # The evaluation should fail
    await process_alert_job(db_session, job)
    
    assert job.status == AlertEvaluationJobStatus.FAILED.value
    assert "Incident-targeted alerts are explicitly REJECTED" in job.error_detail
