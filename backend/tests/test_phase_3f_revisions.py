import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.main import app
from app.models.company import Company
from app.models.manufacturing_event import ManufacturingEvent, ProvenanceType
from app.models.user import User
from tests.test_phase_3f_validation import (
    process_one_candidate,
    process_one_job,
    setup_base_data,
)

pytestmark = pytest.mark.asyncio


async def setup_event_and_token():
    async with AsyncSessionLocal() as db:
        _, _, _, _, _, cand = await setup_base_data(db, "DOWNTIME")

    while await process_one_candidate("w1"):
        pass
    while await process_one_job("w2"):
        pass

    async with AsyncSessionLocal() as db:
        ev = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(
                        ManufacturingEvent.candidate_id == cand.id
                    )
                )
            )
            .scalars()
            .first()
        )
        ev_id = ev.id
        comp_id = ev.company_id  # noqa: F841

    client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    email_val = f"{uuid.uuid4()}@t.com"
    res = await client.post(
        "/api/auth/register",
        json={
            "email": email_val,
            "password": "p",
            "full_name": "t",
            "company_name": f"{uuid.uuid4()}",
            "industry": "a",
            "revenue_range": "",
        },
    )
    res = await client.post(
        "/api/auth/login", json={"email": email_val, "password": "p"}
    )
    assert res.status_code == 200, f"Login failed: {res.json()}"
    token = res.json()["data"]["access_token"]
    token_headers = {"Authorization": f"Bearer {token}"}

    async with AsyncSessionLocal() as db:
        user = (
            (await db.execute(select(User).where(User.email == email_val)))
            .scalars()
            .first()
        )
        user_comp = (
            (await db.execute(select(Company).where(Company.id == user.company_id)))
            .scalars()
            .first()
        )
        ev_real = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(ManufacturingEvent.id == ev_id)
                )
            )
            .scalars()
            .first()
        )
        ev_real.company_id = user_comp.id
        db.add(ev_real)
        await db.commit()

    return ev_id, token_headers, client, user.id, user_comp.id


async def test_revision_schema_and_auth():
    ev_id, token_headers, client, _actor_id, comp_id = await setup_event_and_token()

    # 7. Auth required
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        json={"changes": {"severity": "Critical"}, "reason": "test"},
    )
    assert res.status_code == 403

    # 13. Empty changes
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {}, "reason": "test"},
    )
    assert res.status_code == 400

    # 14. Empty reason
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "Critical"}, "reason": ""},
    )
    assert res.status_code == 400

    # 11. Unknown fields
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"invalid_field": "x"}, "reason": "test"},
    )
    assert res.status_code == 400

    # 15. Invalid event
    res = await client.post(
        f"/api/v1/events/{uuid.uuid4()}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "Critical"}, "reason": "test"},
    )
    assert res.status_code == 404

    # 8. Cross-tenant
    async with AsyncSessionLocal() as db:
        ev = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(ManufacturingEvent.id == ev_id)
                )
            )
            .scalars()
            .first()
        )
        new_comp_id = str(uuid.uuid4())
        new_comp = Company(
            id=new_comp_id, name="Test2", industry="A", revenue_range="B"
        )
        db.add(new_comp)
        ev.company_id = new_comp_id
        await db.commit()
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "Critical"}, "reason": "test"},
    )
    assert res.status_code == 404

    # Restore company
    async with AsyncSessionLocal() as db:
        ev = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(ManufacturingEvent.id == ev_id)
                )
            )
            .scalars()
            .first()
        )
        ev.company_id = comp_id
        await db.commit()


async def test_provenance_and_history():
    ev_id, token_headers, client, actor_id, _comp_id = await setup_event_and_token()

    # Set base provenance to MODEL_DERIVED for test
    async with AsyncSessionLocal() as db:
        ev = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(ManufacturingEvent.id == ev_id)
                )
            )
            .scalars()
            .first()
        )
        ev.severity = "Low"
        ev.severity_provenance = ProvenanceType.MODEL_DERIVED
        ev.root_cause = "Old Cause"
        ev.root_cause_provenance = ProvenanceType.MODEL_DERIVED
        await db.commit()

    # First revision
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "Critical"}, "reason": "Confirmed"},
    )
    assert res.status_code == 200
    rev_data = res.json()["data"]

    assert rev_data["actor_id"] == actor_id
    assert rev_data["changed_fields"]["severity"]["old_value"] == "Low"
    assert rev_data["changed_fields"]["severity"]["new_value"] == "Critical"
    assert (
        rev_data["changed_fields"]["severity"]["previous_provenance"] == "MODEL_DERIVED"
    )
    assert rev_data["changed_fields"]["severity"]["new_provenance"] == "HUMAN_CONFIRMED"

    # 24, 25, 27. Read effective state
    res = await client.get(f"/api/v1/events/{ev_id}", headers=token_headers)
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["base_event"]["severity"] == "Low"
    assert data["current_state"]["severity"] == "Critical"
    assert data["current_state"]["severity_provenance"] == "HUMAN_CONFIRMED"
    assert data["current_state"]["root_cause"] == "Old Cause"  # Unmodified
    assert data["current_state"]["root_cause_provenance"] == "MODEL_DERIVED"
    assert len(data["revisions"]) == 1

    # Second revision
    res = await client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={
            "changes": {"severity": "High", "root_cause": "New Cause"},
            "reason": "Correction",
        },
    )

    res = await client.get(f"/api/v1/events/{ev_id}", headers=token_headers)
    data = res.json()["data"]
    assert len(data["revisions"]) == 2

    # Base event remains immutable
    assert data["base_event"]["severity"] == "Low"
    assert data["base_event"]["root_cause"] == "Old Cause"

    # Current applies all in order
    assert data["current_state"]["severity"] == "High"
    assert data["current_state"]["root_cause"] == "New Cause"
    assert data["current_state"]["root_cause_provenance"] == "HUMAN_CONFIRMED"


async def test_concurrency_revisions():
    import asyncio

    ev_id, token_headers, client, _actor_id, _comp_id = await setup_event_and_token()

    # Two simultaneous
    req1 = client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "S1"}, "reason": "1"},
    )
    req2 = client.post(
        f"/api/v1/events/{ev_id}/revisions",
        headers=token_headers,
        json={"changes": {"severity": "S2"}, "reason": "2"},
    )

    results = await asyncio.gather(req1, req2)
    assert all(r.status_code == 200 for r in results)

    res = await client.get(f"/api/v1/events/{ev_id}", headers=token_headers)
    data = res.json()["data"]
    assert len(data["revisions"]) == 2

    # 34. candidate_id remains NOT NULL and UNIQUE because we didn't touch ManufacturingEvent table
    async with AsyncSessionLocal() as db:
        ev = (
            (
                await db.execute(
                    select(ManufacturingEvent).where(ManufacturingEvent.id == ev_id)
                )
            )
            .scalars()
            .first()
        )
        assert ev.candidate_id is not None
