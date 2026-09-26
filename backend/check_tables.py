import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check():
    engine = create_async_engine(
        "postgresql+asyncpg://user:password@db:5432/xaiote_test"
    )
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
            )
        )
        print("TABLES:", res.fetchall())
    await engine.dispose()


asyncio.run(check())
