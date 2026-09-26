from enum import Enum

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import (
    AlertEvaluationJob,
    AlertEvaluationJobStatus,
    AlertEvidenceLink,
    AlertHistory,
    AlertInstance,
    AlertPolicy,
    AlertRule,
    AlertStatus,
)
from app.models.risk import RiskState, WorkOrderRiskHistory


class MatrixAction(str, Enum):
    CREATE = "CREATE"
    ESCALATE = "ESCALATE"
    DE_ESCALATE = "DE_ESCALATE"
    NO_OP = "NO_OP"
    RESOLVE = "RESOLVE"
    IGNORE = "IGNORE"
    NOT_ALLOWED = "NOT_ALLOWED_BY_RISKEVALUATOR"

def get_matrix_action(previous_state: RiskState | str, current_state: RiskState) -> MatrixAction:
    MATRIX = {
        "NONE": {
            RiskState.PENDING_EVALUATION: MatrixAction.IGNORE,
            RiskState.ON_TRACK: MatrixAction.IGNORE,
            RiskState.AT_RISK: MatrixAction.CREATE,
            RiskState.DELAYED: MatrixAction.CREATE,
            RiskState.CRITICAL: MatrixAction.CREATE,
            RiskState.RESOLVED: MatrixAction.IGNORE,
            RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
        },
        RiskState.PENDING_EVALUATION: {
            RiskState.PENDING_EVALUATION: MatrixAction.IGNORE,
            RiskState.ON_TRACK: MatrixAction.IGNORE,
            RiskState.AT_RISK: MatrixAction.CREATE,
            RiskState.DELAYED: MatrixAction.CREATE,
            RiskState.CRITICAL: MatrixAction.CREATE,
            RiskState.RESOLVED: MatrixAction.IGNORE,
            RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
        },
        RiskState.ON_TRACK: {
            RiskState.PENDING_EVALUATION: MatrixAction.IGNORE,
            RiskState.ON_TRACK: MatrixAction.IGNORE,
            RiskState.AT_RISK: MatrixAction.CREATE,
            RiskState.DELAYED: MatrixAction.CREATE,
            RiskState.CRITICAL: MatrixAction.CREATE,
            RiskState.RESOLVED: MatrixAction.IGNORE,
            RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
        },
        RiskState.AT_RISK: {
            RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
            RiskState.ON_TRACK: MatrixAction.RESOLVE,
            RiskState.AT_RISK: MatrixAction.NO_OP,
            RiskState.DELAYED: MatrixAction.ESCALATE,
            RiskState.CRITICAL: MatrixAction.ESCALATE,
            RiskState.RESOLVED: MatrixAction.RESOLVE,
            RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
        },
        RiskState.DELAYED: {
            RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
            RiskState.ON_TRACK: MatrixAction.RESOLVE,
            RiskState.AT_RISK: MatrixAction.DE_ESCALATE,
            RiskState.DELAYED: MatrixAction.NO_OP,
            RiskState.CRITICAL: MatrixAction.ESCALATE,
            RiskState.RESOLVED: MatrixAction.RESOLVE,
            RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
        },
        RiskState.CRITICAL: {
            RiskState.PENDING_EVALUATION: MatrixAction.RESOLVE,
            RiskState.ON_TRACK: MatrixAction.RESOLVE,
            RiskState.AT_RISK: MatrixAction.DE_ESCALATE,
            RiskState.DELAYED: MatrixAction.DE_ESCALATE,
            RiskState.CRITICAL: MatrixAction.NO_OP,
            RiskState.RESOLVED: MatrixAction.RESOLVE,
            RiskState.NOT_APPLICABLE: MatrixAction.RESOLVE,
        },
        RiskState.RESOLVED: {
            RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
            RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
            RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
            RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
            RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
            RiskState.RESOLVED: MatrixAction.IGNORE,
            RiskState.NOT_APPLICABLE: MatrixAction.NOT_ALLOWED,
        },
        RiskState.NOT_APPLICABLE: {
            RiskState.PENDING_EVALUATION: MatrixAction.NOT_ALLOWED,
            RiskState.ON_TRACK: MatrixAction.NOT_ALLOWED,
            RiskState.AT_RISK: MatrixAction.NOT_ALLOWED,
            RiskState.DELAYED: MatrixAction.NOT_ALLOWED,
            RiskState.CRITICAL: MatrixAction.NOT_ALLOWED,
            RiskState.RESOLVED: MatrixAction.NOT_ALLOWED,
            RiskState.NOT_APPLICABLE: MatrixAction.IGNORE,
        }
    }
    return MATRIX[previous_state][current_state]

async def process_alert_job(db: AsyncSession, job: AlertEvaluationJob):
    if not job.target_work_order_id:
        job.status = AlertEvaluationJobStatus.FAILED.value
        job.error_detail = "Incident-targeted alerts are explicitly REJECTED as out-of-scope for MVP"
        return

    hist_stmt = select(WorkOrderRiskHistory).where(
        WorkOrderRiskHistory.work_order_id == job.target_work_order_id
    ).order_by(WorkOrderRiskHistory.created_at.desc(), WorkOrderRiskHistory.id.desc()).limit(1)
    
    risk_hist = (await db.execute(hist_stmt)).scalar_one_or_none()
    if not risk_hist:
        job.status = AlertEvaluationJobStatus.COMPLETED.value
        return
        
    current_risk_state = risk_hist.new_state
    
    alert_stmt = select(AlertInstance).where(
        AlertInstance.target_work_order_id == job.target_work_order_id,
        AlertInstance.status.in_([AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value])
    )
    alert = (await db.execute(alert_stmt)).scalar_one_or_none()
    
    previous_alert_state = "NONE"
    if alert:
        previous_alert_state = RiskState(alert.severity)
    
    action = get_matrix_action(previous_alert_state, current_risk_state)
    
    if action == MatrixAction.NOT_ALLOWED:
        job.status = AlertEvaluationJobStatus.FAILED.value
        job.error_detail = "Transition not allowed by RiskEvaluator"
        return
        
    if action in (MatrixAction.IGNORE, MatrixAction.NO_OP):
        job.status = AlertEvaluationJobStatus.COMPLETED.value
        return
        
    rule_stmt = select(AlertRule).join(AlertPolicy, and_(
        AlertPolicy.id == AlertRule.policy_id,
        AlertPolicy.version == AlertRule.policy_version,
        AlertPolicy.company_id == AlertRule.company_id
    )).where(
        AlertRule.company_id == job.company_id,
        AlertRule.alert_family == "PRODUCTION_RISK",
        AlertRule.severity == current_risk_state.value
    ).order_by(AlertRule.version.desc()).limit(1)
    
    current_rule = (await db.execute(rule_stmt)).scalar_one_or_none()
    
    if not current_rule and action in (MatrixAction.CREATE, MatrixAction.ESCALATE, MatrixAction.DE_ESCALATE):
        job.status = AlertEvaluationJobStatus.FAILED.value
        job.error_detail = f"No applicable rule found for severity {current_risk_state.value}"
        return
        
    if action == MatrixAction.CREATE:
        new_alert = AlertInstance(
            company_id=job.company_id,
            plant_id=job.plant_id,
            alert_family="PRODUCTION_RISK",
            target_work_order_id=job.target_work_order_id,
            originating_policy_id=current_rule.policy_id,
            originating_policy_version=current_rule.policy_version,
            originating_rule_id=current_rule.id,
            originating_rule_version=current_rule.version,
            current_policy_id=current_rule.policy_id,
            current_policy_version=current_rule.policy_version,
            current_rule_id=current_rule.id,
            current_rule_version=current_rule.version,
            status=AlertStatus.ACTIVE.value,
            severity=current_risk_state.value
        )
        db.add(new_alert)
        await db.flush()
        
        history = AlertHistory(
            alert_instance_id=new_alert.id,
            company_id=job.company_id,
            action="CREATED",
            new_severity=current_risk_state.value,
            new_policy_id=current_rule.policy_id,
            new_policy_version=current_rule.policy_version,
            new_rule_id=current_rule.id,
            new_rule_version=current_rule.version
        )
        db.add(history)
        
        ev_link = AlertEvidenceLink(
            alert_instance_id=new_alert.id,
            company_id=job.company_id,
            evidence_risk_history_id=risk_hist.id
        )
        db.add(ev_link)
            
    elif action in (MatrixAction.ESCALATE, MatrixAction.DE_ESCALATE):
        if alert:
            prev_policy_id = alert.current_policy_id
            prev_policy_version = alert.current_policy_version
            prev_rule_id = alert.current_rule_id
            prev_rule_version = alert.current_rule_version
            prev_severity = alert.severity
            
            alert.current_policy_id = current_rule.policy_id
            alert.current_policy_version = current_rule.policy_version
            alert.current_rule_id = current_rule.id
            alert.current_rule_version = current_rule.version
            alert.severity = current_risk_state.value
            alert.status = AlertStatus.ACTIVE.value # Re-activate if acknowledged
            alert.version += 1
            
            history = AlertHistory(
                alert_instance_id=alert.id,
                company_id=job.company_id,
                action=action.value,
                previous_severity=prev_severity,
                new_severity=current_risk_state.value,
                previous_policy_id=prev_policy_id,
                previous_policy_version=prev_policy_version,
                previous_rule_id=prev_rule_id,
                previous_rule_version=prev_rule_version,
                new_policy_id=current_rule.policy_id,
                new_policy_version=current_rule.policy_version,
                new_rule_id=current_rule.id,
                new_rule_version=current_rule.version
            )
            db.add(history)
            
    elif action == MatrixAction.RESOLVE:
        if alert:
            alert.status = AlertStatus.RESOLVED.value
            alert.version += 1
            
            history = AlertHistory(
                alert_instance_id=alert.id,
                company_id=job.company_id,
                action="RESOLVED",
                previous_severity=alert.severity,
                previous_policy_id=alert.current_policy_id,
                previous_policy_version=alert.current_policy_version,
                previous_rule_id=alert.current_rule_id,
                previous_rule_version=alert.current_rule_version
            )
            db.add(history)

    job.status = AlertEvaluationJobStatus.COMPLETED.value
