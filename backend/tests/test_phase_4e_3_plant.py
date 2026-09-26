import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alerts import AlertInstance, AlertPolicy, AlertRule, AlertStatus
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.risk import RiskState
from app.models.user import User
from app.models.work_order import WorkOrder
from app.services.alert_lifecycle import transition_alert_status


@pytest.fixture
async def base_context(db_session: AsyncSession):
    c1 = Company(id="c1_ev_plt", name="C1")
    p1 = Plant(id="p1_ev_plt", company_id="c1_ev_plt", name="P1", timezone="UTC")
    db_session.add_all([c1, p1])
    await db_session.commit()
    prod = Product(id="prod1_ev_plt", company_id="c1_ev_plt", name="P")
    mach = Machine(id="mach1_ev_plt", company_id="c1_ev_plt", plant_id="p1_ev_plt", name="M")
    db_session.add_all([prod, mach])
    await db_session.commit()
    user = User(id="user1", company_id="c1_ev_plt", email="user1@example.com", password_hash="pw", full_name="User", is_active=True, role="SUPERVISOR")
    wo1 = WorkOrder(id="wo1_ev_plt", company_id="c1_ev_plt", plant_id="p1_ev_plt", order_number="W1", status="PENDING", product_id="prod1_ev_plt", machine_id="mach1_ev_plt", quantity=100.0)
    pol = AlertPolicy(id="pol1_ev", company_id="c1_ev_plt", version=1, name="Pol1")
    rules = [
        AlertRule(id="rule1_ev_risk", company_id="c1_ev_plt", version=1, policy_id="pol1_ev", policy_version=1,
                  alert_family="PRODUCTION_RISK", severity=RiskState.AT_RISK.value, trigger_condition={}, clear_condition={})
    ]
    db_session.add_all([wo1, pol, user] + rules)
    await db_session.commit()
    return {"wo1": wo1}

@pytest.mark.asyncio
async def test_t8_cross_plant_authorization(db_session, base_context):
    wo1 = base_context["wo1"]
    p2 = Plant(id="plant_b", company_id=wo1.company_id, name="PB", timezone="UTC")
    db_session.add(p2)
    await db_session.commit()
    alert = AlertInstance(
        id="alert_plant_b",
        company_id=wo1.company_id,
        plant_id="plant_b",
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
    
    # Try with wrong plant
    with pytest.raises(HTTPException) as exc:
        await transition_alert_status(db_session, alert.id, wo1.company_id, "user1", AlertStatus.ACKNOWLEDGED, 1, user_plant_id="plant_a")
    assert exc.value.status_code == 404
    
    # Try with correct plant
    res = await transition_alert_status(db_session, alert.id, wo1.company_id, "user1", AlertStatus.ACKNOWLEDGED, 1, user_plant_id="plant_b")
    assert res.status == AlertStatus.ACKNOWLEDGED.value

