import asyncio, uuid
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        res = await c.execute(text('SELECT id FROM companies LIMIT 1'))
        comp_id = res.scalar()
        
        s_id = str(uuid.uuid4())
        await c.execute(text(f"INSERT INTO authorized_senders (id, company_id, phone_number, status, created_at, updated_at) VALUES ('{s_id}', '{comp_id}', '12345', 'AUTHORIZED', now(), now())"))
        
        await c.commit()
        print('Inserted AuthorizedSender 12345')
asyncio.run(m())
