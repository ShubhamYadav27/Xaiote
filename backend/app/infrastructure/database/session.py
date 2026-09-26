import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config import settings

is_testing = os.environ.get("TESTING") == "true"

if is_testing:
    db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/xaiote_test",
    )
    engine = create_async_engine(db_url, echo=False, poolclass=NullPool)
else:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
