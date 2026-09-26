from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.models.actions import ActionInstance, ActionHistory, ActionLifecycleState, ActorType

class StaleExecutionMonitor:
    @staticmethod
    def sweep_stale_accepted_attempts(db: Session, timeout_hours: int = 24):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
        
        # Find attempts stuck in ACCEPTED past the SLA
        stale_attempts = db.query(ExecutionAttempt).filter(
            ExecutionAttempt.status == ExecutionAttemptState.ACCEPTED.value,
            ExecutionAttempt.updated_at < cutoff
        ).with_for_update(skip_locked=True).all()
        
        swept_count = 0
        for attempt in stale_attempts:
            attempt.status = ExecutionAttemptState.CONFIRMATION_TIMEOUT.value
            
            # Note: We do NOT create an ActionOutcome or mark the instance as FAILED.
            # It remains EXECUTING, but requires human operational review.
            
            # Log history to action
            action = db.query(ActionInstance).filter_by(id=attempt.action_instance_id).first()
            if action:
                hist = ActionHistory(
                    action_id=action.id, company_id=action.company_id,
                    previous_state=ActionLifecycleState.EXECUTING.value, new_state=ActionLifecycleState.EXECUTING.value,
                    actor_id=None, actor_type=ActorType.SYSTEM.value, reason=f"Confirmation SLA expired ({timeout_hours}h)",
                    policy_id=action.policy_id, policy_version=action.policy_version, action_version=action.version
                )
                db.add(hist)
            
            swept_count += 1
            
        if swept_count > 0:
            db.commit()
        return swept_count
