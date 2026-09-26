import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import urllib.parse
from sqlalchemy import text

pw1 = 'Xaiote#27!Aspect@S7y$27'
pw2 = '<Xaiote#27!Aspect@S7y$27>'
pw3 = '^<Xaiote#27!Aspect@S7y$27^>'

async def test_conn(pw):
    encoded = urllib.parse.quote_plus(pw)
    url = f'postgresql+asyncpg://postgres:{encoded}@db.vyksaiqqwlltlvnlhlnl.supabase.co:5432/postgres'
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            res = await conn.execute(text("SELECT 1"))
            print('SUCCESS with', 'pw1' if pw==pw1 else 'pw2' if pw==pw2 else 'pw3')
            return True
    except Exception as e:
        return False
    finally:
        await engine.dispose()

async def main():
    for pw in [pw1, pw2, pw3]:
        if await test_conn(pw):
            break

asyncio.run(main())
