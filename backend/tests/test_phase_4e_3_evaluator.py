
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import (
    AlertEvaluationJob,
    AlertEvaluationJobStatus,
    AlertEvidenceLink,
    AlertInstance,
    AlertPolicy,
    AlertRule,
    AlertStatus,
)
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState, RiskTriggerType, WorkOrderRiskHistory
from app.models.work_order import WorkOrder
from app.services.alert_evaluator import process_alert_job


@pytest.fixture
async def base_context(db_session: AsyncSession):
    c1 = Company(id="c1_ev", name="C1")
    p1 = Plant(id="p1_ev", company_id="c1_ev", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev", company_id="c1_ev", name="P")
    mach = Machine(id="mach1_ev", company_id="c1_ev", plant_id="p1_ev", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev", machine_id="mach1_ev", quantity=100.0, id="wo1_ev", company_id="c1_ev", plant_id="p1_ev", order_number="W1", status="PENDING")
    db_session.add(wo1)
    
    pol = AlertPolicy(id="pol1_ev", company_id="c1_ev", version=1, name="Pol1")
    rules = [
        AlertRule(id="rule1_ev_risk", company_id="c1_ev", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.AT_RISK.value, trigger_condition={}, clear_condition={}),
        AlertRule(id="rule1_ev_delay", company_id="c1_ev", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.DELAYED.value, trigger_condition={}, clear_condition={}),
        AlertRule(id="rule1_ev_crit", company_id="c1_ev", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.CRITICAL.value, trigger_condition={}, clear_condition={})
    ]
    db_session.add(pol)
    db_session.add_all(rules)
    await db_session.commit()
    
    return {"wo1": wo1, "pol": pol, "rules": rules, "c1": c1}

@pytest.mark.asyncio
async def test_t1_deterministic_alert_creation(db_session, base_context):
    wo1 = base_context["wo1"]
    
    # 1. NONE -> AT_RISK
    rh = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.ON_TRACK, new_state=RiskState.AT_RISK,
        trigger_type=next(iter(RiskTriggerType))
    )
    db_session.add(rh)
    await db_session.commit()
    
    job = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add(job)
    await db_session.commit()
    
    await process_alert_job(db_session, job)
    await db_session.commit()
    
    assert job.status == AlertEvaluationJobStatus.COMPLETED.value
    
    alert = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalar_one()
    assert alert.status == AlertStatus.ACTIVE.value
    assert alert.severity == RiskState.AT_RISK.value
    
    ev = (await db_session.execute(select(AlertEvidenceLink).where(AlertEvidenceLink.alert_instance_id == alert.id))).scalar_one()
    assert ev.evidence_risk_history_id == rh.id

@pytest.mark.asyncio
async def test_t2_deduplication(db_session, base_context):
    wo1 = base_context["wo1"]
    
    # Run creation twice exactly
    rh1 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.ON_TRACK, new_state=RiskState.AT_RISK,
        trigger_type=next(iter(RiskTriggerType))
    )
    db_session.add(rh1)
    await db_session.commit()
    
    job1 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add(job1)
    await db_session.commit()
    await process_alert_job(db_session, job1)
    await db_session.commit()
    
    # 2nd run
    job2 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add(job2)
    await db_session.commit()
    await process_alert_job(db_session, job2)
    await db_session.commit()
    
    assert job2.status == AlertEvaluationJobStatus.COMPLETED.value
    alerts = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalars().all()
    assert len(alerts) == 1

@pytest.mark.asyncio
async def test_t3_escalation(db_session, base_context):
    wo1 = base_context["wo1"]
    
    # AT_RISK
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
    
    alert = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalar_one()
    assert alert.severity == RiskState.CRITICAL.value
    assert alert.version == 2

@pytest.mark.asyncio
async def test_t4_automatic_clear(db_session, base_context):
    wo1 = base_context["wo1"]
    
    # CRITICAL
    rh1 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.ON_TRACK, new_state=RiskState.CRITICAL,
        trigger_type=next(iter(RiskTriggerType))
    )
    job1 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add_all([rh1, job1])
    await db_session.commit()
    await process_alert_job(db_session, job1)
    await db_session.commit()
    
    # Clear to ON_TRACK
    rh2 = WorkOrderRiskHistory(
        work_order_id=wo1.id, company_id=wo1.company_id,
        previous_state=RiskState.CRITICAL, new_state=RiskState.ON_TRACK,
        trigger_type=next(iter(RiskTriggerType))
    )
    job2 = AlertEvaluationJob(company_id=wo1.company_id, plant_id=wo1.plant_id, target_work_order_id=wo1.id)
    db_session.add_all([rh2, job2])
    await db_session.commit()
    await process_alert_job(db_session, job2)
    await db_session.commit()
    
    alert = (await db_session.execute(select(AlertInstance).where(AlertInstance.target_work_order_id == wo1.id))).scalar_one()
    assert alert.status == AlertStatus.RESOLVED.value
