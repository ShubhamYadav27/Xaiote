import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_work_orders_crud_and_isolation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Setup two companies and their tokens
        run_id = str(uuid.uuid4())
        await ac.post(
            "/api/auth/register",
            json={
                "email": f"wa_{run_id}@masters.com",
                "password": "p",
                "full_name": "A",
                "company_name": "CA",
            },
        )
        login_a = await ac.post(
            "/api/auth/login",
            json={"email": f"wa_{run_id}@masters.com", "password": "p"},
        )
        token_a = login_a.json()["data"]["access_token"]

        await ac.post(
            "/api/auth/register",
            json={
                "email": f"wb_{run_id}@masters.com",
                "password": "p",
                "full_name": "B",
                "company_name": "CB",
            },
        )
        login_b = await ac.post(
            "/api/auth/login",
            json={"email": f"wb_{run_id}@masters.com", "password": "p"},
        )
        token_b = login_b.json()["data"]["access_token"]

        # 2. Setup master data for A
        plant_a_res = await ac.post(
            "/api/v1/plants",
            json={"name": "Plant A", "location": "L1", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert plant_a_res.status_code == 200, plant_a_res.text
        plant_a_id = plant_a_res.json()["data"]["id"]

        prod_a = await ac.post(
            "/api/v1/products",
            json={"name": "Prod A"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        prod_a_id = prod_a.json()["data"]["id"]

        mach_a = await ac.post(
            "/api/v1/machines",
            json={"plant_id": plant_a_id, "name": "Mach A"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        mach_a_id = mach_a.json()["data"]["id"]

        cust_a = await ac.post(
            "/api/v1/customers",
            json={"name": "Cust A"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        cust_a_id = cust_a.json()["data"]["id"]

        # Setup master data for B
        plant_b_res = await ac.post(
            "/api/v1/plants",
            json={"name": "Plant B", "location": "L1", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        plant_b_id = plant_b_res.json()["data"]["id"]

        # 3. Create Work Order A
        wo_a_data = {
            "plant_id": plant_a_id,
            "product_id": prod_a_id,
            "machine_id": mach_a_id,
            "customer_id": cust_a_id,
            "order_number": "WO-1",
            "quantity": 100.5,
            "status": "PLANNED",
            "production_progress": 0,
        }
        wo_a = await ac.post(
            "/api/v1/work-orders",
            json=wo_a_data,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert wo_a.status_code == 200, wo_a.json()

        # 4. Duplicate Order Number should fail
        wo_a_dup = await ac.post(
            "/api/v1/work-orders",
            json=wo_a_data,
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert wo_a_dup.status_code == 400

        # 5. Cross-Tenant Integrity failures
        # Company B tries to create using Company A's plant
        wo_b_bad_plant = await ac.post(
            "/api/v1/work-orders",
            json={
                "plant_id": plant_a_id,
                "product_id": prod_a_id,
                "order_number": "WO-2",
                "quantity": 10,
            },
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert wo_b_bad_plant.status_code == 400

        # Company A tries to create using Company B's plant
        wo_a_bad_plant = await ac.post(
            "/api/v1/work-orders",
            json={
                "plant_id": plant_b_id,
                "product_id": prod_a_id,
                "order_number": "WO-3",
                "quantity": 10,
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert wo_a_bad_plant.status_code == 400

        # 6. List and Verify Isolation
        list_a = await ac.get(
            "/api/v1/work-orders", headers={"Authorization": f"Bearer {token_a}"}
        )
        assert list_a.status_code == 200
        assert list_a.json()["data"]["total"] == 1

        list_b = await ac.get(
            "/api/v1/work-orders", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert list_b.json()["data"]["total"] == 0

        # 7. Invalid fields
        # Negative quantity
        wo_a_bad_qty = await ac.post(
            "/api/v1/work-orders",
            json={
                "plant_id": plant_a_id,
                "product_id": prod_a_id,
                "order_number": "WO-4",
                "quantity": -10,
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert wo_a_bad_qty.status_code == 422  # Pydantic validation

        # Invalid progress
        wo_a_bad_prog = await ac.post(
            "/api/v1/work-orders",
            json={
                "plant_id": plant_a_id,
                "product_id": prod_a_id,
                "order_number": "WO-5",
                "quantity": 10,
                "production_progress": 150,
            },
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert wo_a_bad_prog.status_code == 422
