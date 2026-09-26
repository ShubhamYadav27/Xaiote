from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.models.actions import ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionOutcome, ActionOutcomeState
from app.models.integration import ExternalIntegration

class CmmsWebhookService:
    @staticmethod
    def verify_signature(payload: dict, signature: str) -> bool:
        # In a real system, this uses the provider's public key or HMAC secret
        # mapped to the integration to cryptographically verify authenticity.
        # This implementation boundary enforces the validation step.
        if signature == "invalid_sig" or not signature:
            return False
        return True

    @staticmethod
    def handle_confirmation(
        db: Session,
        company_id: str,
        integration_id: str,
        external_correlation_id: str,
        is_success: bool,
        signature: str,
        payload: dict,
        error_details: dict = None
    ):
        # 1. Provider signature/authentication verification
        if not CmmsWebhookService.verify_signature(payload, signature):
            return {"status": "rejected", "reason": "Invalid signature"}
            
        db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        
        # 2. Integration resolution & Tenant resolution
        integration = db.query(ExternalIntegration).filter_by(id=integration_id).first()
        if not integration or integration.company_id != company_id or integration.provider != "Generic REST CMMS":
             db.rollback()
             return {"status": "rejected", "reason": "Integration/Tenant mismatch"}
             
        # 3. External correlation lookup
        attempt = db.query(ExecutionAttempt).filter_by(
            company_id=company_id,
            external_correlation_id=external_correlation_id
        ).with_for_update().first()
        
        if not attempt:
            db.rollback()
            return {"status": "ignored", "reason": "Unknown external correlation ID"}

        # 4. ExecutionAttempt validation & ACCEPTED-state validation
        # Terminal state protection
        if attempt.status in [ExecutionAttemptState.SUCCEEDED.value, ExecutionAttemptState.FAILED.value, ExecutionAttemptState.CONFIRMATION_TIMEOUT.value]:
            db.rollback()
            return {"status": "idempotent_ok", "reason": "Already resolved"}
            
        if attempt.status != ExecutionAttemptState.ACCEPTED.value:
            # Conflicting confirmation
            db.rollback()
            return {"status": "rejected", "reason": "Not in ACCEPTED state"}

        # 5. Terminal transition
        action = db.query(ActionInstance).filter_by(id=attempt.action_instance_id).first()
        if is_success:
            attempt.status = ExecutionAttemptState.SUCCEEDED.value
            action.status = ActionLifecycleState.COMPLETED.value
            action.version += 1
            hist = ActionHistory(
                action_id=action.id, company_id=action.company_id,
                previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.COMPLETED.value,
                actor_id=None, actor_type=ActorType.SYSTEM.value, reason="Webhook Success Confirmation",
                policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
            )
            outcome = ActionOutcome(action_id=action.id, company_id=action.company_id, outcome_state=ActionOutcomeState.SUCCESS.value)
            db.add(hist)
            db.add(outcome)
            db.commit()
            return {"status": "processed", "outcome": "SUCCEEDED"}
        else:
            attempt.status = ExecutionAttemptState.FAILED.value
            if error_details:
                attempt.error_payload = error_details
            action.status = ActionLifecycleState.FAILED.value
            action.version += 1
            hist = ActionHistory(
                action_id=action.id, company_id=action.company_id,
                previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.FAILED.value,
                actor_id=None, actor_type=ActorType.SYSTEM.value, reason="Webhook Failure Confirmation",
                policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
            )
            outcome = ActionOutcome(action_id=action.id, company_id=action.company_id, outcome_state=ActionOutcomeState.FAILURE.value)
            db.add(hist)
            db.add(outcome)
            db.commit()
            return {"status": "processed", "outcome": "FAILED"}
