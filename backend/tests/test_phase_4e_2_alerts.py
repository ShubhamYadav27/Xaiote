import pytest
from sqlalchemy.exc import IntegrityError

from app.models.alerts import (
    AlertEvidenceLink,
    AlertHistory,
    AlertInstance,
    AlertPolicy,
    AlertRule,
    AlertSeverity,
    AlertStatus,
)
from app.models.company import Company
from app.models.incident import Incident
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState, RiskTriggerType, WorkOrderRiskHistory
from app.models.work_order import WorkOrder


@pytest.fixture
async def base_data(db_session):
    c1 = Company(id="c1", name="C1")
    c2 = Company(id="c2", name="C2")
    db_session.add_all([c1, c2])
    await db_session.commit()

    p1 = Plant(id="p1", company_id="c1", name="P1", timezone="UTC")
    db_session.add(p1)
    await db_session.commit()

    prod = Product(id="prod1", company_id="c1", name="P")
    mach = Machine(id="mach1", company_id="c1", plant_id="p1", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()

    wo = WorkOrder(
        id="wo1",
        company_id="c1",
        plant_id="p1",
        product_id="prod1",
        machine_id="mach1",
        order_number="WO-001",
        quantity=100.0,
        status="PENDING",
    )
    inc = Incident(
        id="inc1", company_id="c1", plant_id="p1", title="I1", status="ACTIVE"
    )
    db_session.add_all([wo, inc])

    pol = AlertPolicy(id="pol1", company_id="c1", version=1, name="P1")
    pol_v2 = AlertPolicy(id="pol1", company_id="c1", version=2, name="P1")
    pol_c2 = AlertPolicy(id="pol_c2", company_id="c2", version=1, name="P2")

    rule = AlertRule(
        id="rul1",
        company_id="c1",
        version=1,
        policy_id="pol1",
        policy_version=1,
        alert_family="fam",
        severity=AlertSeverity.AT_RISK,
        trigger_condition={},
        clear_condition={},
    )
    rule_v2 = AlertRule(
        id="rul1",
        company_id="c1",
        version=2,
        policy_id="pol1",
        policy_version=2,
        alert_family="fam",
        severity=AlertSeverity.CRITICAL,
        trigger_condition={},
        clear_condition={},
    )
    db_session.add_all([pol, pol_v2, pol_c2, rule, rule_v2])
    await db_session.commit()

    risk = WorkOrderRiskHistory(
        id="risk1",
        company_id="c1",
        work_order_id="wo1",
        previous_state=RiskState.ON_TRACK,
        new_state=RiskState.AT_RISK,
        trigger_type=next(iter(RiskTriggerType)),
    )
    db_session.add(risk)
    await db_session.commit()
    return {
        "c1": c1,
        "c2": c2,
        "p1": p1,
        "wo": wo,
        "inc": inc,
        "pol": pol,
        "rule": rule,
        "rule_v2": rule_v2,
        "risk": risk,
    }


@pytest.mark.asyncio
async def test_t17_exactly_one_evidence(db_session, base_data):
    inst = AlertInstance(
        id="inst1",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid
    ev1 = AlertEvidenceLink(
        id="ev1",
        alert_instance_id="inst1",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev1)
    await db_session.commit()

    # Zero targets -> Fail
    ev2 = AlertEvidenceLink(id="ev2", alert_instance_id="inst1", company_id="c1")
    db_session.add(ev2)
    with pytest.raises(IntegrityError, match="ck_alert_evidence_xor"):
        await db_session.commit()
    await db_session.rollback()

    
    # Multiple targets -> Fail
    ev3 = AlertEvidenceLink(id="ev3", alert_instance_id="inst1", company_id="c1", evidence_risk_history_id="risk1", evidence_production_order_impact_id="dummy_impact")
    db_session.add(ev3)
    with pytest.raises(IntegrityError, match="ck_alert_evidence_xor"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t20_alert_target_cardinality(db_session, base_data):
    inst1 = AlertInstance(
        id="inst1",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id=None,
        target_incident_id=None,
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst1)
    with pytest.raises(IntegrityError, match="ck_alert_instance_target_xor"):
        await db_session.commit()
    await db_session.rollback()

    inst2 = AlertInstance(
        id="inst2",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        target_incident_id="inc1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError, match="ck_alert_instance_target_xor"):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_t23_t24_referential_integrity(db_session, base_data):
    # Rule referencing nonexistent policy version
    r1 = AlertRule(
        id="r2",
        company_id="c1",
        version=1,
        policy_id="pol1",
        policy_version=999,
        alert_family="fam",
        severity=AlertSeverity.AT_RISK,
        trigger_condition={},
        clear_condition={},
    )
    db_session.add(r1)
    with pytest.raises(IntegrityError, match="fk_alert_rule_policy"):
        await db_session.commit()
    await db_session.rollback()

    # Rule referencing cross-tenant policy
    r2 = AlertRule(
        id="r2",
        company_id="c1",
        version=1,
        policy_id="pol_c2",
        policy_version=1,
        alert_family="fam",
        severity=AlertSeverity.AT_RISK,
        trigger_condition={},
        clear_condition={},
    )
    db_session.add(r2)
    with pytest.raises(IntegrityError, match="fk_alert_rule_policy"):
        await db_session.commit()
    await db_session.rollback()

    # Instance referencing cross-tenant rule
    inst = AlertInstance(
        id="inst1",
        company_id="c2",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_t18_historical_provenance(db_session, base_data):
    # Valid instantiation and history persistence
    inst = AlertInstance(
        id="inst_hist",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    hist = AlertHistory(
        id="hist1",
        alert_instance_id="inst_hist",
        company_id="c1",
        action="ESCALATED",
        previous_severity=AlertSeverity.AT_RISK,
        new_severity=AlertSeverity.CRITICAL,
        previous_policy_id="pol1",
        previous_policy_version=1,
        previous_rule_id="rul1",
        previous_rule_version=1,
        new_policy_id="pol1",
        new_policy_version=2,
        new_rule_id="rul1",
        new_rule_version=2,
    )
    db_session.add(hist)
    await db_session.commit()

    # Now update current to V2
    inst.current_policy_version = 2
    inst.current_rule_version = 2
    inst.severity = AlertSeverity.CRITICAL
    await db_session.commit()


@pytest.mark.asyncio
async def test_deduplication_index(db_session, base_data):
    inst1 = AlertInstance(
        id="dedup1",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst1)
    await db_session.commit()

    inst2 = AlertInstance(
        id="dedup2",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst2)
    with pytest.raises(IntegrityError, match="ix_alert_instances_dedup_wo"):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()



@pytest.mark.asyncio
async def test_t9_alert_evidence_integrity(db_session, base_data):
    inst = AlertInstance(
        id="inst_t9",
        company_id="c1",
        plant_id="p1",
        alert_family="fam",
        target_work_order_id="wo1",
        originating_policy_id="pol1",
        originating_policy_version=1,
        originating_rule_id="rul1",
        originating_rule_version=1,
        current_policy_id="pol1",
        current_policy_version=1,
        current_rule_id="rul1",
        current_rule_version=1,
        status=AlertStatus.ACTIVE,
        severity=AlertSeverity.AT_RISK,
    )
    db_session.add(inst)
    await db_session.commit()

    # Valid evidence reference
    ev_valid = AlertEvidenceLink(
        id="ev_t9_valid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="risk1",
    )
    db_session.add(ev_valid)
    await db_session.commit()

    # Invalid evidence reference -> Foreign Key Violation
    ev_invalid = AlertEvidenceLink(
        id="ev_t9_invalid",
        alert_instance_id="inst_t9",
        company_id="c1",
        evidence_risk_history_id="nonexistent_risk",
    )
    db_session.add(ev_invalid)
    with pytest.raises(IntegrityError, match="alert_evidence_links_evidence_risk_history_id_fkey"):
        await db_session.commit()
    await db_session.rollback()

