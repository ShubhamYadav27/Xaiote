import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.work_order import WorkOrder


@pytest.fixture
async def base_context(db_session: AsyncSession):
    c1 = Company(id="c1_ev_w", name="C1")
    p1 = Plant(id="p1_ev_w", company_id="c1_ev_w", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev_w", company_id="c1_ev_w", name="P")
    mach = Machine(id="mach1_ev_w", company_id="c1_ev_w", plant_id="p1_ev_w", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev_w", machine_id="mach1_ev_w", quantity=100.0, id="wo1_ev_w", company_id="c1_ev_w", plant_id="p1_ev_w", order_number="W1", status="PENDING")
    db_session.add(wo1)
    await db_session.commit()
    return {"wo1": wo1}
from datetime import datetime, timedelta, timezone

import pytest

from app.models.alerts import AlertEvaluationJob, AlertEvaluationJobStatus
from app.workers.alert_worker import run_alert_worker


@pytest.mark.asyncio
async def test_t10_worker_crash_recovery(db_session, base_context):
    wo1 = base_context["wo1"]
    job = AlertEvaluationJob(
        company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id,
        status=AlertEvaluationJobStatus.PROCESSING.value,
        lease_until=datetime.now(timezone.utc) - timedelta(minutes=5)
    )
    db_session.add(job)
    await db_session.commit()
    
    # Run worker for 1 iteration
    await run_alert_worker(max_iterations=1)
    
    # Assert processed
    await db_session.refresh(job)
    # The evaluation logic will run and since there's no risk_history for it, it completes immediately.
    assert job.status == AlertEvaluationJobStatus.COMPLETED.value

