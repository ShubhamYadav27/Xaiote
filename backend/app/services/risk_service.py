from datetime import datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import AlertEvaluationJob
from app.models.impact import ImpactStatus, ProductionOrderImpact
from app.models.risk import RiskState, RiskTriggerType, WorkOrderRiskHistory
from app.models.work_order import WorkOrder
from app.services.risk_evaluator import evaluate


async def fetch_current_risk(
    db: AsyncSession, work_order_id: str, evaluation_time: datetime
) -> RiskState:
    stmt = select(WorkOrder).where(WorkOrder.id == work_order_id)
    result = await db.execute(stmt)
    wo = result.scalar_one_or_none()
    if not wo:
        return RiskState.ON_TRACK  # Fallback, though shouldn't happen

    stmt_i = select(ProductionOrderImpact).where(
        and_(
            ProductionOrderImpact.work_order_id == work_order_id,
            ProductionOrderImpact.status.in_(
                [ImpactStatus.POTENTIAL, ImpactStatus.CONFIRMED]
            ),
        )
    )
    res_i = await db.execute(stmt_i)
    impacts = res_i.scalars().all()

    # We assume 'UTC' or similar for plant timezone for now unless wo.plant_id can give us real tz.
    # We will pass a dummy timezone "UTC" just to satisfy the API if it's strictly required,
    # or rely on the evaluator to throw.
    return evaluate(wo, list(impacts), evaluation_time, "UTC")



async def record_risk_transition_if_changed(
    db: AsyncSession,
    work_order_id: str,
    company_id: str,
    previous_state: RiskState,
    trigger_type: RiskTriggerType,
    evaluation_time: datetime,
):
    new_state = await fetch_current_risk(db, work_order_id, evaluation_time)
    if previous_state != new_state:
        history = WorkOrderRiskHistory(
            work_order_id=work_order_id,
            company_id=company_id,
            previous_state=previous_state,
            new_state=new_state,
            trigger_type=trigger_type,
            created_at=evaluation_time,
        )
        db.add(history)
        
        # Determine plant_id
        wo_stmt = select(WorkOrder.plant_id).where(WorkOrder.id == work_order_id)
        plant_id = (await db.execute(wo_stmt)).scalar_one_or_none()
        
        job = AlertEvaluationJob(
            company_id=company_id,
            plant_id=plant_id,
            target_work_order_id=work_order_id
        )
        db.add(job)
    return new_state

