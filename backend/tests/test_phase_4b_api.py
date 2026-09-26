import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.company import Company
from app.models.masters import Customer, Product
from app.models.plant import Plant
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderStatus


@pytest.fixture
async def setup_data(db_session: AsyncSession):
    db = db_session
    # Clean up
    await db.execute(text("DELETE FROM work_order_risk_history"))
    await db.execute(text("DELETE FROM incident_decision_history"))
    await db.execute(text("DELETE FROM incident_events"))
    await db.execute(text("DELETE FROM assessment_decision_history"))
    await db.execute(text("DELETE FROM assessment_evidence_links"))
    await db.execute(text("DELETE FROM root_cause_assessments"))
    await db.execute(text("DELETE FROM incident_analyses"))
    await db.execute(text("DELETE FROM whatsapp_integrations"))
    await db.execute(text("DELETE FROM authorized_senders"))
    await db.execute(text("DELETE FROM incidents"))
    await db.execute(text("DELETE FROM impact_decision_history"))
    await db.execute(text("DELETE FROM production_order_impacts"))
    await db.execute(text("DELETE FROM manufacturing_event_revisions"))
    await db.execute(text("DELETE FROM manufacturing_events"))
    await db.execute(text("DELETE FROM canonicalization_jobs"))
    await db.execute(text("DELETE FROM entity_resolution_results"))
    await db.execute(text("DELETE FROM extracted_event_candidates"))
    await db.execute(text("DELETE FROM communication_transcripts"))
    await db.execute(text("DELETE FROM communication_attachments"))
    await db.execute(text("DELETE FROM communication_messages"))
    await db.execute(text("DELETE FROM work_orders"))
    await db.execute(text("DELETE FROM machines"))
    await db.execute(text("DELETE FROM products"))
    await db.execute(text("DELETE FROM customers"))
    await db.execute(text("DELETE FROM import_audits"))
    await db.execute(text("DELETE FROM import_jobs"))
    await db.execute(text("DELETE FROM refresh_tokens"))
    await db.execute(text("DELETE FROM users"))
    await db.execute(text("DELETE FROM plants"))
    await db.execute(text("DELETE FROM companies"))
    await db.commit()

    company1 = Company(id=str(uuid.uuid4()), name="Company 1")
    company2 = Company(id=str(uuid.uuid4()), name="Company 2")
    db.add(company1)
    db.add(company2)

    plant1 = Plant(id=str(uuid.uuid4()), company_id=company1.id, name="Plant 1", timezone="UTC")
    plant2 = Plant(id=str(uuid.uuid4()), company_id=company2.id, name="Plant 2", timezone="UTC")
    db.add(plant1)
    db.add(plant2)
    await db.flush()

    user1 = User(
        id=str(uuid.uuid4()),
        company_id=company1.id,
        email="user1@example.com",
        password_hash="hashed",
        full_name="User 1",
        role="USER",
    )
    db.add(user1)

    customer1 = Customer(
        id=str(uuid.uuid4()), company_id=company1.id, name="Customer 1"
    )
    db.add(customer1)
    product1 = Product(id=str(uuid.uuid4()), company_id=company1.id, name="Product 1")
    db.add(product1)

    wo1 = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=company1.id,
        plant_id=plant1.id,
        order_number="WO-1",
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
        product_id=product1.id,
        customer_id=customer1.id,
        quantity=100,
        production_progress=0,
    )
    db.add(wo1)

    wo2 = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=company2.id,
        plant_id=plant2.id,
        order_number="WO-2",
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=datetime.now(timezone.utc) + timedelta(days=1),
        product_id=product1.id,
        customer_id=customer1.id,
        quantity=100,
        production_progress=0,
    )
    db.add(wo2)

    # Due date is none, so this will be ON_TRACK
    wo3 = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=company1.id,
        plant_id=plant1.id,
        order_number="WO-3",
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=None,
        product_id=product1.id,
        customer_id=customer1.id,
        quantity=100,
        production_progress=0,
    )
    db.add(wo3)

    await db.commit()

    token1 = jwt.encode({"sub": str(user1.id)}, settings.JWT_SECRET, algorithm="HS256")
    headers1 = {"Authorization": f"Bearer {token1}"}

    return {
        "company1": company1,
        "company2": company2,
        "user1": user1,
        "wo1": wo1,
        "wo2": wo2,
        "wo3": wo3,
        "headers1": headers1,
        "plant1": plant1,
    }


@pytest.mark.asyncio
async def test_risk_api_get(setup_data):
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        wo1 = setup_data["wo1"]
        headers = setup_data["headers1"]
        response = await async_client.get(
            f"/api/v1/work-orders/{wo1.id}/risk", headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["work_order_id"] == wo1.id
        assert data["risk_state"] == "ON_TRACK"
        assert "Work Order is active, not overdue" in data["impact_summary"]


@pytest.mark.asyncio
async def test_risk_api_tenant_isolation(setup_data):
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        wo2 = setup_data["wo2"]
        headers = setup_data["headers1"]
        response = await async_client.get(
            f"/api/v1/work-orders/{wo2.id}/risk", headers=headers
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_risk_dashboard(setup_data):
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        headers = setup_data["headers1"]
        response = await async_client.get("/api/v1/risk/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2  # wo1 and wo3
        assert any(
            item["work_order_id"] == setup_data["wo1"].id for item in data["items"]
        )
        assert any(
            item["work_order_id"] == setup_data["wo3"].id for item in data["items"]
        )


@pytest.mark.asyncio
async def test_risk_dashboard_filter_plant(setup_data):
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        headers = setup_data["headers1"]
        plant_id = setup_data["plant1"].id
        response = await async_client.get(
            f"/api/v1/risk/dashboard?plant_id={plant_id}", headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2


@pytest.mark.asyncio
async def test_risk_history_empty(setup_data):
    from app.main import app

    async with AsyncClient(app=app, base_url="http://testserver") as async_client:
        wo1 = setup_data["wo1"]
        headers = setup_data["headers1"]
        response = await async_client.get(
            f"/api/v1/work-orders/{wo1.id}/risk/history", headers=headers
        )
        assert response.status_code == 200
        assert len(response.json()) == 0
