from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.impact import (
    ImpactProvenance,
    ImpactStatus,
    ProductionOrderImpact,
)
from app.models.user import User
from app.services.impact_generator import upsert_impact

router = APIRouter()


class ImpactDecisionRequest(BaseModel):
    decision: str  # CONFIRM or REJECT
    reason: str


class ImpactDecisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    impact_id: str
    actor_id: str | None
    previous_status: str | None
    new_status: str
    provenance: str
    reason: str | None
    created_at: datetime


class ImpactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str
    work_order_id: str
    status: ImpactStatus
    provenance: ImpactProvenance
    created_at: datetime
    updated_at: datetime


@router.post("/{impact_id}/decisions", response_model=ImpactResponse)
async def make_decision(
    impact_id: str,
    request: ImpactDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ProductionOrderImpact).where(
        and_(
            ProductionOrderImpact.id == impact_id,
            ProductionOrderImpact.company_id == current_company.id,
        )
    )
    result = await db.execute(stmt)
    impact = result.scalar_one_or_none()

    if not impact:
        raise HTTPException(status_code=404, detail="Impact not found")

    if impact.status != ImpactStatus.POTENTIAL:
        raise HTTPException(
            status_code=400, detail="Only POTENTIAL impacts can be decided"
        )

    if request.decision == "CONFIRM":
        new_status = ImpactStatus.CONFIRMED
        new_provenance = ImpactProvenance.HUMAN_CONFIRMED
    elif request.decision == "REJECT":
        new_status = ImpactStatus.REJECTED
        new_provenance = ImpactProvenance.HUMAN_REJECTED
    else:
        raise HTTPException(status_code=400, detail="Invalid decision")

    updated = await upsert_impact(
        db,
        company_id=current_company.id,
        plant_id=impact.plant_id,
        event_id=impact.event_id,
        work_order_id=impact.work_order_id,
        status=new_status,
        provenance=new_provenance,
        actor_id=current_user.id,
        reason=request.reason,
    )
    await db.commit()
    return updated
