from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.impact import ImpactStatus, ProductionOrderImpact
from app.models.risk import RiskState, WorkOrderRiskHistory
from app.models.work_order import WorkOrder
from app.services.risk_evaluator import InsufficientContextException
from app.services.risk_service import fetch_current_risk

router = APIRouter()


class RiskExplanationEvidence(BaseModel):
    impacts: list[str]
    due_date: datetime | None


class RiskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    work_order_id: str
    order_number: str
    risk_state: RiskState
    evaluation_time: datetime
    due_date: datetime | None
    work_order_status: str
    impact_summary: str
    explainable_risk_evidence: RiskExplanationEvidence


class RiskHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    work_order_id: str
    previous_state: RiskState
    new_state: RiskState
    trigger_type: str
    created_at: datetime


def generate_explanation(risk_state: RiskState) -> str:
    if risk_state == RiskState.ON_TRACK:
        return "Work Order is active, not overdue, and has no active production impact."
    elif risk_state == RiskState.PENDING_EVALUATION:
        return "Work Order has one or more potential production impacts awaiting confirmation."
    elif risk_state == RiskState.AT_RISK:
        return "Work Order has one or more confirmed production impacts and is not overdue."
    elif risk_state == RiskState.DELAYED:
        return "Work Order is active and its due-date deadline has passed, with no confirmed production impact."
    elif risk_state == RiskState.CRITICAL:
        return "Work Order is overdue and has one or more confirmed production impacts."
    elif risk_state == RiskState.RESOLVED:
        return "Work Order is completed."
    elif risk_state == RiskState.NOT_APPLICABLE:
        return "Work Order is cancelled."
    return "Unknown risk state."


@router.get("/work-orders/{id}/risk", response_model=RiskResponse)
async def get_work_order_risk(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(WorkOrder).where(
        and_(WorkOrder.id == id, WorkOrder.company_id == current_company.id)
    )
    result = await db.execute(stmt)
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    eval_time = datetime.now(timezone.utc)
    try:
        risk_state = await fetch_current_risk(db, wo.id, eval_time)
    except InsufficientContextException:
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": "MISSING_TIMEZONE_CONTEXT",
                    "message": "Risk Evaluation Unavailable - Missing Plant Timezone Context",
                }
            },
        )

    # Get evidence
    stmt_i = select(ProductionOrderImpact).where(
        and_(
            ProductionOrderImpact.work_order_id == wo.id,
            ProductionOrderImpact.status.in_(
                [ImpactStatus.POTENTIAL, ImpactStatus.CONFIRMED]
            ),
        )
    )
    res_i = await db.execute(stmt_i)
    impacts = res_i.scalars().all()

    return RiskResponse(
        work_order_id=wo.id,
        order_number=wo.order_number,
        risk_state=risk_state,
        evaluation_time=eval_time,
        due_date=wo.due_date,
        work_order_status=wo.status,
        impact_summary=generate_explanation(risk_state),
        explainable_risk_evidence=RiskExplanationEvidence(
            impacts=[i.id for i in impacts], due_date=wo.due_date
        ),
    )


@router.get("/risk/dashboard")
async def get_risk_dashboard(
    plant_id: str | None = Query(None),
    risk_state: RiskState | None = Query(None),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(WorkOrder).where(WorkOrder.company_id == current_company.id)
    if plant_id:
        stmt = stmt.where(WorkOrder.plant_id == plant_id)

    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    wos = result.scalars().all()

    eval_time = datetime.now(timezone.utc)

    dashboard_items = []
    for wo in wos:
        try:
            r_state = await fetch_current_risk(db, wo.id, eval_time)
        except InsufficientContextException:
            continue

        if risk_state and r_state != risk_state:
            continue

        dashboard_items.append(
            {
                "work_order_id": wo.id,
                "order_number": wo.order_number,
                "risk_state": r_state,
                "due_date": wo.due_date,
            }
        )

    return {"items": dashboard_items}


@router.get("/work-orders/{id}/risk/history", response_model=list[RiskHistoryResponse])
async def get_work_order_risk_history(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(WorkOrder).where(
        and_(WorkOrder.id == id, WorkOrder.company_id == current_company.id)
    )
    result = await db.execute(stmt)
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    stmt_h = (
        select(WorkOrderRiskHistory)
        .where(
            and_(
                WorkOrderRiskHistory.work_order_id == id,
                WorkOrderRiskHistory.company_id == current_company.id,
            )
        )
        .order_by(WorkOrderRiskHistory.created_at.asc())
    )

    res_h = await db.execute(stmt_h)
    history = res_h.scalars().all()

    return history
