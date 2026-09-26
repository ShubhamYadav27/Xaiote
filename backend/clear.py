import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        await c.execute(text("DELETE FROM extracted_event_candidates"))
        await c.execute(text("DELETE FROM communication_transcripts"))
        await c.execute(text("DELETE FROM communication_attachments"))
        await c.execute(text("DELETE FROM communication_messages"))
        await c.commit()
asyncio.run(m())
