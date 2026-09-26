from app.models.impact import ImpactProvenance, ImpactStatus, ProductionOrderImpact
from app.models.work_order import WorkOrder
from app.services.impact_generator import upsert_impact


class ImpactDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    event_id: str
    work_order_id: str
    status: ImpactStatus
    provenance: ImpactProvenance
    created_at: datetime
    updated_at: datetime


class CreateImpactRequest(BaseModel):
    work_order_id: str
    reason: str


@router.get("/{event_id}/impacts", response_model=list[ImpactDetailResponse])
async def get_event_impacts(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(ProductionOrderImpact).where(
        and_(
            ProductionOrderImpact.event_id == event_id,
            ProductionOrderImpact.company_id == current_company.id,
        )
    )
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/{event_id}/impacts", response_model=ImpactDetailResponse)
async def create_event_impact(
    event_id: str,
    request: CreateImpactRequest,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
):
    event_stmt = select(ManufacturingEvent).where(
        and_(
            ManufacturingEvent.id == event_id,
            ManufacturingEvent.company_id == current_company.id,
        )
    )
    event_res = await db.execute(event_stmt)
    event = event_res.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    wo_stmt = select(WorkOrder).where(
        and_(
            WorkOrder.id == request.work_order_id,
            WorkOrder.company_id == current_company.id,
        )
    )
    wo_res = await db.execute(wo_stmt)
    wo = wo_res.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work Order not found")

    impact_plant_id = None
    if event.plant_id is not None:
        if event.plant_id != wo.plant_id:
            raise HTTPException(status_code=400, detail="Plant conflict")
        else:
            impact_plant_id = event.plant_id
    else:
        impact_plant_id = wo.plant_id

    updated = await upsert_impact(
        db,
        company_id=current_company.id,
        plant_id=impact_plant_id,
        event_id=event.id,
        work_order_id=wo.id,
        status=ImpactStatus.CONFIRMED,
        provenance=ImpactProvenance.HUMAN_CONFIRMED,
        actor_id=current_user.id,
        reason=request.reason,
    )
    await db.commit()
    return updated
