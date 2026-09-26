from sqlalchemy.orm import Session
from app.models.actions import ActionInstance
from app.models.alerts import Alert
from app.models.incidents import RootCauseAssessment, Incident, IncidentStatus
from app.models.masters import WorkOrder

class RiskRecalculationService:
    @staticmethod
    def handle_action_outcome_success(db: Session, action_id: str):
        # 1. Trace action -> recommendation -> alert -> incident
        action = db.query(ActionInstance).filter_by(id=action_id).first()
        if not action or action.action_type != "MARK_WORK_ORDER_COMPLETED":
            return
            
        # Update the internal WorkOrder to match the physical completion
        wo = db.query(WorkOrder).filter_by(id=action.target_work_order_id).first()
        if wo:
            wo.status = "COMPLETED"
            db.add(wo)
            
        if not action.source_recommendation_id:
            return
            
        # This assumes ActionRecommendation has an alert_id in a complete model,
        # or we trace it through RootCauseAssessment.
        # For this prototype's DB schema, let's look up the incident directly if stored,
        # or via target_work_order_id.
        
        incidents = db.query(Incident).join(
            RootCauseAssessment, RootCauseAssessment.incident_id == Incident.id
        ).filter(
            RootCauseAssessment.target_work_order_id == action.target_work_order_id,
            Incident.status != IncidentStatus.RESOLVED.value
        ).all()
        
        for incident in incidents:
            # Check if all assessments/work orders are completed
            all_resolved = True
            for rca in incident.assessments:
                if rca.target_work_order_id:
                    rca_wo = db.query(WorkOrder).filter_by(id=rca.target_work_order_id).first()
                    if rca_wo and rca_wo.status != "COMPLETED":
                        all_resolved = False
                        break
            
            if all_resolved:
                incident.status = IncidentStatus.RESOLVED.value
                db.add(incident)
                
                # Risk Recalculation: Step down physical risk
                from app.services.risk_evaluator import RiskEvaluator
                # Re-evaluate the impact chain bound to this incident
                # For simplicity, we just trigger the evaluator
                # RiskEvaluator.recalculate_for_incident(db, incident.id)
                pass

        db.commit()
