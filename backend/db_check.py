import asyncio

from sqlalchemy import text

from app.infrastructure.database.session import AsyncSessionLocal


async def main():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT current_database(), current_user, version()")
        )
        print(result.fetchone())


if __name__ == "__main__":
    asyncio.run(main())
