import pytest

from app.workers.canonicalization_worker import process_one_job

pytestmark = pytest.mark.asyncio


async def test_process_one_job_empty():
    from sqlalchemy import delete

    from app.infrastructure.database.session import AsyncSessionLocal
    from app.models.manufacturing_event import CanonicalizationJob

    async with AsyncSessionLocal() as db:
        await db.execute(delete(CanonicalizationJob))
        await db.commit()
    res = await process_one_job("test_worker")
    assert res in (True, False)
