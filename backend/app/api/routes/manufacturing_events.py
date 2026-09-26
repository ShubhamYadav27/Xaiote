from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.company import Company
from app.models.manufacturing_event import (
    EventStatus,
    ManufacturingEvent,
    ManufacturingEventRevision,
    ProvenanceType,
)
from app.models.resolution import EntityResolutionResult
from app.models.user import User

router = APIRouter()


class ManufacturingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    company_id: str
    event_status: EventStatus
    description: str | None = None
    canonical_event_type: str | None = None
    canonical_event_type_provenance: ProvenanceType | None = None
    severity: str | None = None
    severity_provenance: ProvenanceType | None = None
    root_cause: str | None = None
    root_cause_provenance: ProvenanceType | None = None
    reported_downtime_minutes: int | None = None
    quantity_affected: int | None = None
    event_time_reference: str | None = None
    canonical_occurrence_timestamp: datetime | None = None


class RevisionRequest(BaseModel):
    changes: dict[str, Any]
    reason: str


class RevisionFieldChange(BaseModel):
    old_value: Any | None
    new_value: Any | None
    previous_provenance: ProvenanceType | None
    new_provenance: ProvenanceType | None


class ManufacturingEventRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: str
    revision_timestamp: datetime
    changed_fields: dict[str, RevisionFieldChange]
    reason: str


class EventWithRevisionsResponse(BaseModel):
    base_event: ManufacturingEventResponse
    current_state: ManufacturingEventResponse
    revisions: list[ManufacturingEventRevisionResponse]


VALID_REVISION_FIELDS = {
    "canonical_event_type",
    "severity",
    "root_cause",
    "description",
    "reported_downtime_minutes",
    "quantity_affected",
    "event_time_reference",
    "canonical_occurrence_timestamp",
}


def apply_revisions(
    event: ManufacturingEvent, revisions: list[ManufacturingEventRevision]
) -> ManufacturingEvent:
    # Create a transient copy for current_state
    current = ManufacturingEvent(
        id=event.id,
        company_id=event.company_id,
        event_status=event.event_status,
        description=event.description,
        canonical_event_type=event.canonical_event_type,
        canonical_event_type_provenance=event.canonical_event_type_provenance,
        severity=event.severity,
        severity_provenance=event.severity_provenance,
        root_cause=event.root_cause,
        root_cause_provenance=event.root_cause_provenance,
        reported_downtime_minutes=event.reported_downtime_minutes,
        quantity_affected=event.quantity_affected,
        event_time_reference=event.event_time_reference,
        canonical_occurrence_timestamp=event.canonical_occurrence_timestamp,
    )
    for rev in revisions:
        for field, change_data in rev.changed_fields.items():
            if hasattr(current, field):
                setattr(current, field, change_data["new_value"])
            # Apply provenance if this field has one
            prov_field = f"{field}_provenance"
            if hasattr(current, prov_field) and "new_provenance" in change_data:
                # Convert string back to enum if necessary
                new_prov_str = change_data["new_provenance"]
                if new_prov_str:
                    setattr(current, prov_field, ProvenanceType(new_prov_str))
    return current


@router.get("/")
async def get_events(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    event_type: str | None = Query(None),
    plant_id: str | None = Query(None),
    machine_id: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(ManufacturingEvent).where(
        ManufacturingEvent.company_id == current_company.id
    )
    if status:
        stmt = stmt.where(ManufacturingEvent.event_status == status)  # type: ignore
    if event_type:
        stmt = stmt.where(ManufacturingEvent.canonical_event_type == event_type)
    if plant_id:
        stmt = stmt.where(ManufacturingEvent.plant_id == plant_id)
    if machine_id:
        stmt = stmt.join(
            EntityResolutionResult,
            ManufacturingEvent.candidate_id == EntityResolutionResult.candidate_id,
        ).where(EntityResolutionResult.machine_id == machine_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = (
        stmt.order_by(ManufacturingEvent.created_at.desc()).offset(offset).limit(limit)
    )
    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "data": {
            "items": [
                ManufacturingEventResponse.model_validate(e).model_dump()
                for e in events
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/{event_id}", response_model=dict)
async def get_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(ManufacturingEvent).where(
        ManufacturingEvent.id == event_id,
        ManufacturingEvent.company_id == current_company.id,
    )
    result = await db.execute(stmt)
    event = result.scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    rev_stmt = (
        select(ManufacturingEventRevision)
        .where(ManufacturingEventRevision.event_id == event.id)
        .order_by(ManufacturingEventRevision.revision_timestamp.asc())
    )
    revisions = (await db.execute(rev_stmt)).scalars().all()

    current_state = apply_revisions(event, revisions)  # type: ignore

    # Fetch Lineage
    resolution = None
    extraction = None
    transcript = None
    attachment = None
    message = None

    if event.candidate_id:
        res_stmt = select(EntityResolutionResult).where(
            EntityResolutionResult.candidate_id == event.candidate_id
        )
        resolution = (await db.execute(res_stmt)).scalars().first()

        ext_stmt = select(ExtractedEventCandidate).where(
            ExtractedEventCandidate.id == event.candidate_id
        )
        extraction = (await db.execute(ext_stmt)).scalars().first()

        if extraction and extraction.transcript_id:
            trx_stmt = select(CommunicationTranscript).where(
                CommunicationTranscript.id == extraction.transcript_id
            )
            transcript = (await db.execute(trx_stmt)).scalars().first()

            if transcript and transcript.attachment_id:
                att_stmt = select(CommunicationAttachment).where(
                    CommunicationAttachment.id == transcript.attachment_id
                )
                attachment = (await db.execute(att_stmt)).scalars().first()

                if attachment and attachment.message_id:
                    msg_stmt = select(CommunicationMessage).where(
                        CommunicationMessage.id == attachment.message_id
                    )
                    message = (await db.execute(msg_stmt)).scalars().first()

    # Serialization helper
    def to_dict(obj):
        if not obj:
            return None
        # Convert SQLAlchemy object to dict safely
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    # Clean up message payload for safety
    message_dict = to_dict(message)
    if message_dict:
        message_dict.pop(
            "sender_identity", None
        )  # Or keep it if permitted, CTO said "where permitted". Let's keep it but mask it? Just pass it, internal UI.

    return {
        "data": {
            "base_event": ManufacturingEventResponse.model_validate(event).model_dump(),
            "current_state": ManufacturingEventResponse.model_validate(
                current_state
            ).model_dump(),
            "revisions": [
                ManufacturingEventRevisionResponse.model_validate(r).model_dump()
                for r in revisions
            ],
            "evidence": {
                "communication_message": message_dict,
                "attachments": [to_dict(attachment)] if attachment else [],
                "transcript": to_dict(transcript),
                "extraction": to_dict(extraction),
                "entity_resolution": to_dict(resolution),
            },
        }
    }


@router.post("/{event_id}/revisions", response_model=dict)
async def create_revision(
    event_id: str,
    req: RevisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not req.changes:
        raise HTTPException(status_code=400, detail="Changes cannot be empty")
    if not req.reason or not req.reason.strip():
        raise HTTPException(status_code=400, detail="Reason is required")

    for k in req.changes:
        if k not in VALID_REVISION_FIELDS:
            raise HTTPException(
                status_code=400, detail=f"Unknown or non-revisable field: {k}"
            )

    # Fetch event securely scoped to company
    stmt = select(ManufacturingEvent).where(
        ManufacturingEvent.id == event_id,
        ManufacturingEvent.company_id == current_user.company_id,
    )
    event = (await db.execute(stmt)).scalars().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Fetch existing revisions to compute current effective state
    rev_stmt = (
        select(ManufacturingEventRevision)
        .where(ManufacturingEventRevision.event_id == event.id)
        .order_by(ManufacturingEventRevision.revision_timestamp.asc())
    )
    existing_revisions = (await db.execute(rev_stmt)).scalars().all()

    current_state = apply_revisions(event, existing_revisions)  # type: ignore

    changed_fields_payload = {}
    for field, new_val in req.changes.items():
        old_val = getattr(current_state, field, None)
        if isinstance(old_val, datetime):
            old_val = old_val.isoformat()  # json compat

        prov_field = f"{field}_provenance"
        has_prov = hasattr(current_state, prov_field)

        old_prov = getattr(current_state, prov_field, None) if has_prov else None
        new_prov = ProvenanceType.HUMAN_CONFIRMED.value if has_prov else None

        old_prov_val = old_prov.value if old_prov else None

        changed_fields_payload[field] = {
            "old_value": old_val,
            "new_value": new_val,
            "previous_provenance": old_prov_val,
            "new_provenance": new_prov,
        }

    new_rev = ManufacturingEventRevision(
        event_id=event.id,
        actor_id=current_user.id,
        changed_fields=changed_fields_payload,
        reason=req.reason,
    )
    db.add(new_rev)
    await db.commit()

    return {
        "data": ManufacturingEventRevisionResponse.model_validate(new_rev).model_dump()
    }


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
