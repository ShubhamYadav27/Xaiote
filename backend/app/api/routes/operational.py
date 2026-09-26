from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.schemas.operational import (
    OperationalContextEnvelope,
    TimelineResponse,
)
from app.services.operational_context import (
    get_incident_context,
    get_work_order_context,
)
from app.services.timeline import get_timeline

router = APIRouter()


@router.get(
    "/operational-context/incidents/{incident_id}",
    response_model=OperationalContextEnvelope,
)
async def read_incident_context(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    ctx = await get_incident_context(db, company.id, incident_id)
    return OperationalContextEnvelope(data=ctx)


@router.get(
    "/operational-context/work-orders/{work_order_id}",
    response_model=OperationalContextEnvelope,
)
async def read_work_order_context(
    work_order_id: str,
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    ctx = await get_work_order_context(db, company.id, work_order_id)
    return OperationalContextEnvelope(data=ctx)


@router.get("/timeline", response_model=OperationalContextEnvelope)
async def read_timeline(
    entity_type: str = Query(..., description="incident or work_order"),
    entity_id: str = Query(...),
    chronology: str = Query("operational", description="operational or audit"),
    limit: int = Query(50, ge=1, le=100),
    cursor: str | None = Query(None, description="ISO8601time|source_id"),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
):
    cursor_time = None
    cursor_id = None
    if cursor:
        try:
            parts = cursor.split("|", 1)
            cursor_time = datetime.fromisoformat(parts[0])
            cursor_id = parts[1]
        except ValueError:
            pass  # Invalid cursor handled safely

    entries, next_cursor = await get_timeline(
        db=db,
        company_id=company.id,
        entity_type=entity_type,
        entity_id=entity_id,
        chronology=chronology,
        limit=limit,
        cursor_time=cursor_time,
        cursor_id=cursor_id,
    )

    response_data = TimelineResponse(
        data=entries,
        next_cursor=next_cursor,
        context_generated_at=datetime.now(timezone.utc),
    )
    return OperationalContextEnvelope(data=response_data)
