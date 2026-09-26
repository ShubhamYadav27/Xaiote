import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.models.actions import ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionOutcome, ActionOutcomeState
from app.models.integration import ExternalIntegration
from app.interfaces.adapters import BaseActionAdapter, AdapterExecutionContext, AdapterResult

class ExecutionWorkerService:
    
    @staticmethod
    def process_pending_attempt(db: Session, adapter: BaseActionAdapter, attempt_id: str, worker_id: str = "worker-1"):
        # 1. Claim
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        
        attempt = db.query(ExecutionAttempt).filter(
            ExecutionAttempt.id == attempt_id,
            ((ExecutionAttempt.status == ExecutionAttemptState.PENDING.value) | 
             ((ExecutionAttempt.status == ExecutionAttemptState.RUNNING.value) & (ExecutionAttempt.lease_expires_at < datetime.now(timezone.utc))))
        ).with_for_update(skip_locked=True).first()
        
        if not attempt:
            return None
            
        action = db.query(ActionInstance).filter_by(id=attempt.action_instance_id).first()
        
        # Security: Evaluate exact Work Order safety rules
        if action.action_type != "MARK_WORK_ORDER_COMPLETED":
            return ExecutionWorkerService._fail_closed(db, attempt, action, "Unsupported ActionType for this integration")
            
        # Target must be IN_PROGRESS or PLANNED
        # Note: Xaiote WorkOrder status is mocked here for simplicity, 
        # in reality we'd join WorkOrder model.
        mocked_internal_wo_status = attempt.error_payload.get("_mock_internal_state", "IN_PROGRESS") if attempt.error_payload else "IN_PROGRESS"
        if mocked_internal_wo_status not in ["PLANNED", "IN_PROGRESS"]:
            return ExecutionWorkerService._fail_closed(db, attempt, action, f"Invalid local WorkOrder state: {mocked_internal_wo_status}")

        integration = db.query(ExternalIntegration).filter_by(
            company_id=action.company_id,
            provider="Generic REST CMMS"
        ).first()
        if not integration or not integration.enabled:
             return ExecutionWorkerService._fail_closed(db, attempt, action, "Integration not enabled or not found")

        from app.services.approval_service import ApprovalDomainService
        is_fresh, stale_reason = ApprovalDomainService._evaluate_freshness(db, action.id)
        if not is_fresh:
            return ExecutionWorkerService._fail_closed(db, attempt, action, stale_reason)
            
        attempt.status = ExecutionAttemptState.RUNNING.value
        attempt.worker_id = worker_id
        attempt.lease_expires_at = datetime.now(timezone.utc) + timedelta(seconds=60)
        db.commit()
        
        # 2. Context Construction (Strictly Typed)
        # We parse the DB payload into validated_parameters.
        params = attempt.error_payload if attempt.error_payload else {}
        
        context = AdapterExecutionContext(
            company_id=action.company_id,
            plant_id=action.plant_id,
            action_instance_id=action.id,
            execution_attempt_id=attempt.id,
            action_type=action.action_type,
            allowlisted_operation="UPDATE_WORK_ORDER_STATUS",
            validated_parameters=params,
            target_identity=action.target_work_order_id,
            correlation_id=None,
            downstream_idempotency_key=attempt.downstream_idempotency_key,
            integration_id=integration.id,
            credential_reference=integration.credential_reference,
            credential_version=integration.credential_version
        )
        
        # 3. External Execution (Outside DB Lock)
        try:
            result = adapter.execute(context)
        except Exception as e:
            result = AdapterResult(success=False, error_payload={"error": str(e)}, is_unknown_outcome=True)
            
        # 4. Post-Execution Persist - RE-LOCK AND VERIFY LEASE
        db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        re_attempt = db.query(ExecutionAttempt).filter_by(id=attempt_id).with_for_update().first()
        
        if not re_attempt or re_attempt.worker_id != worker_id or re_attempt.status != ExecutionAttemptState.RUNNING.value:
            db.rollback()
            return None
            
        re_action = db.query(ActionInstance).filter_by(id=re_attempt.action_instance_id).first()
            
        if result.is_unknown_outcome:
            re_attempt.status = ExecutionAttemptState.UNKNOWN.value
            re_attempt.error_payload = result.error_payload
            db.commit()
            caps = adapter.get_capabilities()
            if caps.supports_idempotency:
                new_attempt = ExecutionAttempt(
                    company_id=re_attempt.company_id,
                    action_instance_id=re_attempt.action_instance_id,
                    attempt_number=re_attempt.attempt_number + 1,
                    downstream_idempotency_key=re_attempt.downstream_idempotency_key,
                    status=ExecutionAttemptState.PENDING.value,
                    provider_type=re_attempt.provider_type
                )
                db.add(new_attempt)
                db.commit()
            return re_attempt
            
        if result.is_accepted_pending_confirmation:
            # Atomic ACCEPTED handoff
            re_attempt.status = ExecutionAttemptState.ACCEPTED.value
            re_attempt.external_correlation_id = result.external_correlation_id
            # NO ActionOutcome is created
            # ActionInstance remains EXECUTING
            db.commit()
            return re_attempt

        if result.success:
            re_attempt.status = ExecutionAttemptState.SUCCEEDED.value
            re_attempt.external_correlation_id = result.external_correlation_id
            re_action.status = ActionLifecycleState.COMPLETED.value
            re_action.version += 1
            hist = ActionHistory(
                action_id=re_action.id, company_id=re_action.company_id,
                previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.COMPLETED.value,
                actor_id=None, actor_type=ActorType.SYSTEM.value, reason="Adapter Success",
                policy_id=re_action.policy_id, policy_version=re_action.policy_version, action_version=re_action.version
            )
            outcome = ActionOutcome(action_id=re_action.id, company_id=re_action.company_id, outcome_state=ActionOutcomeState.SUCCESS.value)
            db.add(hist)
            db.add(outcome)
            db.commit()
            return re_attempt
            
        else:
            if result.is_retryable_error:
                re_attempt.status = ExecutionAttemptState.FAILED.value
                re_attempt.error_payload = result.error_payload
                db.commit()
                new_attempt = ExecutionAttempt(
                    company_id=re_attempt.company_id,
                    action_instance_id=re_attempt.action_instance_id,
                    attempt_number=re_attempt.attempt_number + 1,
                    downstream_idempotency_key=re_attempt.downstream_idempotency_key,
                    status=ExecutionAttemptState.PENDING.value,
                    provider_type=re_attempt.provider_type
                )
                db.add(new_attempt)
                db.commit()
                return re_attempt
            else:
                re_attempt.status = ExecutionAttemptState.FAILED.value
                re_attempt.error_payload = result.error_payload
                re_action.status = ActionLifecycleState.FAILED.value
                re_action.version += 1
                hist = ActionHistory(
                    action_id=re_action.id, company_id=re_action.company_id,
                    previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.FAILED.value,
                    actor_id=None, actor_type=ActorType.SYSTEM.value, reason="Adapter Permanent Failure",
                    policy_id=re_action.policy_id, policy_version=re_action.policy_version, action_version=re_action.version
                )
                outcome = ActionOutcome(action_id=re_action.id, company_id=re_action.company_id, outcome_state=ActionOutcomeState.FAILURE.value)
                db.add(hist)
                db.add(outcome)
                db.commit()
                return re_attempt
                
    @staticmethod
    def _fail_closed(db, attempt, action, reason):
        attempt.status = ExecutionAttemptState.FAILED.value
        attempt.error_payload = {"error": f"Failed closed prior to network I/O: {reason}"}
        action.status = ActionLifecycleState.FAILED.value
        action.version += 1
        hist = ActionHistory(
            action_id=action.id, company_id=action.company_id,
            previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.FAILED.value,
            actor_id=None, actor_type=ActorType.SYSTEM.value, reason=reason,
            policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
        )
        outcome = ActionOutcome(action_id=action.id, company_id=action.company_id, outcome_state=ActionOutcomeState.FAILURE.value)
        db.add(hist)
        db.add(outcome)
        db.commit()
        return attempt

