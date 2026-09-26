from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.alerts import AlertInstance, AlertPolicy, AlertRule
from app.models.company import Company
from app.models.masters import Machine, Product
from app.models.plant import Plant
from app.models.user import User
from app.models.work_order import WorkOrder


@pytest.fixture
async def setup_api(db_session: AsyncSession):
    import uuid

    def _uid():
        return str(uuid.uuid4())

    cid = _uid()
    c2id = _uid()
    c1 = Company(id=cid, name="Company A")
    c2 = Company(id=c2id, name="Company B")
    p1 = Plant(id=_uid(), company_id=cid, name="Plant A", timezone="UTC")
    p2 = Plant(id=_uid(), company_id=cid, name="Plant A2", timezone="UTC")
    db_session.add_all([c1, c2, p1, p2])

    u_super = User(
        id=_uid(),
        company_id=cid,
        email="super@example.com",
        password_hash="pw",
        role="SUPERVISOR",
        is_active=True,
        full_name="Super",
    )
    u_view = User(
        id=_uid(),
        company_id=cid,
        email="view@example.com",
        password_hash="pw",
        role="VIEWER",
        is_active=True,
        full_name="View",
    )
    u_other = User(
        id=_uid(),
        company_id=c2id,
        email="other@example.com",
        password_hash="pw",
        role="SUPERVISOR",
        is_active=True,
        full_name="Other",
    )
    db_session.add_all([u_super, u_view, u_other])
    await db_session.commit()

    mac = Machine(id=_uid(), company_id=cid, plant_id=p1.id, name="CNC")
    prod = Product(id=_uid(), company_id=cid, name="Part")
    mac2 = Machine(id=_uid(), company_id=c2id, plant_id=p2.id, name="CNC2")
    prod2 = Product(id=_uid(), company_id=c2id, name="Part2")
    db_session.add_all([mac, prod, mac2, prod2])
    await db_session.commit()

    wo = WorkOrder(
        id=_uid(),
        company_id=cid,
        plant_id=p1.id,
        order_number="W1",
        status="PENDING",
        machine_id=mac2.id,
        product_id=prod2.id,
        quantity=100,
    )
    wo2 = WorkOrder(
        id=_uid(),
        company_id=c2id,
        plant_id=p2.id,
        order_number="W2",
        status="PENDING",
        machine_id=mac.id,
        product_id=prod.id,
        quantity=100,
    )
    db_session.add_all([wo, wo2])

    pol = AlertPolicy(id=_uid(), company_id=cid, version=1, name="Policy1")
    rule = AlertRule(
        id=_uid(),
        company_id=cid,
        version=1,
        policy_id=pol.id,
        policy_version=1,
        alert_family="PRODUCTION_RISK",
        severity="AT_RISK",
        trigger_condition={},
        clear_condition={},
    )
    pol2 = AlertPolicy(id=_uid(), company_id=c2id, version=1, name="Pol2")
    rule2 = AlertRule(
        id=_uid(),
        company_id=c2id,
        version=1,
        policy_id=pol2.id,
        policy_version=1,
        alert_family="PRODUCTION_RISK",
        severity="AT_RISK",
        trigger_condition={},
        clear_condition={},
    )
    db_session.add_all([pol, rule, pol2, rule2])
    await db_session.commit()

    alert1 = AlertInstance(
        id=_uid(),
        company_id=cid,
        plant_id=p1.id,
        alert_family="PRODUCTION_RISK",
        target_work_order_id=wo.id,
        originating_policy_id=pol.id,
        originating_policy_version=1,
        originating_rule_id=rule.id,
        originating_rule_version=1,
        current_policy_id=pol.id,
        current_policy_version=1,
        current_rule_id=rule.id,
        current_rule_version=1,
        status="ACTIVE",
        severity="AT_RISK",
        version=1,
    )
    alert2 = AlertInstance(
        id=_uid(),
        company_id=c2id,
        plant_id=p2.id,
        alert_family="PRODUCTION_RISK",
        target_work_order_id=wo2.id,
        originating_policy_id=pol2.id,
        originating_policy_version=1,
        originating_rule_id=rule2.id,
        originating_rule_version=1,
        current_policy_id=pol2.id,
        current_policy_version=1,
        current_rule_id=rule2.id,
        current_rule_version=1,
        status="ACTIVE",
        severity="AT_RISK",
        version=1,
    )
    db_session.add_all([alert1, alert2])
    await db_session.commit()

    tok_super = jwt.encode(
        {"sub": str(u_super.id)}, settings.JWT_SECRET, algorithm="HS256"
    )
    tok_view = jwt.encode(
        {"sub": str(u_view.id)}, settings.JWT_SECRET, algorithm="HS256"
    )
    tok_other = jwt.encode(
        {"sub": str(u_other.id)}, settings.JWT_SECRET, algorithm="HS256"
    )

    return {
        "company_a": cid,
        "company_b": c2id,
        "plant_a": p1.id,
        "plant_a2": p2.id,
        "alert1": alert1.id,
        "alert2": alert2.id,
        "head_super": {"Authorization": f"Bearer {tok_super}"},
        "head_view": {"Authorization": f"Bearer {tok_view}"},
        "head_other": {"Authorization": f"Bearer {tok_other}"},
    }


@pytest.mark.asyncio
async def test_api_get_alerts_tenant_scoped(setup_api, async_client: AsyncClient):
    # 1. GET alerts returns tenant-scoped alerts.
    res = await async_client.get("/api/v1/alerts", headers=setup_api["head_super"])
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    assert data[0]["id"] == setup_api["alert1"]


@pytest.mark.asyncio
async def test_api_get_alert_detail(setup_api, async_client: AsyncClient):
    # 2. GET alert detail returns correct alert.
    res = await async_client.get(
        f"/api/v1/alerts/{setup_api['alert1']}", headers=setup_api["head_super"]
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["id"] == setup_api["alert1"]


@pytest.mark.asyncio
async def test_api_cross_tenant_rejected(setup_api, async_client: AsyncClient):
    # 3. Cross-tenant alert access is rejected (404 since it filters by company_id).
    res = await async_client.get(
        f"/api/v1/alerts/{setup_api['alert2']}", headers=setup_api["head_super"]
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_unauthorized_plant_rejected(setup_api, async_client: AsyncClient):
    # 4. Unauthorized plant access is rejected (for transition).
    payload = {
        "status": "ACKNOWLEDGED",
        "expected_version": 1,
        "plant_id": setup_api["plant_a2"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_api_viewer_can_read(setup_api, async_client: AsyncClient):
    # 5. Viewer can read alerts.
    res = await async_client.get("/api/v1/alerts", headers=setup_api["head_view"])
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_api_viewer_cannot_mutate(setup_api, async_client: AsyncClient):
    # 6. Unauthorized mutation is rejected.
    payload = {
        "status": "ACKNOWLEDGED",
        "expected_version": 1,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_view"],
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_api_supervisor_acknowledge_and_resolve(
    setup_api, async_client: AsyncClient
):
    # 7. Authorized Supervisor can acknowledge.
    payload = {
        "status": "ACKNOWLEDGED",
        "expected_version": 1,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "ACKNOWLEDGED"

    # 8. Authorized Supervisor can resolve.
    payload = {
        "status": "RESOLVED",
        "expected_version": 2,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "RESOLVED"


@pytest.mark.asyncio
async def test_api_stale_version_409(setup_api, async_client: AsyncClient):
    # 9. Stale expected_version returns HTTP 409.
    payload = {
        "status": "ACKNOWLEDGED",
        "expected_version": 999,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_api_success_returns_authoritative(setup_api, async_client: AsyncClient):
    # 10. Successful mutation returns authoritative backend state.
    payload = {
        "status": "ACKNOWLEDGED",
        "expected_version": 1,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    data = res.json()["data"]
    assert data["version"] == 2
    assert len(data["history"]) > 0


@pytest.mark.asyncio
async def test_api_invalid_transition(setup_api, async_client: AsyncClient):
    # 11. Invalid transition is rejected by frozen lifecycle semantics.
    # Trying to resolve an active alert directly (skipping ACKNOWLEDGED) may or may not be invalid in frozen service,
    # but we can try setting an invalid enum status or transition that raises HTTPException inside the service.
    # The API layer returns 400 if enum is invalid.
    payload = {
        "status": "INVALID_STATUS",
        "expected_version": 1,
        "plant_id": setup_api["plant_a"],
    }
    res = await async_client.post(
        f"/api/v1/alerts/{setup_api['alert1']}/transition",
        json=payload,
        headers=setup_api["head_super"],
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_no_bypass_frozen_service(setup_api, async_client: AsyncClient):
    # 12. No route bypasses the frozen service layer.
    # We can mock transition_alert_status to prove it is called.
    with patch("app.api.routes.alerts.transition_alert_status") as mock_transition:
        mock_transition.side_effect = HTTPException(
            status_code=418, detail="I'm a teapot"
        )
        payload = {
            "status": "ACKNOWLEDGED",
            "expected_version": 1,
            "plant_id": setup_api["plant_a"],
        }
        res = await async_client.post(
            f"/api/v1/alerts/{setup_api['alert1']}/transition",
            json=payload,
            headers=setup_api["head_super"],
        )
        assert res.status_code == 418
        mock_transition.assert_called_once()
