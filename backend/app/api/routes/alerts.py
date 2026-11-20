
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_company, get_current_user
from app.infrastructure.database.session import get_db
from app.models.alerts import AlertHistory, AlertInstance, AlertStatus
from app.models.company import Company
from app.models.user import User
from app.services.alert_lifecycle import transition_alert_status

router = APIRouter()

class AlertHistoryResponse(BaseModel):
    id: str
    action: str
    previous_status: str | None = None
    
    previous_severity: str | None = None
    new_severity: str | None = None
    previous_policy_version: int | None = None
    new_policy_version: int | None = None
    previous_rule_version: int | None = None
    new_rule_version: int | None = None
    actor_id: str | None = None
    timestamp: str

class AlertInstanceResponse(BaseModel):
    id: str
    plant_id: str
    alert_family: str
    target_work_order_id: str | None = None
    originating_policy_id: str
    originating_policy_version: int
    originating_rule_id: str
    originating_rule_version: int
    current_policy_id: str
    current_policy_version: int
    current_rule_id: str
    current_rule_version: int
    status: str
    severity: str
    version: int
    created_at: str
    updated_at: str
    history: list[AlertHistoryResponse] | None = []

class AlertListEnvelope(BaseModel):
    data: list[AlertInstanceResponse]

class AlertEnvelope(BaseModel):
    data: AlertInstanceResponse

class TransitionRequest(BaseModel):
    status: str
    expected_version: int
    plant_id: str | None = None

@router.get("", response_model=AlertListEnvelope)
async def list_alerts(
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    status: str | None = Query(None),
    plant_id: str | None = Query(None),
    target_work_order_id: str | None = Query(None)
):
    stmt = select(AlertInstance).where(AlertInstance.company_id == company.id)
    if status:
        stmt = stmt.where(AlertInstance.status == status)
    if plant_id:
        stmt = stmt.where(AlertInstance.plant_id == plant_id)
    if target_work_order_id:
        stmt = stmt.where(AlertInstance.target_work_order_id == target_work_order_id)
        
    stmt = stmt.order_by(AlertInstance.created_at.desc())
    alerts = (await db.execute(stmt)).scalars().all()
    
    res = []
    for a in alerts:
        res.append(AlertInstanceResponse(
            id=a.id, plant_id=a.plant_id, alert_family=a.alert_family,
            target_work_order_id=a.target_work_order_id,
            originating_policy_id=a.originating_policy_id, originating_policy_version=a.originating_policy_version,
            originating_rule_id=a.originating_rule_id, originating_rule_version=a.originating_rule_version,
            current_policy_id=a.current_policy_id, current_policy_version=a.current_policy_version,
            current_rule_id=a.current_rule_id, current_rule_version=a.current_rule_version,
            status=a.status, severity=a.severity, version=a.version,
            created_at=a.created_at.isoformat(), updated_at=a.updated_at.isoformat()
        ))
    return AlertListEnvelope(data=res)

@router.get("/{alert_id}", response_model=AlertEnvelope)
async def get_alert(
    alert_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company)
):
    alert = (await db.execute(select(AlertInstance).where(AlertInstance.id == alert_id, AlertInstance.company_id == company.id))).scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    hist_recs = (await db.execute(select(AlertHistory).where(AlertHistory.alert_instance_id == alert.id).order_by(AlertHistory.timestamp.desc()))).scalars().all()
    
    hist_out = []
    for h in hist_recs:
        hist_out.append(AlertHistoryResponse(
            id=h.id, action=h.action, previous_severity=h.previous_severity, new_severity=h.new_severity,
            previous_policy_version=h.previous_policy_version, new_policy_version=h.new_policy_version,
            previous_rule_version=h.previous_rule_version, new_rule_version=h.new_rule_version,
            actor_id=h.actor_id, timestamp=h.timestamp.isoformat()
        ))
        
    res = AlertInstanceResponse(
        id=alert.id, plant_id=alert.plant_id, alert_family=alert.alert_family,
        target_work_order_id=alert.target_work_order_id,
        originating_policy_id=alert.originating_policy_id, originating_policy_version=alert.originating_policy_version,
        originating_rule_id=alert.originating_rule_id, originating_rule_version=alert.originating_rule_version,
        current_policy_id=alert.current_policy_id, current_policy_version=alert.current_policy_version,
        current_rule_id=alert.current_rule_id, current_rule_version=alert.current_rule_version,
        status=alert.status, severity=alert.severity, version=alert.version,
        created_at=alert.created_at.isoformat(), updated_at=alert.updated_at.isoformat(),
        history=hist_out
    )
    return AlertEnvelope(data=res)

@router.post("/{alert_id}/transition", response_model=AlertEnvelope)
async def transition_alert(
    request: TransitionRequest,
    alert_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_user)
):
    try:
        status_enum = AlertStatus(request.status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
        
    if user.role not in ["SUPERVISOR", "ADMIN", "SYSTEM"]:
        raise HTTPException(status_code=403, detail="Not authorized to transition alerts")
        
    await transition_alert_status(
        db=db,
        alert_id=alert_id,
        company_id=company.id,
        user_id=user.id,
        new_status=status_enum,
        expected_version=request.expected_version,
        user_plant_id=request.plant_id
    )
    await db.commit()
    
    # Reload with history
    return await get_alert(alert_id, db, company)


class JobRetryRequest(BaseModel):
    reason: str

class JobRetryResponse(BaseModel):
    id: str
    status: str
    message: str

@router.post("/jobs/{job_id}/retry", response_model=JobRetryResponse)
async def retry_alert_job(
    request: JobRetryRequest,
    job_id: str = Path(...),
    db: AsyncSession = Depends(get_db),
    company: Company = Depends(get_current_company),
    user: User = Depends(get_current_user)
):
    if user.role not in ["OWNER", "ADMIN", "SYSTEM"]:
        raise HTTPException(status_code=403, detail="Only OWNER, ADMIN, or SYSTEM can retry jobs")
        
    from app.services.alert_job_service import retry_failed_alert_evaluation_job
    
    # Optional plant authorization check if user is bound to a specific plant
    # For now, we assume ADMIN has tenant-wide access, or we check user's plant context if necessary.
    # In Xaiote, get_current_user usually verifies tenant. We can pass None for plant isolation,
    # as ADMINs can manage tenant jobs.
    
    job = await retry_failed_alert_evaluation_job(
        db=db,
        job_id=job_id,
        company_id=company.id,
        actor_id=user.id,
        reason=request.reason,
        user_plant_id=None
    )
    
    await db.commit()
    return JobRetryResponse(id=job.id, status=job.status, message="Job successfully requeued")

