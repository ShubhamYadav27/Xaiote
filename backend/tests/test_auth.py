import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_auth_lifecycle():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            "/api/auth/register",
            json={
                "email": "test@test.com",
                "password": "pass",
                "full_name": "Test",
                "company_name": "C1",
                "industry": "Auto",
                "revenue_range": "50Cr-100Cr",
            },
        )
        assert res.status_code == 200, res.json()

        res_login = await ac.post(
            "/api/auth/login", json={"email": "test@test.com", "password": "pass"}
        )
        data = res_login.json()["data"]
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        res_me = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {access_token}"}
        )
        assert res_me.json()["data"]["email"] == "test@test.com"

        res_ref = await ac.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        new_data = res_ref.json()["data"]
        new_access = new_data["access_token"]
        new_refresh = new_data["refresh_token"]

        # USE the new_access token to fix F841 and verify it works
        res_me2 = await ac.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {new_access}"}
        )
        assert res_me2.json()["data"]["email"] == "test@test.com"

        res_ref_old = await ac.post(
            "/api/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert "detail" in res_ref_old.json()

        res_logout = await ac.post(
            "/api/auth/logout", json={"refresh_token": new_refresh}
        )
        assert res_logout.status_code == 200

        res_ref_logout = await ac.post(
            "/api/auth/refresh", json={"refresh_token": new_refresh}
        )
        assert "detail" in res_ref_logout.json()


@pytest.mark.asyncio
async def test_tenant_isolation():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        await ac.post(
            "/api/auth/register",
            json={
                "email": "a@a.com",
                "password": "p",
                "full_name": "A",
                "company_name": "CA",
            },
        )
        login_a = await ac.post(
            "/api/auth/login", json={"email": "a@a.com", "password": "p"}
        )
        token_a = login_a.json()["data"]["access_token"]

        await ac.post(
            "/api/auth/register",
            json={
                "email": "b@b.com",
                "password": "p",
                "full_name": "B",
                "company_name": "CB",
            },
        )
        login_b = await ac.post(
            "/api/auth/login", json={"email": "b@b.com", "password": "p"}
        )
        token_b = login_b.json()["data"]["access_token"]

        plant_a_res = await ac.post(
            "/api/v1/plants",
            json={"name": "Plant A", "location": "L1", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert plant_a_res.status_code == 200, plant_a_res.json()
        plant_a_id = plant_a_res.json()["data"]["id"]

        plant_b_res = await ac.post(
            "/api/v1/plants",
            json={"name": "Plant B", "location": "L2", "timezone": "UTC"},
            headers={"Authorization": f"Bearer {token_b}"},
        )
        plant_b_id = plant_b_res.json()["data"]["id"]

        assert (
            await ac.get(
                f"/api/v1/plants/{plant_a_id}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
        ).status_code == 200
        assert (
            await ac.get(
                f"/api/v1/plants/{plant_b_id}",
                headers={"Authorization": f"Bearer {token_b}"},
            )
        ).status_code == 200

        res_denied_1 = await ac.get(
            f"/api/v1/plants/{plant_b_id}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert "detail" in res_denied_1.json()

        res_denied_2 = await ac.get(
            f"/api/v1/plants/{plant_a_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert "detail" in res_denied_2.json()
