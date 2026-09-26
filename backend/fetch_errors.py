import asyncio

from sqlalchemy.future import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.resolution import EntityResolutionResult


async def run():
    async with AsyncSessionLocal() as db:
        er_q = await db.execute(
            select(EntityResolutionResult).where(
                EntityResolutionResult.last_error.isnot(None)
            )
        )
        for er in er_q.scalars().all():
            print(er.last_error)


asyncio.run(run())
