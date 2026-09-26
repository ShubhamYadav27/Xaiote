import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["JWT_SECRET"] = "test-secret"
os.environ["JWT_REFRESH_SECRET"] = "test-refresh-secret"
os.environ["SECRET_ENCRYPTION_KEY"] = "Vl_QdYg2o-O_8jA5q4B0y8vV_1F6V5c9wG5V-Qy0qN4="
os.environ["MINIO_ENDPOINT"] = "http://storage:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
os.environ["TESTING"] = "true"
os.environ["TEST_DATABASE_URL"] = (
    "postgresql+asyncpg://user:password@db:5432/xaiote_test"
)

from app.infrastructure.database.session import AsyncSessionLocal, Base, engine
import app.models


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    async def _teardown():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    asyncio.run(_setup())
    yield
    asyncio.run(_teardown())


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def check_pending_tasks():
    yield
    import asyncio

    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        print(f"\nWARNING: Pending tasks after test: {pending}\n")
        # Cancel them so the test suite does not hang
        for task in pending:
            task.cancel()
        # Optionally await them


from httpx import AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def async_client():
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db_before_test(db_session: AsyncSession):
    from app.infrastructure.database.session import Base

    for table in reversed(Base.metadata.sorted_tables):
        try:
            await db_session.execute(table.delete())
        except Exception:
            pass
    await db_session.commit()
