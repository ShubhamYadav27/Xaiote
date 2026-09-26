import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import AlertPolicy, AlertRule
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState
from app.models.user import User
from app.models.work_order import WorkOrder


@pytest.fixture
async def base_context(db_session: AsyncSession):
    c1 = Company(id="c1_ev_l", name="C1")
    p1 = Plant(id="p1_ev_l", company_id="c1_ev_l", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev_l", company_id="c1_ev_l", name="P")
    mach = Machine(id="mach1_ev_l", company_id="c1_ev_l", plant_id="p1_ev_l", name="M")
    db_session.add_all([prod, mach])
    user = User(id="user1", company_id="c1_ev_l", email="user1@example.com", password_hash="pw", full_name="User1", is_active=True, role="SUPERVISOR")
    db_session.add(user)
    await db_session.commit()

    wo1 = WorkOrder(product_id="prod1_ev_l", machine_id="mach1_ev_l", quantity=100.0, id="wo1_ev_l", company_id="c1_ev_l", plant_id="p1_ev_l", order_number="W1", status="PENDING")
    db_session.add(wo1)
    
    pol = AlertPolicy(id="pol1_ev", company_id="c1_ev_l", version=1, name="Pol1")
    rules = [
        AlertRule(id="rule1_ev_risk", company_id="c1_ev_l", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.AT_RISK.value, trigger_condition={}, clear_condition={})
    ]
    db_session.add(pol)
    db_session.add_all(rules)
    await db_session.commit()
    return {"wo1": wo1}

import pytest
from fastapi import HTTPException

from app.models.alerts import AlertInstance, AlertStatus
from app.services.alert_lifecycle import transition_alert_status


@pytest.mark.asyncio
async def test_t6_occ_conflict(db_session, base_context):
    wo1 = base_context["wo1"]
    alert = AlertInstance(
        id="alert_occ",
        company_id=wo1.company_id,
        plant_id=wo1.plant_id,
        alert_family="PRODUCTION_RISK",
        target_work_order_id=wo1.id,
        originating_policy_id="pol1_ev",
        originating_policy_version=1,
        originating_rule_id="rule1_ev_risk",
        originating_rule_version=1,
        current_policy_id="pol1_ev",
        current_policy_version=1,
        current_rule_id="rule1_ev_risk",
        current_rule_version=1,
        status=AlertStatus.ACTIVE.value,
        severity="AT_RISK",
        version=1
    )
    db_session.add(alert)
    await db_session.commit()
    
    # Try with wrong version
    with pytest.raises(HTTPException) as exc:
        await transition_alert_status(db_session, alert.id, wo1.company_id, "user1", AlertStatus.ACKNOWLEDGED, 2)
    assert exc.value.status_code == 409
    
    # Correct version
    res = await transition_alert_status(db_session, alert.id, wo1.company_id, "user1", AlertStatus.ACKNOWLEDGED, 1)
    await db_session.commit()
    assert res.status == AlertStatus.ACKNOWLEDGED.value
    assert res.version == 2

