from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.models.company import Company
from app.models.user import User
from app.services.analysis_service import (
    confirm_assessment,
    generate_analysis_for_incident,
    get_latest_analysis,
    reject_assessment,
)

router = APIRouter(prefix="/analysis", tags=["analysis"])


class GenerateAnalysisRequest(BaseModel):
    incident_id: str
    manual_reanalysis: bool = False


class RevisionRequest(BaseModel):
    expected_revision: int
    reason: str = None


@router.get("/incidents/{incident_id}")
async def get_analysis(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_company: Company = Depends(get_current_company),
) -> Any:
    analysis, is_stale = await get_latest_analysis(db, incident_id, current_company.id)
    if not analysis:
        raise HTTPException(
            status_code=404, detail="No analysis found for this incident"
        )

    return {
        "analysis_id": analysis.id,
        "version": analysis.version,
        "status": analysis.status.value,
        "is_stale": is_stale,
    }


@router.post("/incidents/{incident_id}/generate")
async def generate_analysis(
    incident_id: str,
    request: GenerateAnalysisRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_company: Company = Depends(get_current_company),
) -> Any:
    if current_user.role not in ["SUPERVISOR", "ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to generate analysis"
        )

    if request.incident_id != incident_id:
        raise HTTPException(status_code=400, detail="Incident ID mismatch")

    analysis = await generate_analysis_for_incident(
        session=db,
        incident_id=incident_id,
        company_id=current_company.id,
        idempotency_key=idempotency_key,
        manual_reanalysis=request.manual_reanalysis,
    )
    return {
        "analysis_id": analysis.id,
        "status": analysis.status.value,
        "version": analysis.version,
    }


@router.post("/{analysis_id}/assessments/{assessment_id}/confirm")
async def confirm(
    analysis_id: str,
    assessment_id: str,
    request: RevisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_company: Company = Depends(get_current_company),
) -> Any:
    if current_user.role not in ["SUPERVISOR", "ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to confirm assessment"
        )

    assessment = await confirm_assessment(
        session=db,
        assessment_id=assessment_id,
        company_id=current_company.id,
        actor_id=current_user.id,
        expected_revision=request.expected_revision,
    )
    return {
        "assessment_id": assessment.id,
        "status": assessment.status.value,
        "revision": assessment.revision,
    }


@router.post("/{analysis_id}/assessments/{assessment_id}/reject")
async def reject(
    analysis_id: str,
    assessment_id: str,
    request: RevisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    current_company: Company = Depends(get_current_company),
) -> Any:
    if current_user.role not in ["SUPERVISOR", "ADMIN"]:
        raise HTTPException(
            status_code=403, detail="Not authorized to reject assessment"
        )

    assessment = await reject_assessment(
        session=db,
        assessment_id=assessment_id,
        company_id=current_company.id,
        actor_id=current_user.id,
        expected_revision=request.expected_revision,
        reason=request.reason,
    )
    return {
        "assessment_id": assessment.id,
        "status": assessment.status.value,
        "revision": assessment.revision,
    }
