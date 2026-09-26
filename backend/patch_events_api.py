with open("app/api/routes/manufacturing_events.py", "r") as f:
    content = f.read()

# We need to import Query, func
content = content.replace(
    "from fastapi import APIRouter, Depends, HTTPException",
    "from fastapi import APIRouter, Depends, HTTPException, Query\nfrom sqlalchemy import func",
)

# And import models for lineage
content = content.replace(
    "from app.models.user import User",
    "from app.models.user import User\nfrom app.models.resolution import EntityResolutionResult\nfrom app.models.communication import ExtractedEventCandidate, CommunicationTranscript, CommunicationAttachment, CommunicationMessage",
)

# Replace get_events
old_get_events = """@router.get("/")
async def get_events(
    db: AsyncSession = Depends(get_db),
    current_company: Company = Depends(get_current_company),
):
    stmt = select(ManufacturingEvent).where(
        ManufacturingEvent.company_id == current_company.id
    )
    result = await db.execute(stmt)
    events = result.scalars().all()
    return {"data": [ManufacturingEventResponse.model_validate(e) for e in events]}"""

new_get_events = """@router.get("/")
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
        stmt = stmt.where(ManufacturingEvent.event_status == status)
    if event_type:
        stmt = stmt.where(ManufacturingEvent.canonical_event_type == event_type)
    if plant_id:
        stmt = stmt.where(ManufacturingEvent.plant_id == plant_id)
    if machine_id:
        stmt = stmt.join(
            EntityResolutionResult,
            ManufacturingEvent.candidate_id == EntityResolutionResult.candidate_id
        ).where(EntityResolutionResult.machine_id == machine_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(ManufacturingEvent.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "data": {
            "items": [ManufacturingEventResponse.model_validate(e).model_dump() for e in events],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    }"""

content = content.replace(old_get_events, new_get_events)

# Replace get_event to include lineage
old_get_event = """@router.get("/{event_id}", response_model=dict)
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

    current_state = apply_revisions(event, revisions)

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
        }
    }"""

new_get_event = """@router.get("/{event_id}", response_model=dict)
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

    current_state = apply_revisions(event, revisions)

    # Fetch Lineage
    resolution = None
    extraction = None
    transcript = None
    attachment = None
    message = None

    if event.candidate_id:
        res_stmt = select(EntityResolutionResult).where(EntityResolutionResult.candidate_id == event.candidate_id)
        resolution = (await db.execute(res_stmt)).scalars().first()
        
        ext_stmt = select(ExtractedEventCandidate).where(ExtractedEventCandidate.id == event.candidate_id)
        extraction = (await db.execute(ext_stmt)).scalars().first()
        
        if extraction and extraction.transcript_id:
            trx_stmt = select(CommunicationTranscript).where(CommunicationTranscript.id == extraction.transcript_id)
            transcript = (await db.execute(trx_stmt)).scalars().first()
            
            if transcript and transcript.attachment_id:
                att_stmt = select(CommunicationAttachment).where(CommunicationAttachment.id == transcript.attachment_id)
                attachment = (await db.execute(att_stmt)).scalars().first()
                
                if attachment and attachment.message_id:
                    msg_stmt = select(CommunicationMessage).where(CommunicationMessage.id == attachment.message_id)
                    message = (await db.execute(msg_stmt)).scalars().first()

    # Serialization helper
    def to_dict(obj):
        if not obj: return None
        # Convert SQLAlchemy object to dict safely
        d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        for k, v in d.items():
            if isinstance(v, datetime):
                d[k] = v.isoformat()
        return d

    # Clean up message payload for safety
    message_dict = to_dict(message)
    if message_dict:
        message_dict.pop("sender_identity", None) # Or keep it if permitted, CTO said "where permitted". Let's keep it but mask it? Just pass it, internal UI.

    return {
        "data": {
            "base_event": ManufacturingEventResponse.model_validate(event).model_dump(),
            "current_state": ManufacturingEventResponse.model_validate(current_state).model_dump(),
            "revisions": [
                ManufacturingEventRevisionResponse.model_validate(r).model_dump()
                for r in revisions
            ],
            "evidence": {
                "communication_message": message_dict,
                "attachments": [to_dict(attachment)] if attachment else [],
                "transcript": to_dict(transcript),
                "extraction": to_dict(extraction),
                "entity_resolution": to_dict(resolution)
            }
        }
    }"""

content = content.replace(old_get_event, new_get_event)

with open("app/api/routes/manufacturing_events.py", "w") as f:
    f.write(content)
