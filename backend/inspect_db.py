import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings


async def inspect():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        )
        tables = res.fetchall()
        print("Tables:", tables)
    await engine.dispose()


asyncio.run(inspect())
