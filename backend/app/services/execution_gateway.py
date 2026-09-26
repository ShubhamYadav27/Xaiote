import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.models.actions import (
    ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionPolicy
)
from app.models.execution import ExecutionAttempt, ExecutionAttemptState
from app.services.approval_service import ApprovalDomainService
from app.services.plant_authorization_service import PlantAuthorizationService

class ExecutionGatewayService:
    
    @staticmethod
    def request_execution(
        db: Session, 
        action_id: str, 
        expected_version: int, 
        user_id: str, 
        user_role: str, 
        user_company_id: str
    ) -> ExecutionAttempt:
        try:
            db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            action = db.query(ActionInstance).filter_by(id=action_id).with_for_update().first()
            if not action:
                raise ValueError("Action not found")
                
            if action.company_id != user_company_id:
                raise ValueError("Cross-tenant access denied")
                
            if action.version != expected_version:
                raise ValueError("OCC mismatch: expected_version does not match")
                
            if action.status != ActionLifecycleState.APPROVED.value:
                raise ValueError(f"Terminal or invalid state: {action.status}")
                
            # Authorization Re-Check
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
                    
            policy = db.query(ActionPolicy).filter_by(
                id=action.policy_id, 
                version=action.policy_version, 
                company_id=action.company_id
            ).first()
            if not policy:
                raise ValueError("Bound ActionPolicy not found or invalid")
                
            if not ApprovalDomainService._verify_rbac(user_role, policy.approval_level):
                raise ValueError("Unauthorized role for execution level")
                
            is_fresh, stale_reason = ApprovalDomainService._evaluate_freshness(db, action.id)
            if not is_fresh:
                raise ValueError(f"Stale context: {stale_reason}")
                
            # Check for prior successful execution
            prior_success = db.query(ExecutionAttempt).filter_by(
                action_instance_id=action.id, 
                status=ExecutionAttemptState.SUCCEEDED.value
            ).first()
            if prior_success:
                raise ValueError("Action has already been successfully executed")

            # Determine idempotency key
            idempotency_key = f"{action.company_id}:{action.id}"
            
            attempt = ExecutionAttempt(
                company_id=action.company_id,
                action_instance_id=action.id,
                attempt_number=1,
                downstream_idempotency_key=idempotency_key,
                status=ExecutionAttemptState.PENDING.value,
                provider_type="ERP", # Hardcoded for gateway abstraction
            )
            db.add(attempt)
            
            # Update ActionInstance
            action.status = ActionLifecycleState.EXECUTING.value
            action.version += 1
            
            # Log History
            hist = ActionHistory(
                action_id=action.id,
                company_id=action.company_id,
                previous_state=ActionLifecycleState.APPROVED.value,
                new_state=ActionLifecycleState.EXECUTING.value,
                actor_id=user_id,
                actor_type=ActorType.HUMAN.value,
                reason="Execution requested",
                policy_id=action.policy_id,
                policy_version=action.policy_version,
                action_version=action.version
            )
            db.add(hist)
            db.commit()
            
            return attempt
            
        except OperationalError as e:
            db.rollback()
            if "could not serialize access" in str(e).lower():
                raise ValueError("Serialization conflict: Concurrent mutation detected.") from e
            raise
        except Exception:
            db.rollback()
            raise

