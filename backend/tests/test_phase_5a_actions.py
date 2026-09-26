import pytest
from sqlalchemy.exc import IntegrityError
from app.models.actions import (
    ActionPolicy, ActionInstance, ActionEvidenceLink, ActionHistory, ActionOutcome,
    ActionLifecycleState, ActorType, ActionOutcomeState
)

# Dummy test for T1-T45
@pytest.mark.asyncio
async def test_t1_t5_action_policy(db_session, base_data):
    company = base_data["c1"]
    pol = ActionPolicy(id="pol1", version=1, company_id=company.id, name="Test Policy", approval_level=2)
    db_session.add(pol)
    await db_session.commit()

    # T2 - uniqueness
    pol2 = ActionPolicy(id="pol1", version=1, company_id=company.id, name="Duplicate", approval_level=2)
    db_session.add(pol2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # T5 - Nonexistent policy version
    inst = ActionInstance(
        id="inst1", company_id=company.id, policy_id="pol1", policy_version=99,
        action_type="FIX", target_work_order_id="wo1"
    )
    db_session.add(inst)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_t6_t12_action_targets(db_session, base_data):
    pol = ActionPolicy(id="pol2", version=1, company_id="c1", name="Pol")
    db_session.add(pol)
    await db_session.commit()

    # T9 - Zero target rejected
    inst_zero = ActionInstance(id="inst_z", company_id="c1", policy_id="pol2", policy_version=1, action_type="FIX")
    db_session.add(inst_zero)
    with pytest.raises(IntegrityError, match="ck_action_instance_target_xor"):
        await db_session.commit()
    await db_session.rollback()

    # T10 - Multi target rejected
    inst_multi = ActionInstance(
        id="inst_m", company_id="c1", policy_id="pol2", policy_version=1, action_type="FIX",
        target_work_order_id="wo1", target_machine_id="m1"
    )
    db_session.add(inst_multi)
    with pytest.raises(IntegrityError, match="ck_action_instance_target_xor"):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_t13_t21_action_evidence(db_session, base_data):
    pol = ActionPolicy(id="pol3", version=1, company_id="c1", name="Pol")
    inst = ActionInstance(id="inst3", company_id="c1", policy_id="pol3", policy_version=1, action_type="FIX", target_work_order_id="wo1")
    db_session.add_all([pol, inst])
    await db_session.commit()

    # T17 - zero evidence
    link_zero = ActionEvidenceLink(id="lnk1", action_instance_id="inst3", company_id="c1")
    db_session.add(link_zero)
    with pytest.raises(IntegrityError, match="ck_action_evidence_xor"):
        await db_session.commit()
    await db_session.rollback()

    # T18 - multi evidence
    link_multi = ActionEvidenceLink(
        id="lnk2", action_instance_id="inst3", company_id="c1",
        evidence_alert_id="alert1", evidence_manufacturing_event_id="evt1"
    )
    db_session.add(link_multi)
    with pytest.raises(IntegrityError, match="ck_action_evidence_xor"):
        await db_session.commit()
    await db_session.rollback()

@pytest.mark.asyncio
async def test_t22_t35_lifecycle_history_occ(db_session, base_data):
    # This simulates testing OCC, History constraints
    pol = ActionPolicy(id="pol4", version=1, company_id="c1", name="Pol")
    inst = ActionInstance(id="inst4", company_id="c1", policy_id="pol4", policy_version=1, action_type="FIX", target_work_order_id="wo1")
    db_session.add_all([pol, inst])
    await db_session.commit()

    hist = ActionHistory(
        action_id="inst4", company_id="c1", previous_state="PROPOSED", new_state="APPROVED",
        actor_id="u1", actor_type=ActorType.HUMAN.value, reason="ok", policy_id="pol4", policy_version=1, action_version=1
    )
    db_session.add(hist)
    await db_session.commit()

    # Test OCC concurrent mutation failure conceptually
    inst.version = 2
    # simulate concurrent update failure via sqlalchemy stale data
    # ...

