from sqlalchemy import event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.actions import (
    ActionInstance, ActionEvidenceLink, ActionHistory, ActionLifecycleState, ActorType
)
from app.models.work_order import WorkOrder
from app.models.masters import Machine, Product
from app.models.alerts import AlertInstance
from app.models.risk import WorkOrderRiskHistory
from app.models.analysis import RootCauseAssessment
from app.models.manufacturing_event import ManufacturingEvent

def prevent_update(mapper, connection, target):
    raise ValueError("Update prohibited: append-only table")

def prevent_delete(mapper, connection, target):
    raise ValueError("Delete prohibited: append-only table")

event.listen(ActionEvidenceLink, 'before_update', prevent_update)
event.listen(ActionEvidenceLink, 'before_delete', prevent_delete)
event.listen(ActionHistory, 'before_update', prevent_update)
event.listen(ActionHistory, 'before_delete', prevent_delete)

class ActionDomainService:
    @staticmethod
    def create_action(
        db: Session, company_id: str, policy_id: str, policy_version: int, action_type: str, 
        target_kwargs: dict, user_plant_id: str = None
    ) -> ActionInstance:
        # Cross-tenant and plant integrity validation
        wo_id = target_kwargs.get('target_work_order_id')
        mac_id = target_kwargs.get('target_machine_id')
        prod_id = target_kwargs.get('target_product_id')
        
        target_plant = None
        if wo_id:
            wo = db.query(WorkOrder).filter_by(id=wo_id).first()
            if wo and wo.company_id != company_id:
                raise ValueError("Cross-tenant target rejected")
            if wo: target_plant = wo.plant_id
        if mac_id:
            mac = db.query(Machine).filter_by(id=mac_id).first()
            if mac and mac.company_id != company_id:
                raise ValueError("Cross-tenant target rejected")
            if mac: target_plant = mac.plant_id
        if prod_id:
            prod = db.query(Product).filter_by(id=prod_id).first()
            if prod and prod.company_id != company_id:
                raise ValueError("Cross-tenant target rejected")
                
        if user_plant_id and target_plant and user_plant_id != target_plant:
            raise ValueError("Unauthorized plant access rejected")

        action = ActionInstance(
            company_id=company_id,
            plant_id=target_plant,
            policy_id=policy_id,
            policy_version=policy_version,
            action_type=action_type,
            **target_kwargs
        )
        db.add(action)
        return action

    @staticmethod
    def add_evidence(db: Session, action: ActionInstance, evidence_kwargs: dict):
        # Tenant integrity validation
        for k, v in evidence_kwargs.items():
            if not v: continue
            model = None
            if k == 'evidence_alert_id': model = AlertInstance
            elif k == 'evidence_risk_history_id': model = WorkOrderRiskHistory
            elif k == 'evidence_root_cause_assessment_id': model = RootCauseAssessment
            elif k == 'evidence_manufacturing_event_id': model = ManufacturingEvent
            
            if model:
                rec = db.query(model).filter_by(id=v).first()
                if rec and rec.company_id != action.company_id:
                    raise ValueError("Cross-tenant evidence rejected")
                    
        link = ActionEvidenceLink(
            action_instance_id=action.id,
            company_id=action.company_id,
            **evidence_kwargs
        )
        db.add(link)
        return link

    @staticmethod
    def transition_action(
        db: Session, action: ActionInstance, expected_version: int, new_state: ActionLifecycleState, 
        actor_id: str, actor_type: ActorType, reason: str = None
    ):
        if action.version != expected_version:
            raise ValueError("Stale OCC version")

        # Lifecycle constraints
        allowed = {
            ActionLifecycleState.PROPOSED: [ActionLifecycleState.PENDING_APPROVAL, ActionLifecycleState.APPROVED],
            ActionLifecycleState.PENDING_APPROVAL: [ActionLifecycleState.APPROVED, ActionLifecycleState.REJECTED],
            ActionLifecycleState.APPROVED: [ActionLifecycleState.EXECUTING],
            ActionLifecycleState.EXECUTING: [ActionLifecycleState.COMPLETED, ActionLifecycleState.FAILED],
            ActionLifecycleState.FAILED: [ActionLifecycleState.EXECUTING]
        }
        
        current = ActionLifecycleState(action.status)
        if current in [ActionLifecycleState.REJECTED, ActionLifecycleState.COMPLETED]:
            raise ValueError(f"Terminal state {current.value} is immutable")
            
        if new_state not in allowed.get(current, []):
            raise ValueError(f"Invalid transition from {current.value} to {new_state.value}")

        hist = ActionHistory(
            action_id=action.id,
            company_id=action.company_id,
            previous_state=action.status,
            new_state=new_state.value,
            actor_id=actor_id,
            actor_type=actor_type.value,
            reason=reason,
            policy_id=action.policy_id,
            policy_version=action.policy_version,
            action_version=action.version
        )
        db.add(hist)
        
        # Atomic OCC update
        result = db.query(ActionInstance).filter(
            ActionInstance.id == action.id, 
            ActionInstance.version == expected_version
        ).update({
            "status": new_state.value,
            "version": action.version + 1
        })
        
        if result == 0:
            raise ValueError("Stale OCC version")
            
        # Keep in-memory object in sync for ORM flush
        action.status = new_state.value
        action.version += 1
