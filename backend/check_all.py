import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
async def m():
    e = create_async_engine('postgresql+asyncpg://user:password@db:5432/xaiote')
    async with e.connect() as c:
        for t in ['entity_resolution_results', 'manufacturing_events', 'work_order_risk_history', 'production_order_impacts']:
            try:
                r = await c.execute(text(f"SELECT * FROM {t} LIMIT 1"))
                print(f'{t}:', r.fetchall())
            except Exception as ex:
                print(f'{t} error: {ex}')
asyncio.run(m())
