import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models.actions import (
    ActionPolicy, ActionInstance, ActionEvidenceLink, ActionHistory, ActionOutcome,
    ActionLifecycleState, ActorType, ActionOutcomeState
)
from app.models.company import Company
from app.models.plant import Plant
from app.models.masters import Machine
from app.models.work_order import WorkOrder
from app.models.alerts import AlertInstance
from app.services.action_service import ActionDomainService

@pytest.fixture
def mock_tenant_data(db_session: Session):
    c1 = Company(id="c1", name="C1")
    c2 = Company(id="c2", name="C2")
    p1 = Plant(id="p1", company_id="c1", name="P1", timezone="UTC")
    p2 = Plant(id="p2", company_id="c1", name="P2", timezone="UTC")
    db_session.add_all([c1, c2, p1, p2])
    db_session.commit()
    
    m1 = Machine(id="m1", company_id="c1", plant_id="p1", name="M1")
    m2 = Machine(id="m2", company_id="c2", plant_id="p2", name="M2") # M2 belongs to C2
    wo1 = WorkOrder(id="wo1", company_id="c1", plant_id="p1", status="PENDING")
    
    pol = ActionPolicy(id="pol1", version=1, company_id="c1", name="Pol")
    db_session.add_all([m1, m2, wo1, pol])
    db_session.commit()
    
    a1 = AlertInstance(id="a1", company_id="c2", plant_id="p2", status="ACTIVE", severity="AT_RISK", alert_family="f1", target_work_order_id="wo1")
    db_session.add(a1)
    db_session.commit()
    
    return {"c1": "c1", "c2": "c2", "p1": "p1", "p2": "p2", "m1": "m1", "m2": "m2", "wo1": "wo1", "a1": "a1", "pol": pol}

def test_tenant_plant_integrity(db_session, mock_tenant_data):
    # Case A: Tenant A action + Tenant B WorkOrder (mock with machine here)
    with pytest.raises(ValueError, match="Cross-tenant target rejected"):
        ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m2"})
        
    # Case D: Authorized plant A context + Plant B target
    with pytest.raises(ValueError, match="Unauthorized plant access rejected"):
        ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"}, user_plant_id="p2")

def test_evidence_tenant_integrity(db_session, mock_tenant_data):
    action = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    
    # Case C: Tenant A action + Tenant B evidence (a1 is c2)
    with pytest.raises(ValueError, match="Cross-tenant evidence rejected"):
        ActionDomainService.add_evidence(db_session, action, {"evidence_alert_id": "a1"})

def test_lifecycle_semantics(db_session, mock_tenant_data):
    action = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    
    # 1. PROPOSED -> PENDING_APPROVAL succeeds
    ActionDomainService.transition_action(db_session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
    db_session.commit()
    assert action.status == ActionLifecycleState.PENDING_APPROVAL.value
    
    # 2. PENDING_APPROVAL -> APPROVED succeeds
    ActionDomainService.transition_action(db_session, action, 2, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)
    db_session.commit()
    
    # 9. APPROVED -> REJECTED fails
    with pytest.raises(ValueError, match="Invalid transition"):
        ActionDomainService.transition_action(db_session, action, 3, ActionLifecycleState.REJECTED, "u1", ActorType.HUMAN)
        
    # 3. PENDING_APPROVAL -> REJECTED succeeds
    action2 = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    ActionDomainService.transition_action(db_session, action2, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
    ActionDomainService.transition_action(db_session, action2, 2, ActionLifecycleState.REJECTED, "u1", ActorType.HUMAN)
    db_session.commit()
    
    # 4. REJECTED -> APPROVED fails
    with pytest.raises(ValueError, match="Terminal state REJECTED is immutable"):
        ActionDomainService.transition_action(db_session, action2, 3, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)

def test_occ_concurrency(db_session, mock_tenant_data):
    action = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    
    # Initial version = 1
    assert action.version == 1
    
    # Writer A: expected_version = 1 -> succeeds
    ActionDomainService.transition_action(db_session, action, 1, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)
    db_session.commit()
    assert action.version == 2
    
    # Writer B: expected_version = 1 -> rejected
    with pytest.raises(ValueError, match="Stale OCC version"):
        ActionDomainService.transition_action(db_session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u2", ActorType.HUMAN)
    
def test_append_only_integrity(db_session, mock_tenant_data):
    action = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    ActionDomainService.transition_action(db_session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
    db_session.commit()
    
    hist = db_session.query(ActionHistory).filter_by(action_id=action.id).first()
    
    # Try UPDATE
    hist.reason = "Modified"
    with pytest.raises(ValueError, match="Update prohibited: append-only table"):
        db_session.commit()
    db_session.rollback()
    
    # Try DELETE
    hist = db_session.query(ActionHistory).filter_by(action_id=action.id).first()
    db_session.delete(hist)
    with pytest.raises(ValueError, match="Delete prohibited: append-only table"):
        db_session.commit()
    db_session.rollback()

def test_level1_lifecycle_semantics(db_session, mock_tenant_data):
    action = ActionDomainService.create_action(db_session, "c1", "pol1", 1, "FIX", {"target_machine_id": "m1"})
    db_session.commit()
    
    # 1. Succeeds
    ActionDomainService.transition_action(db_session, action, 1, ActionLifecycleState.APPROVED, "sys", ActorType.SYSTEM)
    db_session.commit()
    
    assert action.status == ActionLifecycleState.APPROVED.value
    
    # 2. Increment OCC version exactly once
    assert action.version == 2
    
    # 3. Produce exactly one ActionHistory record
    hist_records = db_session.query(ActionHistory).filter_by(action_id=action.id).all()
    assert len(hist_records) == 1
    
    hist = hist_records[0]
    assert hist.previous_state == ActionLifecycleState.PROPOSED.value
    assert hist.new_state == ActionLifecycleState.APPROVED.value
    
    # 5. Preserve exact policy identity
    assert hist.policy_id == "pol1"
    assert hist.policy_version == 1

