import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.actions import (
    ActionPolicy, ActionInstance, ActionEvidenceLink, ActionHistory, ActionOutcome,
    ActionLifecycleState, ActorType, ActionOutcomeState
)
from app.models.company import Company
from app.models.plant import Plant
from app.models.masters import Machine, Product
from app.models.work_order import WorkOrder
from app.models.alerts import AlertInstance, AlertPolicy, AlertRule
from app.services.action_service import ActionDomainService

@pytest.fixture
async def mock_tenant_data(db_session: AsyncSession):
    import uuid
    s = uuid.uuid4().hex[:8]

    def _setup(session):
        c1 = Company(id=f"c1_{s}", name="C1")
        c2 = Company(id=f"c2_{s}", name="C2")
        p1 = Plant(id=f"p1_{s}", company_id=f"c1_{s}", name="P1", timezone="UTC")
        p2 = Plant(id=f"p2_{s}", company_id=f"c1_{s}", name="P2", timezone="UTC")
        session.add_all([c1, c2, p1, p2])
        session.commit()
        
        prod1 = Product(id=f"prod1_{s}", company_id=f"c1_{s}", name="Prod1")
        pol1_alert = AlertPolicy(id=f"pol1_alert_{s}", version=1, company_id=f"c1_{s}", name="AlertPol")
        rule1_alert = AlertRule(id=f"rule1_{s}", version=1, company_id=f"c1_{s}", policy_id=f"pol1_alert_{s}", policy_version=1, alert_family="f1", trigger_condition={}, clear_condition={}, severity="AT_RISK")
        pol2_alert = AlertPolicy(id=f"pol2_alert_{s}", version=1, company_id=f"c2_{s}", name="AlertPol2")
        rule2_alert = AlertRule(id=f"rule2_{s}", version=1, company_id=f"c2_{s}", policy_id=f"pol2_alert_{s}", policy_version=1, alert_family="f1", trigger_condition={}, clear_condition={}, severity="AT_RISK")
        session.add_all([prod1, pol1_alert, rule1_alert, pol2_alert, rule2_alert])
        session.commit()
        
        m1 = Machine(id=f"m1_{s}", company_id=f"c1_{s}", plant_id=f"p1_{s}", name="M1")
        m2 = Machine(id=f"m2_{s}", company_id=f"c2_{s}", plant_id=f"p2_{s}", name="M2")
        session.add_all([m1, m2])
        session.commit()
        
        wo1 = WorkOrder(id=f"wo1_{s}", company_id=f"c1_{s}", plant_id=f"p1_{s}", product_id=f"prod1_{s}", order_number="WO-123", quantity=100.0, status="PENDING")
        pol = ActionPolicy(id=f"pol1_{s}", version=1, company_id=f"c1_{s}", name="Pol", approval_level=1)
        session.add_all([wo1, pol])
        session.commit()
        
        a1 = AlertInstance(id=f"a1_{s}", company_id=f"c2_{s}", plant_id=f"p2_{s}", status="ACTIVE", severity="AT_RISK", alert_family="f1", target_work_order_id=f"wo1_{s}", originating_policy_id=f"pol2_alert_{s}", originating_policy_version=1, originating_rule_id=f"rule2_{s}", originating_rule_version=1, current_policy_id=f"pol2_alert_{s}", current_policy_version=1, current_rule_id=f"rule2_{s}", current_rule_version=1)
        session.add(a1)
        session.commit()

    await db_session.run_sync(_setup)
    
    return {
        "c1": f"c1_{s}", "c2": f"c2_{s}", "p1": f"p1_{s}", "p2": f"p2_{s}",
        "m1": f"m1_{s}", "m2": f"m2_{s}", "wo1": f"wo1_{s}", "a1": f"a1_{s}",
        "pol1": f"pol1_{s}", "pol": f"pol1_{s}"
    }


@pytest.mark.asyncio
async def test_tenant_plant_integrity(db_session, mock_tenant_data):
    def _test(session):    
        # Case A: Tenant A action + Tenant B WorkOrder (mock with machine here)
        with pytest.raises(ValueError, match="Cross-tenant target rejected"):
            ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m2"]})
            
        # Case D: Authorized plant A context + Plant B target
        with pytest.raises(ValueError, match="Unauthorized plant access rejected"):
            ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]}, user_plant_id=mock_tenant_data["p2"])
    
    await db_session.run_sync(_test)
@pytest.mark.asyncio
async def test_evidence_tenant_integrity(db_session, mock_tenant_data):
    def _test(session):    
        action = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        
        # Case C: Tenant A action + Tenant B evidence (a1 is c2)
        with pytest.raises(ValueError, match="Cross-tenant evidence rejected"):
            ActionDomainService.add_evidence(session, action, {"evidence_alert_id": mock_tenant_data["a1"]})
    
    await db_session.run_sync(_test)
@pytest.mark.asyncio
async def test_lifecycle_semantics(db_session, mock_tenant_data):
    def _test(session):    
        action = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        
        # 1. PROPOSED -> PENDING_APPROVAL succeeds
        ActionDomainService.transition_action(session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
        session.commit()
        assert action.status == ActionLifecycleState.PENDING_APPROVAL.value
        
        # 2. PENDING_APPROVAL -> APPROVED succeeds
        ActionDomainService.transition_action(session, action, 2, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)
        session.commit()
        
        # 9. APPROVED -> REJECTED fails
        with pytest.raises(ValueError, match="Invalid transition"):
            ActionDomainService.transition_action(session, action, 3, ActionLifecycleState.REJECTED, "u1", ActorType.HUMAN)
            
        # 3. PENDING_APPROVAL -> REJECTED succeeds
        action2 = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        ActionDomainService.transition_action(session, action2, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
        ActionDomainService.transition_action(session, action2, 2, ActionLifecycleState.REJECTED, "u1", ActorType.HUMAN)
        session.commit()
        
        # 4. REJECTED -> APPROVED fails
        with pytest.raises(ValueError, match="Terminal state REJECTED is immutable"):
            ActionDomainService.transition_action(session, action2, 3, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)
    
    await db_session.run_sync(_test)
@pytest.mark.asyncio
async def test_occ_concurrency(db_session, mock_tenant_data):
    def _test(session):    
        action = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        
        # Initial version = 1
        assert action.version == 1
        
        # Writer A: expected_version = 1 -> succeeds
        ActionDomainService.transition_action(session, action, 1, ActionLifecycleState.APPROVED, "u1", ActorType.HUMAN)
        session.commit()
        assert action.version == 2
        
        # Writer B: expected_version = 1 -> rejected
        with pytest.raises(ValueError, match="Stale OCC version"):
            ActionDomainService.transition_action(session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u2", ActorType.HUMAN)
        
    await db_session.run_sync(_test)
@pytest.mark.asyncio
async def test_append_only_integrity(db_session, mock_tenant_data):
    def _test(session):    
        action = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        ActionDomainService.transition_action(session, action, 1, ActionLifecycleState.PENDING_APPROVAL, "u1", ActorType.HUMAN)
        session.commit()
        
        hist = session.query(ActionHistory).filter_by(action_id=action.id).first()
        
        # Try UPDATE
        hist.reason = "Modified"
        with pytest.raises(ValueError, match="Update prohibited: append-only table"):
            session.commit()
        session.rollback()
        
        # Try DELETE
        hist = session.query(ActionHistory).filter_by(action_id=action.id).first()
        session.delete(hist)
        with pytest.raises(ValueError, match="Delete prohibited: append-only table"):
            session.commit()
        session.rollback()
    
    await db_session.run_sync(_test)
@pytest.mark.asyncio
async def test_level1_lifecycle_semantics(db_session, mock_tenant_data):
    def _test(session):    
        action = ActionDomainService.create_action(session, mock_tenant_data["c1"], mock_tenant_data["pol1"], 1, "FIX", {"target_machine_id": mock_tenant_data["m1"]})
        session.commit()
        
        # 1. Succeeds
        ActionDomainService.transition_action(session, action, 1, ActionLifecycleState.APPROVED, "sys", ActorType.SYSTEM)
        session.commit()
        
        assert action.status == ActionLifecycleState.APPROVED.value
        
        # 2. Increment OCC version exactly once
        assert action.version == 2
        
        # 3. Produce exactly one ActionHistory record
        hist_records = session.query(ActionHistory).filter_by(action_id=action.id).all()
        assert len(hist_records) == 1
        
        hist = hist_records[0]
        assert hist.previous_state == ActionLifecycleState.PROPOSED.value
        assert hist.new_state == ActionLifecycleState.APPROVED.value
        
        # 5. Preserve exact policy identity
        assert hist.policy_id == mock_tenant_data["pol1"]
        assert hist.policy_version == 1
    
    
    await db_session.run_sync(_test)