import asyncio
import uuid

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main():
    email_val = f"{uuid.uuid4()}@t.com"
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res1 = await client.post(
            "/api/auth/register",
            json={
                "email": email_val,
                "password": "p",
                "full_name": "t",
                "company_name": f"{uuid.uuid4()}",
                "industry": "a",
                "revenue_range": "",
            },
        )
        print("REG:", res1.status_code, res1.json())
        res2 = await client.post(
            "/api/auth/login", data={"username": email_val, "password": "p"}
        )
        print("LOGIN:", res2.status_code, res2.json())


asyncio.run(main())
