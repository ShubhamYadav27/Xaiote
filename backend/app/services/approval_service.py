import enum
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from app.models.actions import (
    ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionPolicy, ActionEvidenceLink
)
from app.models.alerts import AlertInstance
from app.services.plant_authorization_service import PlantAuthorizationService
try:
    from app.models.risk import WorkOrderRiskHistory, RiskState
    from app.models.work_order import WorkOrder
    from app.models.impact import ProductionOrderImpact
    from app.models.plant import Plant
    from app.services.risk_evaluator import evaluate as evaluate_risk
except ImportError:
    WorkOrderRiskHistory = None
    evaluate_risk = None
try:
    from app.models.analysis import RootCauseAssessment
except ImportError:
    RootCauseAssessment = None
try:
    from app.models.manufacturing_event import ManufacturingEvent
except ImportError:
    ManufacturingEvent = None

LEVEL_2_ROLES = {"SUPERVISOR", "PRODUCTION_MANAGER", "MAINTENANCE_MANAGER"}
LEVEL_3_ROLES = {"PLANT_HEAD", "ADMIN", "OWNER"}

class ApprovalDomainService:
    @staticmethod
    def _verify_rbac(user_role: str, approval_level: int) -> bool:
        if approval_level == 3:
            return user_role in LEVEL_3_ROLES
        elif approval_level == 2:
            return user_role in LEVEL_2_ROLES or user_role in LEVEL_3_ROLES
        return True

    @staticmethod
    def _evaluate_freshness(db: Session, action_id: str):
        links = db.query(ActionEvidenceLink).filter_by(action_instance_id=action_id).all()
        for link in links:
            if link.evidence_alert_id:
                alert = db.query(AlertInstance).filter_by(id=link.evidence_alert_id).first()
                if not alert:
                    return False, "Alert not found"
                if alert.status == 'RESOLVED':
                    return False, "Alert is RESOLVED"

            if link.evidence_risk_history_id and WorkOrderRiskHistory and evaluate_risk:
                hist = db.query(WorkOrderRiskHistory).filter_by(id=link.evidence_risk_history_id).first()
                if not hist:
                    return False, "RiskHistory not found"
                wo = db.query(WorkOrder).filter_by(id=hist.work_order_id).first()
                if not wo:
                    return False, "WorkOrder not found for Risk evaluation"
                impacts = db.query(ProductionOrderImpact).filter_by(work_order_id=wo.id).all()
                plant = db.query(Plant).filter_by(id=wo.plant_id).first()
                plant_timezone = plant.timezone if plant else "UTC"
                
                # Use current authoritative risk state!
                current_risk_state = evaluate_risk(wo, impacts, datetime.now(timezone.utc), plant_timezone)
                
                if current_risk_state in [RiskState.ON_TRACK, RiskState.NOT_APPLICABLE, RiskState.RESOLVED]:
                    return False, f"Risk is {current_risk_state.value}"
                if current_risk_state == RiskState.PENDING_EVALUATION:
                    return False, f"Risk is {current_risk_state.value}"

            if link.evidence_root_cause_assessment_id and RootCauseAssessment:
                rca = db.query(RootCauseAssessment).filter_by(id=link.evidence_root_cause_assessment_id).first()
                if not rca:
                    return False, "RootCauseAssessment not found"
                if rca.status in ['REJECTED', 'SUPERSEDED']:
                    return False, f"RCA is {rca.status}"
                if rca.status in ['CANDIDATE', 'NEEDS_REVIEW']:
                    return False, f"RCA is {rca.status}"

            if link.evidence_manufacturing_event_id and ManufacturingEvent:
                me = db.query(ManufacturingEvent).filter_by(id=link.evidence_manufacturing_event_id).first()
                if not me:
                    return False, "ManufacturingEvent not found"
                if me.status in ['SUPERSEDED', 'REJECTED']:
                    return False, f"ManufacturingEvent is {me.status}"

        return True, "Fresh"

    @staticmethod
    def approve_action(db: Session, action_id: str, expected_version: int, user_id: str, user_role: str, user_company_id: str, reason: str = None) -> ActionInstance:
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            action = db.query(ActionInstance).filter_by(id=action_id).with_for_update().first()
            if not action:
                raise ValueError("Action not found")
                
            if action.company_id != user_company_id:
                raise ValueError("Cross-tenant access denied")
                
            if action.plant_id:
                is_authorized = PlantAuthorizationService.is_plant_authorized(
                    db=db,
                    user_id=user_id,
                    company_id=user_company_id,
                    role=user_role,
                    target_plant_id=action.plant_id
                )
                if not is_authorized:
                    raise ValueError("Unauthorized plant access")
                
            if action.version != expected_version:
                raise ValueError("OCC mismatch: expected_version does not match")
                
            if action.status != ActionLifecycleState.PENDING_APPROVAL.value:
                raise ValueError(f"Terminal or invalid state: {action.status}")
                
            policy = db.query(ActionPolicy).filter_by(id=action.policy_id, version=action.policy_version, company_id=action.company_id).first()
            if not policy:
                raise ValueError("Bound ActionPolicy not found")
                
            if not ApprovalDomainService._verify_rbac(user_role, policy.approval_level):
                raise ValueError("Unauthorized role for approval level")
                
            is_fresh, stale_reason = ApprovalDomainService._evaluate_freshness(db, action.id)
            
            if not is_fresh:
                action.status = ActionLifecycleState.REJECTED.value
                action.version += 1
                hist = ActionHistory(
                    action_id=action.id,
                    company_id=action.company_id,
                    previous_state=ActionLifecycleState.PENDING_APPROVAL.value,
                    new_state=ActionLifecycleState.REJECTED.value,
                    actor_id=None,
                    actor_type=ActorType.SYSTEM.value,
                    reason=f"Stale or unevaluable operational context: {stale_reason}",
                    policy_id=action.policy_id,
                    policy_version=action.policy_version,
                    action_version=action.version
                )
                db.add(hist)
                db.commit()
                return action
                
            action.status = ActionLifecycleState.APPROVED.value
            action.version += 1
            hist = ActionHistory(
                action_id=action.id,
                company_id=action.company_id,
                previous_state=ActionLifecycleState.PENDING_APPROVAL.value,
                new_state=ActionLifecycleState.APPROVED.value,
                actor_id=user_id,
                actor_type=ActorType.HUMAN.value,
                reason=reason or "Approved by authorized user",
                policy_id=action.policy_id,
                policy_version=action.policy_version,
                action_version=action.version
            )
            db.add(hist)
            db.commit()
            return action
            
        except OperationalError as e:
            db.rollback()
            if "could not serialize access" in str(e).lower():
                raise ValueError("Serialization conflict: Concurrent mutation detected.") from e
            raise
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def reject_action(db: Session, action_id: str, expected_version: int, user_id: str, user_role: str, user_company_id: str, reason: str) -> ActionInstance:
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            action = db.query(ActionInstance).filter_by(id=action_id).with_for_update().first()
            if not action:
                raise ValueError("Action not found")
            if action.company_id != user_company_id:
                raise ValueError("Cross-tenant access denied")
            
            if action.plant_id:
                is_authorized = PlantAuthorizationService.is_plant_authorized(
                    db=db,
                    user_id=user_id,
                    company_id=user_company_id,
                    role=user_role,
                    target_plant_id=action.plant_id
                )
                if not is_authorized:
                    raise ValueError("Unauthorized plant access")
                    
            if action.version != expected_version:
                raise ValueError("OCC mismatch: expected_version does not match")
            if action.status != ActionLifecycleState.PENDING_APPROVAL.value:
                raise ValueError(f"Terminal or invalid state: {action.status}")
                
            policy = db.query(ActionPolicy).filter_by(id=action.policy_id, version=action.policy_version, company_id=action.company_id).first()
            if not policy:
                raise ValueError("Bound ActionPolicy not found")
            if not ApprovalDomainService._verify_rbac(user_role, policy.approval_level):
                raise ValueError("Unauthorized role for approval level")
                
            action.status = ActionLifecycleState.REJECTED.value
            action.version += 1
            hist = ActionHistory(
                action_id=action.id,
                company_id=action.company_id,
                previous_state=ActionLifecycleState.PENDING_APPROVAL.value,
                new_state=ActionLifecycleState.REJECTED.value,
                actor_id=user_id,
                actor_type=ActorType.HUMAN.value,
                reason=reason,
                policy_id=action.policy_id,
                policy_version=action.policy_version,
                action_version=action.version
            )
            db.add(hist)
            db.commit()
            return action
        except OperationalError as e:
            db.rollback()
            if "could not serialize access" in str(e).lower():
                raise ValueError("Serialization conflict: Concurrent mutation detected.") from e
            raise
        except Exception:
            db.rollback()
            raise
