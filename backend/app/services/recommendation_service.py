import hashlib
import json
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from app.models.actions import (
    ActionInstance, ActionHistory, ActionLifecycleState, ActorType, ActionPolicy
)
from app.models.actions import ActionEvidenceLink as Phase5aEvidenceLink
from app.models.recommendations import (
    ActionRecommendation, RecommendationState, RecommendationConversion, RecommendationEvidenceLink
)

class RecommendationDomainService:
    
    @staticmethod
    def compute_context_hash(context: Dict[str, Any]) -> str:
        clean_context = {k: v for k, v in context.items() if k not in ['created_at', 'updated_at', 'deleted_at']}
        serialized = json.dumps(clean_context, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

    @staticmethod
    def supersede_previous_recommendations(db: Session, company_id: str, context_hash: str) -> None:
        """
        Marks any existing PROPOSED or VALIDATED recommendations for the exact identical context as SUPERSEDED,
        as a newer recommendation generation has been requested for this operational state.
        """
        existing = db.query(ActionRecommendation).filter(
            ActionRecommendation.company_id == company_id,
            ActionRecommendation.context_hash == context_hash,
            ActionRecommendation.status.in_([
                RecommendationState.PROPOSED.value,
                RecommendationState.VALIDATED.value
            ])
        ).all()
        
        for rec in existing:
            rec.status = RecommendationState.SUPERSEDED.value
            
        db.commit()

    @staticmethod
    def validate_proposed_candidate(db: Session, recommendation_id: str) -> ActionRecommendation:
        rec = db.query(ActionRecommendation).filter_by(id=recommendation_id).with_for_update().first()
        if not rec or rec.status != RecommendationState.PROPOSED.value:
            raise ValueError("Invalid recommendation for validation")
            
        authoritative_policy = db.query(ActionPolicy).filter_by(
            company_id=rec.company_id,
            name=rec.action_type
        ).order_by(ActionPolicy.version.desc()).first()
        
        if not authoritative_policy:
            rec.status = RecommendationState.REJECTED.value
            rec.stale_reason = "No authorized policy found for action type."
            db.commit()
            return rec
            
        rec.policy_id = authoritative_policy.id
        rec.policy_version = authoritative_policy.version
        
        ev_count = db.query(RecommendationEvidenceLink).filter_by(recommendation_id=rec.id).count()
        if ev_count == 0:
            rec.status = RecommendationState.REJECTED.value
            rec.stale_reason = "Insufficient evidence cardinality."
            db.commit()
            return rec

        rec.status = RecommendationState.VALIDATED.value
        db.commit()
        return rec

    @staticmethod
    def validate_and_convert(
        db: Session, 
        recommendation_id: str, 
        current_context: Dict[str, Any], 
        actor_id: str,
        actor_type: ActorType
    ) -> ActionInstance:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                rec = db.query(ActionRecommendation).filter_by(id=recommendation_id).with_for_update().first()
                if not rec:
                    raise ValueError("Recommendation not found")
                if rec.status != RecommendationState.VALIDATED.value:
                    raise ValueError(f"Recommendation cannot be converted from status {rec.status}")
                    
                fresh_hash = RecommendationDomainService.compute_context_hash(current_context)
                if fresh_hash != rec.context_hash:
                    rec.status = RecommendationState.STALE.value
                    rec.stale_reason = "Context mutated prior to conversion."
                    db.commit()
                    raise ValueError("Stale context: Recommendation aborted and marked STALE.")
                    
                policy = db.query(ActionPolicy).filter_by(
                    id=rec.policy_id, 
                    version=rec.policy_version,
                    company_id=rec.company_id
                ).first()
                
                if not policy:
                    rec.status = RecommendationState.REJECTED.value
                    db.commit()
                    raise ValueError("Policy validation failed.")
                    
                initial_status = ActionLifecycleState.PROPOSED
                
                action = ActionInstance(
                    company_id=rec.company_id,
                    plant_id=rec.plant_id,
                    policy_id=rec.policy_id,
                    policy_version=rec.policy_version,
                    action_type=rec.action_type,
                    target_work_order_id=rec.target_work_order_id,
                    target_machine_id=rec.target_machine_id,
                    target_product_id=rec.target_product_id,
                    status=initial_status.value
                )
                db.add(action)
                db.flush()
                
                if policy.approval_level == 1:
                    next_status = ActionLifecycleState.APPROVED
                else:
                    next_status = ActionLifecycleState.PENDING_APPROVAL
                    
                hist = ActionHistory(
                    action_id=action.id,
                    company_id=action.company_id,
                    previous_state=initial_status.value,
                    new_state=next_status.value,
                    actor_id=actor_id,
                    actor_type=actor_type.value,
                    reason="Converted from Recommendation",
                    policy_id=action.policy_id,
                    policy_version=action.policy_version,
                    action_version=action.version
                )
                db.add(hist)
                
                action.status = next_status.value
                action.version += 1
                
                evidences = db.query(RecommendationEvidenceLink).filter_by(recommendation_id=rec.id).all()
                if not evidences:
                    raise ValueError("Insufficient evidence cardinality")
                    
                for ev in evidences:
                    a_ev = Phase5aEvidenceLink(
                        action_instance_id=action.id,
                        company_id=action.company_id,
                        evidence_alert_id=ev.evidence_alert_id,
                        evidence_risk_history_id=ev.evidence_risk_history_id,
                        evidence_root_cause_assessment_id=ev.evidence_root_cause_assessment_id,
                        evidence_manufacturing_event_id=ev.evidence_manufacturing_event_id
                    )
                    db.add(a_ev)
                    
                idempotency_key = hashlib.sha256(f"{rec.id}:{rec.policy_version}:{rec.company_id}".encode()).hexdigest()
                
                conv = RecommendationConversion(
                    company_id=rec.company_id,
                    recommendation_id=rec.id,
                    action_instance_id=action.id,
                    conversion_idempotency_key=idempotency_key
                )
                db.add(conv)
                rec.status = RecommendationState.CONVERTED.value
                return action
                
            except OperationalError as e:
                db.rollback()
                if "could not serialize access" in str(e).lower() and attempt < max_retries - 1:
                    continue
                raise ValueError("Serialization conflict during conversion") from e
            except Exception:
                raise

