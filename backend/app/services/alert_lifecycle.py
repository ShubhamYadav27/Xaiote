from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import AlertHistory, AlertInstance, AlertStatus


async def transition_alert_status(
    db: AsyncSession,
    alert_id: str,
    company_id: str,
    user_id: str,
    new_status: AlertStatus,
    expected_version: int,
    user_plant_id: str | None = None,
):
    stmt = select(AlertInstance).where(
        AlertInstance.id == alert_id,
        AlertInstance.company_id == company_id
    )
    if user_plant_id:
        stmt = stmt.where(AlertInstance.plant_id == user_plant_id)
    stmt = stmt.with_for_update()
    
    alert = (await db.execute(stmt)).scalar_one_or_none()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    if alert.version != expected_version:
        raise HTTPException(status_code=409, detail="OCC conflict: stale version")
        
    # State transitions
    # ACTIVE -> ACKNOWLEDGED
    # ACTIVE -> RESOLVED
    # ACKNOWLEDGED -> RESOLVED
    if alert.status == AlertStatus.RESOLVED.value:
        raise HTTPException(status_code=400, detail="Alert is already resolved")
        
    if new_status == AlertStatus.ACKNOWLEDGED:
        if alert.status != AlertStatus.ACTIVE.value:
            raise HTTPException(status_code=400, detail="Can only acknowledge an ACTIVE alert")
        alert.status = AlertStatus.ACKNOWLEDGED.value
        
    elif new_status == AlertStatus.RESOLVED:
        alert.status = AlertStatus.RESOLVED.value
    else:
        raise HTTPException(status_code=400, detail="Invalid transition")

    alert.version += 1
    
    history = AlertHistory(
        alert_instance_id=alert.id,
        company_id=company_id,
        action=new_status.value,
        previous_severity=alert.severity,
        previous_policy_id=alert.current_policy_id,
        previous_policy_version=alert.current_policy_version,
        previous_rule_id=alert.current_rule_id,
        previous_rule_version=alert.current_rule_version,
        actor_id=user_id
    )
    db.add(history)
    return alert
