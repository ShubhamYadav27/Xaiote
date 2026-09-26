from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.incident import IncidentStatus
from app.models.user import User
from app.services.incident_service import (
    IncidentSecurityException,
    IncidentStateError,
    get_incident_detail,
    get_incidents,
    link_event_to_incident,
    resolve_incident,
    unlink_event_from_incident,
)

router = APIRouter()


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    plant_id: str
    machine_id: str | None
    title: str
    status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None


class PaginatedIncidentResponse(BaseModel):
    items: list[IncidentResponse]
    total: int


class LinkEventRequest(BaseModel):
    event_id: str
    reason: str | None = None


class UnlinkEventRequest(BaseModel):
    event_id: str
    reason: str


class ResolveIncidentRequest(BaseModel):
    reason: str | None = None


class RiskChangeResponse(BaseModel):
    work_order_id: str
    previous_state: str
    new_state: str


@router.get("", response_model=PaginatedIncidentResponse)
async def list_incidents(
    status: IncidentStatus | None = Query(None),
    plant_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    incidents, total = await get_incidents(
        db,
        current_company.id,
        status=status,
        plant_id=plant_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedIncidentResponse(items=incidents, total=total)


@router.get("/{id}")
async def get_incident(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    try:
        detail = await get_incident_detail(db, id, current_company.id)
    except IncidentSecurityException:
        raise HTTPException(status_code=404, detail="Incident not found")

    return detail


@router.post("/{id}/link-event")
async def link_event(
    id: str,
    request: LinkEventRequest,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
):
    try:
        await link_event_to_incident(
            db=db,
            incident_id=id,
            event_id=request.event_id,
            company_id=current_company.id,
            actor_id=current_user.id,
            reason=request.reason,
        )
        await db.commit()
    except IncidentSecurityException:
        raise HTTPException(status_code=404, detail="Incident or Event not found")

    return {"status": "success"}


@router.post("/{id}/unlink-event")
async def unlink_event(
    id: str,
    request: UnlinkEventRequest,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
):
    try:
        risk_changes = await unlink_event_from_incident(
            db=db,
            incident_id=id,
            event_id=request.event_id,
            company_id=current_company.id,
            actor_id=current_user.id,
            reason=request.reason,
        )
        await db.commit()
    except IncidentSecurityException:
        raise HTTPException(status_code=404, detail="Incident or Event not found")

    return {"status": "success", "risk_changes": risk_changes}


@router.post("/{id}/resolve")
async def resolve(
    id: str,
    request: ResolveIncidentRequest,
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
    current_user: User = Depends(get_current_user),
):
    try:
        _, risk_changes = await resolve_incident(
            db=db,
            incident_id=id,
            company_id=current_company.id,
            actor_id=current_user.id,
            reason=request.reason,
        )
        await db.commit()
    except IncidentSecurityException:
        raise HTTPException(status_code=404, detail="Incident not found")
    except IncidentStateError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "success", "risk_changes": risk_changes}
