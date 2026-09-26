import asyncio

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import (
    AlertEvaluationJob,
    AlertHistory,
    AlertInstance,
    AlertPolicy,
    AlertRule,
)
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState, RiskTriggerType, WorkOrderRiskHistory
from app.models.work_order import WorkOrder
from app.services.alert_evaluator import process_alert_job
from app.workers.alert_worker import run_alert_worker


@pytest.fixture
async def base_context(db_session: AsyncSession):
    c1 = Company(id="c1_ev_ext", name="C1")
    p1 = Plant(id="p1_ev_ext", company_id="c1_ev_ext", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev_ext", company_id="c1_ev_ext", name="P")
    mach = Machine(id="mach1_ev_ext", company_id="c1_ev_ext", plant_id="p1_ev_ext", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()
    wo1 = WorkOrder(id="wo1_ev_ext", company_id="c1_ev_ext", plant_id="p1_ev_ext", order_number="W1", status="PENDING", product_id="prod1_ev_ext", machine_id="mach1_ev_ext", quantity=100.0)
    pol = AlertPolicy(id="pol1_ev", company_id="c1_ev_ext", version=1, name="Pol1")
    rules = [
        AlertRule(id="rule1_ev_risk", company_id="c1_ev_ext", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.AT_RISK.value, trigger_condition={}, clear_condition={}),
        AlertRule(id="rule1_ev_crit", company_id="c1_ev_ext", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.CRITICAL.value, trigger_condition={}, clear_condition={})
    ]
    db_session.add(wo1)
    db_session.add(pol)
    db_session.add_all(rules)
    await db_session.commit()
    return {"wo1": wo1}

@pytest.mark.asyncio
async def test_t5_concurrent_evaluation(db_session, base_context):
    wo1 = base_context["wo1"]
    
    rh1 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.ON_TRACK, new_state=RiskState.AT_RISK,
        trigger_type=next(iter(RiskTriggerType))
    )
    db_session.add(rh1)
    await db_session.commit()

    # Create two duplicate jobs manually
    job1 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    job2 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add_all([job1, job2])
    await db_session.commit()
    
    # Run them concurrently via run_alert_worker
    await asyncio.gather(
        run_alert_worker(max_iterations=1),
        run_alert_worker(max_iterations=1)
    )
    
    alerts = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalars().all()
    assert len(alerts) == 1
    
    hist = (await db_session.execute(select(AlertHistory).where(AlertHistory.alert_instance_id == alerts[0].id))).scalars().all()
    assert len(hist) == 1

@pytest.mark.asyncio
async def test_t7_tenant_isolation(db_session, base_context):
    wo1 = base_context["wo1"]
    
    c2 = Company(id="c2_iso", name="C2")
    p2 = Plant(id="p2_iso", company_id="c2_iso", name="P2", timezone="UTC")
    db_session.add_all([c2, p2])
    await db_session.commit()
    
    # Try to evaluate job from company A using company B's identity
    job = AlertEvaluationJob(company_id=c2.id, plant_id=p2.id, target_work_order_id=wo1.id)
    db_session.add(job)
    await db_session.commit()
    
    await process_alert_job(db_session, job)
    await db_session.commit()
    
    # Since WO belongs to C1 but job is C2, risk_history query should fail or Alert should be isolated
    alerts = (await db_session.execute(select(AlertInstance).where(AlertInstance.company_id == c2.id))).scalars().all()
    assert len(alerts) == 0

@pytest.mark.asyncio
async def test_t18_provenance_full_cycle(db_session, base_context):
    wo1 = base_context["wo1"]
    
    # CREATE AT_RISK
    rh1 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.ON_TRACK, new_state=RiskState.AT_RISK,
        trigger_type=next(iter(RiskTriggerType))
    )
    job1 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add_all([rh1, job1])
    await db_session.commit()
    await process_alert_job(db_session, job1)
    await db_session.commit()
    
    alert = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalar_one()
    assert alert.originating_policy_version == 1
    assert alert.current_policy_version == 1
    
    # Introduce v2 Policy and Rule for CRITICAL
    pol2 = AlertPolicy(id="pol1_ev", company_id=wo1.company_id, version=2, name="Pol1 v2")
    rule2 = AlertRule(id="rule1_ev_crit", company_id=wo1.company_id, version=2, policy_id="pol1_ev", policy_version=2,
                      alert_family="PRODUCTION_RISK", severity=RiskState.CRITICAL.value, trigger_condition={}, clear_condition={})
    db_session.add_all([pol2, rule2])
    await db_session.commit()
    
    # ESCALATE to CRITICAL
    rh2 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.AT_RISK, new_state=RiskState.CRITICAL,
        trigger_type=next(iter(RiskTriggerType))
    )
    job2 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add_all([rh2, job2])
    await db_session.commit()
    await process_alert_job(db_session, job2)
    await db_session.commit()
    
    await db_session.refresh(alert)
    assert alert.originating_policy_version == 1
    assert alert.current_policy_version == 2
    
    hist = (await db_session.execute(select(AlertHistory).where(AlertHistory.alert_instance_id == alert.id).order_by(AlertHistory.timestamp.desc()))).scalars().first()
    assert hist.action == "ESCALATE"
    assert hist.previous_policy_version == 1
    assert hist.new_policy_version == 2

