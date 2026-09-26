import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        await c.execute(text("UPDATE authorized_senders SET company_id = '1c6b5e63-ee7f-4fd6-b737-8937c46e38ff'"))
        await c.execute(text("UPDATE machines SET company_id = '1c6b5e63-ee7f-4fd6-b737-8937c46e38ff'"))
        await c.execute(text("UPDATE work_orders SET company_id = '1c6b5e63-ee7f-4fd6-b737-8937c46e38ff'"))
        await c.execute(text("UPDATE plants SET company_id = '1c6b5e63-ee7f-4fd6-b737-8937c46e38ff'"))
        await c.commit()
asyncio.run(m())
