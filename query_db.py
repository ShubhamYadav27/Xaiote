import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = 'postgresql+asyncpg://postgres.vyksaiqqwlltlvnlhlnl:Xaiote%2327!Aspect%40S7y%2427@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        res = await conn.execute(text('SELECT id, name FROM companies LIMIT 1;'))
        row = res.fetchone()
        if row:
            print(f"Company ID: {row[0]}, Name: {row[1]}")
        else:
            print("No companies found!")
            
        res2 = await conn.execute(text("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = 'whatsapp_integrations';"))
        print("\nColumns in whatsapp_integrations:")
        for r in res2:
            print(f"{r[0]} ({r[1]}, nullable: {r[2]})")

asyncio.run(main())
