import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        r = await c.execute(text("SELECT id, status, external_message_id FROM communication_messages WHERE external_message_id = 'wamid.00002'"))
        msg = r.fetchall()
        print('Message:', msg)
        if msg:
            r = await c.execute(text(f"SELECT id, status, media_type FROM communication_attachments WHERE message_id = '{msg[0][0]}'"))
            print('Attachment:', r.fetchall())
            
            r = await c.execute(text(f"SELECT id, processing_status FROM extracted_event_candidates"))
            print('Candidates:', r.fetchall())
asyncio.run(m())
