import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.impact import (
    ImpactDecisionHistory,
    ImpactProvenance,
    ImpactStatus,
    ProductionOrderImpact,
)
from app.models.manufacturing_event import ManufacturingEvent
from app.models.resolution import EntityResolutionResult
from app.models.risk import RiskTriggerType
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.services.risk_service import (
    fetch_current_risk,
    record_risk_transition_if_changed,
)

logger = logging.getLogger(__name__)


class SecurityException(Exception):
    pass


async def evaluate_impacts_for_event(
    db: AsyncSession, event_id: str, current_company_id: str
):
    stmt = (
        select(ManufacturingEvent, EntityResolutionResult)
        .join(
            EntityResolutionResult,
            ManufacturingEvent.candidate_id == EntityResolutionResult.candidate_id,
        )
        .where(ManufacturingEvent.id == event_id)
    )
    result = await db.execute(stmt)
    row = result.first()
    if not row:
        return

    event, resolution = row

    if event.company_id != current_company_id:
        raise SecurityException("Cross-tenant event impact evaluation denied.")

    if resolution.work_order_id and resolution.work_order_state == "RESOLVED":
        wo_stmt = select(WorkOrder).where(WorkOrder.id == resolution.work_order_id)
        wo_result = await db.execute(wo_stmt)
        wo = wo_result.scalar_one_or_none()

        if wo:
            if wo.company_id != current_company_id:
                raise SecurityException(
                    "Cross-tenant work order impact mapping denied."
                )

            impact_plant_id = None
            if event.plant_id is not None:
                if event.plant_id == wo.plant_id:
                    impact_plant_id = event.plant_id
            else:
                impact_plant_id = wo.plant_id

            if impact_plant_id:
                await upsert_impact(
                    db,
                    company_id=current_company_id,
                    plant_id=impact_plant_id,
                    event_id=event.id,
                    work_order_id=wo.id,
                    status=ImpactStatus.CONFIRMED,
                    provenance=ImpactProvenance.EXPLICIT_WORK_ORDER_RESOLUTION,
                )

    elif resolution.machine_id and resolution.machine_state == "RESOLVED":
        wo_stmt = select(WorkOrder).where(
            and_(
                WorkOrder.company_id == current_company_id,
                WorkOrder.machine_id == resolution.machine_id,
                WorkOrder.status.in_(
                    [WorkOrderStatus.IN_PROGRESS.value, WorkOrderStatus.PLANNED.value]
                ),
            )
        )
        wo_result = await db.execute(wo_stmt)
        wos = wo_result.scalars().all()

        for wo in wos:
            impact_plant_id = None
            if event.plant_id is not None:
                if event.plant_id == wo.plant_id:
                    impact_plant_id = event.plant_id
            else:
                impact_plant_id = wo.plant_id

            if impact_plant_id:
                await upsert_impact(
                    db,
                    company_id=current_company_id,
                    plant_id=impact_plant_id,
                    event_id=event.id,
                    work_order_id=wo.id,
                    status=ImpactStatus.POTENTIAL,
                    provenance=ImpactProvenance.MACHINE_CONTEXT_DERIVED,
                )


async def upsert_impact(
    db: AsyncSession,
    company_id,
    plant_id,
    event_id,
    work_order_id,
    status,
    provenance,
    actor_id=None,
    reason=None,
):
    now = datetime.now(timezone.utc)
    prev_risk = await fetch_current_risk(db, work_order_id, now)
    stmt = select(ProductionOrderImpact).where(
        and_(
            ProductionOrderImpact.event_id == event_id,
            ProductionOrderImpact.work_order_id == work_order_id,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.status == status and existing.provenance == provenance:
            trigger = RiskTriggerType.IMPACT_GENERATED
            if status == ImpactStatus.CONFIRMED:
                trigger = RiskTriggerType.IMPACT_CONFIRMED
            elif status == ImpactStatus.REJECTED:
                trigger = RiskTriggerType.IMPACT_REJECTED
            await db.flush()
            await record_risk_transition_if_changed(
                db, work_order_id, company_id, prev_risk, trigger, now
            )
            return existing
        else:
            previous_status = (
                existing.status.value
                if isinstance(existing.status, ImpactStatus)
                else existing.status
            )
            existing.status = status
            existing.provenance = provenance

            history = ImpactDecisionHistory(
                impact_id=existing.id,
                actor_id=actor_id,
                previous_status=previous_status,
                new_status=status.value if isinstance(status, ImpactStatus) else status,
                provenance=(
                    provenance.value
                    if isinstance(provenance, ImpactProvenance)
                    else provenance
                ),
                reason=reason,
            )
            db.add(history)
            trigger = RiskTriggerType.IMPACT_GENERATED
            if status == ImpactStatus.CONFIRMED:
                trigger = RiskTriggerType.IMPACT_CONFIRMED
            elif status == ImpactStatus.REJECTED:
                trigger = RiskTriggerType.IMPACT_REJECTED
            await db.flush()
            await record_risk_transition_if_changed(
                db, work_order_id, company_id, prev_risk, trigger, now
            )
            return existing
    else:
        new_id = str(uuid.uuid4())
        stmt_ins = (
            insert(ProductionOrderImpact)
            .values(
                id=new_id,
                company_id=company_id,
                plant_id=plant_id,
                event_id=event_id,
                work_order_id=work_order_id,
                status=status.value if isinstance(status, ImpactStatus) else status,
                provenance=(
                    provenance.value
                    if isinstance(provenance, ImpactProvenance)
                    else provenance
                ),
            )
            .on_conflict_do_nothing(index_elements=["event_id", "work_order_id"])
            .returning(ProductionOrderImpact.id)
        )

        result_ins = await db.execute(stmt_ins)
        inserted_id = result_ins.scalar_one_or_none()

        if inserted_id:
            history = ImpactDecisionHistory(
                impact_id=inserted_id,
                actor_id=actor_id,
                previous_status=None,
                new_status=status.value if isinstance(status, ImpactStatus) else status,
                provenance=(
                    provenance.value
                    if isinstance(provenance, ImpactProvenance)
                    else provenance
                ),
                reason=reason,
            )
            db.add(history)
            stmt2 = select(ProductionOrderImpact).where(
                ProductionOrderImpact.id == inserted_id
            )
            res2 = await db.execute(stmt2)
            trigger = RiskTriggerType.IMPACT_GENERATED
            if status == ImpactStatus.CONFIRMED:
                trigger = RiskTriggerType.IMPACT_CONFIRMED
            elif status == ImpactStatus.REJECTED:
                trigger = RiskTriggerType.IMPACT_REJECTED
            await db.flush()
            await record_risk_transition_if_changed(
                db, work_order_id, company_id, prev_risk, trigger, now
            )
            return res2.scalar_one()
        else:
            return await upsert_impact(
                db,
                company_id,
                plant_id,
                event_id,
                work_order_id,
                status,
                provenance,
                actor_id,
                reason,
            )
