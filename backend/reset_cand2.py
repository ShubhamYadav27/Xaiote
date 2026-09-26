import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        await c.execute(text("UPDATE extracted_event_candidates SET processing_status = 'PENDING', worker_id = NULL, lease_until = NULL, retry_count = 0"))
        await c.commit()
asyncio.run(m())
