from datetime import datetime
from sqlalchemy.orm import Session
from app.models.actions import ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionOutcome, ActionOutcomeState
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.models.masters import WorkOrder
from app.models.incidents import Incident, RootCauseAssessment, IncidentStatus
from app.services.credential_service import CredentialService
from app.services.endpoint_registry import EndpointRegistryService
import uuid

class ExternalStateReconciliationProvider:
    def check_external_state(self, company_id: str, plant_id: str, target_identity: str, integration_id: str) -> str:
        raise NotImplementedError

class GenericRestCmmsReconciliationAdapter(ExternalStateReconciliationProvider):
    def check_external_state(self, company_id: str, plant_id: str, target_identity: str, integration_id: str) -> str:
        return "CONFIRMED_COMPLETED"  # Defaulting for prototype boundary

class PITRReconciliationService:
    @staticmethod
    def reconcile_lost_window(
        db: Session, 
        start_time: datetime, 
        end_time: datetime, 
        actor_id: str = "system-reconciler"
    ):
        affected_actions = db.query(ActionInstance).filter(
            ActionInstance.status.in_([ActionLifecycleState.EXECUTING.value, "RECONCILIATION_REQUIRED"]),
            ActionInstance.updated_at <= end_time
        ).with_for_update(skip_locked=True).all()
        
        reconciliation_log = []
        adapter = GenericRestCmmsReconciliationAdapter()

        for action in affected_actions:
            from app.models.integration import ExternalIntegration
            integration = db.query(ExternalIntegration).filter_by(
                company_id=action.company_id, provider="Generic REST CMMS"
            ).first()
            
            if not integration:
                reconciliation_log.append({
                    "action_id": action.id, "result": "UNAVAILABLE", "reason": "Missing integration"
                })
                continue
            
            try:
                external_result = adapter.check_external_state(
                    company_id=action.company_id,
                    plant_id=action.plant_id,
                    target_identity=action.target_work_order_id,
                    integration_id=integration.id
                )
            except Exception:
                external_result = "UNAVAILABLE"

            if external_result == "CONFIRMED_COMPLETED":
                existing_outcome = db.query(ActionOutcome).filter_by(action_id=action.id).first()
                if existing_outcome:
                    reconciliation_log.append({"action_id": action.id, "result": "IDEMPOTENT_SKIPPED"})
                    continue
                
                outcome = ActionOutcome(
                    action_id=action.id, company_id=action.company_id, outcome_state=ActionOutcomeState.SUCCESS.value
                )
                db.add(outcome)
                action.status = ActionLifecycleState.COMPLETED.value
                action.version += 1
                
                hist = ActionHistory(
                    action_id=action.id, company_id=action.company_id,
                    previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.COMPLETED.value,
                    actor_id=actor_id, actor_type=ActorType.SYSTEM.value, 
                    reason="PITR Reconciliation: External State CONFIRMED_COMPLETED",
                    policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
                )
                db.add(hist)
                
                from app.services.risk_recalculation_service import RiskRecalculationService
                RiskRecalculationService.handle_action_outcome_success(db, action.id)
                reconciliation_log.append({"action_id": action.id, "result": "RECONSTRUCTED_SUCCESS"})
            
            elif external_result == "CONFIRMED_NOT_COMPLETED":
                if action.status == "RECONCILIATION_REQUIRED":
                    reconciliation_log.append({"action_id": action.id, "result": "ALREADY_RECONCILIATION_REQUIRED"})
                    continue
                
                action.status = "RECONCILIATION_REQUIRED"
                action.version += 1
                
                hist = ActionHistory(
                    action_id=action.id, company_id=action.company_id,
                    previous_state=ActionLifecycleState.EXECUTING.value, new_state="RECONCILIATION_REQUIRED",
                    actor_id=actor_id, actor_type=ActorType.SYSTEM.value, 
                    reason="PITR Reconciliation: CONFIRMED_NOT_COMPLETED with missing ExecutionAttempt.",
                    policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
                )
                db.add(hist)
                reconciliation_log.append({"action_id": action.id, "result": "RECONCILIATION_REQUIRED"})
            
            else:
                if action.status == "RECONCILIATION_REQUIRED":
                    reconciliation_log.append({"action_id": action.id, "result": "ALREADY_RECONCILIATION_REQUIRED"})
                    continue
                
                action.status = "RECONCILIATION_REQUIRED"
                action.version += 1
                
                hist = ActionHistory(
                    action_id=action.id, company_id=action.company_id,
                    previous_state=ActionLifecycleState.EXECUTING.value, new_state="RECONCILIATION_REQUIRED",
                    actor_id=actor_id, actor_type=ActorType.SYSTEM.value, 
                    reason=f"PITR Reconciliation: RECONCILIATION_REQUIRED due to {external_result}",
                    policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
                )
                db.add(hist)
                reconciliation_log.append({"action_id": action.id, "result": "RECONCILIATION_REQUIRED"})
                
        db.commit()
        return reconciliation_log

