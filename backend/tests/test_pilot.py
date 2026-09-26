import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_pilot_persistence(db_session):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post(
            "/api/company/pilot",
            json={
                "full_name": "Test User",
                "email": "test@company.com",
                "company_name": "Test Co",
                "team_size": "100",
                "role": "CTO",
                "primary_challenge": "Scaling",
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["data"]["message"] == "Pilot request received"
        assert "id" in data["data"]
