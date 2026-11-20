from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import update

from app.api.dependencies.auth import get_current_company
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.communication import ExtractedEventCandidate, CommunicationTranscript, CommunicationAttachment, CommunicationMessage
from app.models.resolution import EntityResolutionResult
from app.models.manufacturing_event import CanonicalizationJob, CanonicalizationJobStatus
from app.models.plant import Plant
from app.models.masters import Machine

router = APIRouter()

class CandidateResolveRequest(BaseModel):
    machine_id: Optional[str] = None
    plant_id: Optional[str] = None

class CandidateResponse(BaseModel):
    id: str
    processing_status: str
    payload: dict
    original_message: Optional[str] = None
    original_channel: Optional[str] = None

@router.get("/pending", response_model=List[CandidateResponse])
async def get_pending_candidates(
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ExtractedEventCandidate, EntityResolutionResult).join(
        EntityResolutionResult, ExtractedEventCandidate.id == EntityResolutionResult.candidate_id
    ).where(
        ExtractedEventCandidate.company_id == current_company.id,
        EntityResolutionResult.overall_status == "NEEDS_REVIEW"
    )
    res = await db.execute(stmt)
    candidates = res.all()
    
    response = []
    for cand, er in candidates:
        response.append(CandidateResponse(
            id=cand.id,
            processing_status=er.overall_status,
            payload=cand.payload or {}
        ))
    return response

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    # Fetch candidate
    stmt = select(ExtractedEventCandidate).where(
        ExtractedEventCandidate.id == candidate_id,
        ExtractedEventCandidate.company_id == current_company.id
    )
    cand = (await db.execute(stmt)).scalars().first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    er_stmt = select(EntityResolutionResult).where(EntityResolutionResult.candidate_id == cand.id)
    er = (await db.execute(er_stmt)).scalars().first()
    
    # Try to fetch original message if possible
    orig_msg_text = None
    orig_channel = None
    if cand.transcript_id:
        # Join transcript -> attachment -> message
        t_stmt = select(CommunicationTranscript).where(CommunicationTranscript.id == cand.transcript_id)
        tx = (await db.execute(t_stmt)).scalars().first()
        if tx and tx.attachment_id:
            a_stmt = select(CommunicationAttachment).where(CommunicationAttachment.id == tx.attachment_id)
            att = (await db.execute(a_stmt)).scalars().first()
            if att and att.message_id:
                m_stmt = select(CommunicationMessage).where(CommunicationMessage.id == att.message_id)
                msg = (await db.execute(m_stmt)).scalars().first()
                if msg:
                    orig_msg_text = msg.raw_payload
                    orig_channel = msg.source_channel

    return CandidateResponse(
        id=cand.id,
        processing_status=er.overall_status if er else cand.processing_status,
        payload=cand.payload or {},
        original_message=orig_msg_text,
        original_channel=orig_channel
    )

@router.post("/{candidate_id}/resolve", response_model=dict)
async def resolve_candidate(
    candidate_id: str,
    req: CandidateResolveRequest,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db)
):
    async with db.begin_nested():
        # Get ER result with FOR UPDATE to safely lock it
        stmt = select(EntityResolutionResult).where(
            EntityResolutionResult.candidate_id == candidate_id,
            EntityResolutionResult.company_id == current_company.id
        ).with_for_update()
        er = (await db.execute(stmt)).scalars().first()
        
        if not er:
            raise HTTPException(status_code=404, detail="Entity Resolution Result not found")
            
        if er.overall_status == "RESOLVED":
            # Idempotent - already resolved
            return {"status": "success", "message": "Already resolved"}
            
        if er.overall_status != "NEEDS_REVIEW":
            raise HTTPException(status_code=400, detail=f"Cannot resolve candidate in status: {er.overall_status}")
            
        # Validate plant
        if req.plant_id:
            p_stmt = select(Plant).where(Plant.id == req.plant_id, Plant.company_id == current_company.id)
            if not (await db.execute(p_stmt)).scalars().first():
                raise HTTPException(status_code=403, detail="Plant not found or cross-tenant access denied")
            er.plant_id = req.plant_id
            
        # Validate machine
        if req.machine_id:
            m_stmt = select(Machine).where(Machine.id == req.machine_id, Machine.company_id == current_company.id)
            m = (await db.execute(m_stmt)).scalars().first()
            if not m:
                raise HTTPException(status_code=403, detail="Machine not found or cross-tenant access denied")
            er.machine_id = req.machine_id
            er.machine_state = "RESOLVED"
            if not er.plant_id and m.plant_id:
                er.plant_id = m.plant_id
                
        er.overall_status = "RESOLVED"
        
        # Now update CanonicalizationJob to PENDING
        j_stmt = select(CanonicalizationJob).where(
            CanonicalizationJob.candidate_id == candidate_id,
            CanonicalizationJob.company_id == current_company.id
        ).with_for_update()
        job = (await db.execute(j_stmt)).scalars().first()
        if job:
            job.status = CanonicalizationJobStatus.PENDING
            job.attempt_count = 0
            job.last_error = None
            job.worker_id = None
        else:
            # Create the job if it doesn't exist for some reason
            new_job = CanonicalizationJob(
                company_id=current_company.id,
                candidate_id=candidate_id,
                status=CanonicalizationJobStatus.PENDING
            )
            db.add(new_job)

    await db.commit()
    return {"status": "success", "message": "Candidate resolved"}

@router.get("/debug")
async def debug_db(db: AsyncSession = Depends(get_db)):
    from app.core.config import settings
    return {"db_url": settings.DATABASE_URL}
