import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_masters_crud_and_isolation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Setup two companies and their tokens
        run_id = str(uuid.uuid4())
        await ac.post(
            "/api/auth/register",
            json={
                "email": f"a_{run_id}@masters.com",
                "password": "p",
                "full_name": "A",
                "company_name": "CA",
            },
        )
        login_a = await ac.post(
            "/api/auth/login",
            json={"email": f"a_{run_id}@masters.com", "password": "p"},
        )
        token_a = login_a.json()["data"]["access_token"]

        await ac.post(
            "/api/auth/register",
            json={
                "email": f"b_{run_id}@masters.com",
                "password": "p",
                "full_name": "B",
                "company_name": "CB",
            },
        )
        login_b = await ac.post(
            "/api/auth/login",
            json={"email": f"b_{run_id}@masters.com", "password": "p"},
        )
        token_b = login_b.json()["data"]["access_token"]

        # 2. Test Customer Creation and Isolation
        cust_a_res = await ac.post(
            "/api/v1/customers",
            json={"name": "Cust A", "external_id": f"C-1-{run_id}"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert cust_a_res.status_code == 200, cust_a_res.json()

        # Test duplicate external_id
        cust_a_dup = await ac.post(
            "/api/v1/customers",
            json={"name": "Cust A2", "external_id": f"C-1-{run_id}"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert cust_a_dup.status_code == 400

        # Test Company B can use same external_id
        cust_b_res = await ac.post(
            "/api/v1/customers",
            json={"name": "Cust B", "external_id": f"C-1-{run_id}"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert cust_b_res.status_code == 200

        # Test Listing (Pagination and Isolation)
        list_a = await ac.get(
            "/api/v1/customers", headers={"Authorization": f"Bearer {token_a}"}
        )
        assert list_a.status_code == 200
        assert list_a.json()["data"]["total"] == 1
        assert list_a.json()["data"]["items"][0]["name"] == "Cust A"

        list_b = await ac.get(
            "/api/v1/customers", headers={"Authorization": f"Bearer {token_b}"}
        )
        assert list_b.json()["data"]["total"] == 1
        assert list_b.json()["data"]["items"][0]["name"] == "Cust B"

        # 3. Test Machine creation with Plant Verification
        plant_a_res = await ac.post(
            "/api/v1/plants",
            json={"name": "Plant A", "location": "L1", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        plant_a_id = plant_a_res.json()["data"]["id"]

        # Try to create Machine in Company A's plant using Company B's token
        mach_deny = await ac.post(
            "/api/v1/machines",
            json={"plant_id": plant_a_id, "name": "Mach B"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert mach_deny.status_code == 404  # Plant not found for Company B

        mach_a = await ac.post(
            "/api/v1/machines",
            json={"plant_id": plant_a_id, "name": "Mach A"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert mach_a.status_code == 200

        # Test Product Creation
        prod_a = await ac.post(
            "/api/v1/products",
            json={"name": "Prod A", "sku": "SKU1"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert prod_a.status_code == 200

        # Test Vendor Creation
        vend_a = await ac.post(
            "/api/v1/vendors",
            json={"name": "Vendor A"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert vend_a.status_code == 200
