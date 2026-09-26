import re

with open(r'app/services/risk_service.py', 'r', encoding='utf-8') as f:
    t = f.read()

# Add import for AlertEvaluationJob
t = t.replace('from app.models.work_order import WorkOrder', 
'from app.models.work_order import WorkOrder\nfrom app.models.alerts import AlertEvaluationJob')

# We need the plant_id for AlertEvaluationJob. 
# We can fetch wo from db directly in record_risk_transition_if_changed.

new_func = '''
async def record_risk_transition_if_changed(
    db: AsyncSession,
    work_order_id: str,
    company_id: str,
    previous_state: RiskState,
    trigger_type: RiskTriggerType,
    evaluation_time: datetime,
):
    new_state = await fetch_current_risk(db, work_order_id, evaluation_time)
    if previous_state != new_state:
        history = WorkOrderRiskHistory(
            work_order_id=work_order_id,
            company_id=company_id,
            previous_state=previous_state,
            new_state=new_state,
            trigger_type=trigger_type,
            created_at=evaluation_time,
        )
        db.add(history)
        
        # Determine plant_id
        wo_stmt = select(WorkOrder.plant_id).where(WorkOrder.id == work_order_id)
        plant_id = (await db.execute(wo_stmt)).scalar_one_or_none()
        
        job = AlertEvaluationJob(
            company_id=company_id,
            plant_id=plant_id,
            target_work_order_id=work_order_id
        )
        db.add(job)
    return new_state
'''

t = re.sub(r'async def record_risk_transition_if_changed.*?return new_state', new_func, t, flags=re.DOTALL)

with open(r'app/services/risk_service.py', 'w', encoding='utf-8') as f:
    f.write(t)
