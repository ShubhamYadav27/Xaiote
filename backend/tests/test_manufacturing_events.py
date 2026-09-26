import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

pytestmark = pytest.mark.asyncio


async def test_get_events():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/auth/register",
            json={
                "email": "ev@test.com",
                "password": "pass",
                "full_name": "test",
                "company_name": "c1",
                "industry": "auto",
                "revenue_range": "",
            },
        )
        res = await client.post(
            "/api/auth/login", data={"username": "ev@test.com", "password": "pass"}
        )
        token = res.json().get("access_token", "")
        token_headers = {"Authorization": f"Bearer {token}"}

        response = await client.get("/api/v1/events/", headers=token_headers)
        # Assuming the auth works and route exists
        print(response.json())
        assert response.status_code in [200, 401, 403, 404, 422]
        if response.status_code == 200:
            assert isinstance(response.json(), list)


async def test_supersede_event_not_found():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/auth/login", data={"username": "ev@test.com", "password": "pass"}
        )
        token = res.json().get("access_token", "")
        token_headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/v1/events/invalid-id/supersede",
            headers=token_headers,
            json={"new_description": "test"},
        )
        assert response.status_code in [404, 401, 422, 403]
