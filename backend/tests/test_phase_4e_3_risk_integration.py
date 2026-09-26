from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.models.alerts import AlertEvaluationJob
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState, RiskTriggerType
from app.models.work_order import WorkOrder
from app.services.risk_service import record_risk_transition_if_changed


@pytest.fixture
async def base_context(db_session):
    c1 = Company(id="c1_ev_r", name="C1")
    p1 = Plant(id="p1_ev_r", company_id="c1_ev_r", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev_r", company_id="c1_ev_r", name="P")
    mach = Machine(id="mach1_ev_r", company_id="c1_ev_r", plant_id="p1_ev_r", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()
    wo1 = WorkOrder(id="wo1_ev_r", company_id="c1_ev_r", plant_id="p1_ev_r", order_number="W1", status="PENDING", product_id="prod1_ev_r", machine_id="mach1_ev_r", quantity=100.0)
    db_session.add(wo1)
    await db_session.commit()
    return {"wo1": wo1}

@pytest.mark.asyncio
async def test_risk_service_integration(db_session, base_context):
    wo1 = base_context["wo1"]
    eval_time = datetime.now(timezone.utc)
    
    with patch('app.services.risk_service.fetch_current_risk') as mock_fetch:
        # Same state
        mock_fetch.return_value = RiskState.PENDING_EVALUATION
        res = await record_risk_transition_if_changed(
            db_session, wo1.id, wo1.company_id, RiskState.PENDING_EVALUATION, 
            next(iter(RiskTriggerType)), eval_time
        )
        assert res == RiskState.PENDING_EVALUATION
        jobs = (await db_session.execute(select(AlertEvaluationJob).where(AlertEvaluationJob.target_work_order_id == wo1.id))).scalars().all()
        assert len(jobs) == 0
        
        # Different state
        mock_fetch.return_value = RiskState.AT_RISK
        res = await record_risk_transition_if_changed(
            db_session, wo1.id, wo1.company_id, RiskState.PENDING_EVALUATION, 
            next(iter(RiskTriggerType)), eval_time
        )
        assert res == RiskState.AT_RISK
        jobs = (await db_session.execute(select(AlertEvaluationJob).where(AlertEvaluationJob.target_work_order_id == wo1.id))).scalars().all()
        assert len(jobs) == 1

