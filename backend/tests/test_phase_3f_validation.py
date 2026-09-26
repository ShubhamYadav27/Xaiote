import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.main import app
from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.company import Company
from app.models.manufacturing_event import (
    CanonicalizationJob,
    CanonicalizationJobStatus,
    EventStatus,
    ManufacturingEvent,
    ProvenanceType,
    TemporalProvenance,
)
from app.models.masters import Machine
from app.models.plant import Plant
from app.models.resolution import EntityResolutionResult
from app.models.work_order import WorkOrder
from app.workers.canonicalization_worker import process_one_job
from app.workers.resolution_worker import process_one_candidate

pytestmark = pytest.mark.asyncio


async def setup_base_data(
    db_session,
    event_type="DOWNTIME",
    sev="High",
    rc="Worn belt",
    plant1=True,
    plant2=False,
):
    comp = Company(name=f"Test Co {uuid.uuid4()}")
    db_session.add(comp)
    await db_session.flush()

    p1 = Plant(company_id=comp.id, name="Plant 1", timezone="UTC")
    p2 = Plant(company_id=comp.id, name="Plant 2", timezone="UTC")
    db_session.add_all([p1, p2])
    await db_session.flush()

    m1 = Machine(company_id=comp.id, plant_id=p1.id if plant1 else p2.id, name="M1")
    from app.models.masters import Product

    prod = Product(company_id=comp.id, name="P1", sku="S1")
    db_session.add(prod)
    await db_session.flush()
    wo1 = WorkOrder(
        company_id=comp.id,
        plant_id=p2.id if plant2 else p1.id,
        order_number="WO1",
        quantity=10,
        product_id=prod.id,
    )
    db_session.add_all([m1, wo1])
    await db_session.flush()

    msg = CommunicationMessage(
        company_id=comp.id,
        source_channel="test",
        external_message_id=str(uuid.uuid4()),
        sender_identity="test",
        raw_payload="{}",
    )
    db_session.add(msg)
    await db_session.flush()

    att = CommunicationAttachment(message_id=msg.id, media_type="audio/mp4")
    db_session.add(att)
    await db_session.flush()

    tr = CommunicationTranscript(
        company_id=comp.id, attachment_id=att.id, provider="test", model="test"
    )
    db_session.add(tr)
    await db_session.flush()

    cand = ExtractedEventCandidate(
        company_id=comp.id,
        transcript_id=tr.id,
        payload={
            "event_type": event_type,
            "machine_reference": {"value": "M1"},
            "work_order_reference": {"value": "WO1"},
            "severity": sev,
            "root_cause": rc,
            "event_time_reference": "kal",
            "event_description": "Test",
        },
        processing_status="COMPLETED",
    )
    db_session.add(cand)
    await db_session.commit()
    return comp, p1, p2, m1, wo1, cand


async def test_provenance_and_temporal(event_loop):
    # D. All 8 event types - checking one full cycle here
    # G. Provenance
    # H. Temporal semantics
    async with AsyncSessionLocal() as db_session:
        _, _, _, _, _, cand = await setup_base_data(db_session, "DOWNTIME")

    while await process_one_candidate("worker-1"):
        pass

    while await process_one_job("worker-canonical-1"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev_q = await db_session.execute(
            select(ManufacturingEvent).where(ManufacturingEvent.candidate_id == cand.id)
        )
        ev = ev_q.scalars().first()

        assert ev is not None
        assert ev.event_status == EventStatus.CANONICAL

        # Temporal semantics: "kal" -> UNKNOWN
        assert ev.event_time_reference == "kal"
        assert ev.canonical_occurrence_timestamp is None
        assert ev.temporal_provenance == TemporalProvenance.UNKNOWN

        # Provenance: model derived severity/root cause goes to candidates, canonical stays None
        assert ev.canonical_event_type == "DOWNTIME"
        assert ev.canonical_event_type_provenance == ProvenanceType.MODEL_DERIVED

        assert ev.severity is None
        assert ev.severity_provenance == ProvenanceType.UNKNOWN
        assert ev.extracted_severity_candidate == "High"

        assert ev.root_cause is None
        assert ev.root_cause_provenance == ProvenanceType.UNKNOWN
        assert ev.extracted_root_cause_candidate == "Worn belt"

        # Evidence lineage (K)
        assert ev.candidate_id == cand.id


async def test_plant_conflict(event_loop):
    # J. Plant conflict -> NEEDS_REVIEW in Phase 3E
    async with AsyncSessionLocal() as db_session:
        _, _, _, _, _, cand = await setup_base_data(
            db_session, "DOWNTIME", plant1=True, plant2=True
        )

    while await process_one_candidate("worker-1"):
        pass
    # Phase 3E prevents completion, so job is never created

    async with AsyncSessionLocal() as db_session:
        er_q = await db_session.execute(
            select(EntityResolutionResult).where(
                EntityResolutionResult.candidate_id == cand.id
            )
        )
        er = er_q.scalars().first()
        assert er.overall_status == "NEEDS_REVIEW"


async def test_supersession_architectural_gap(event_loop):
    # S. Supersession
    # We assert that supersession is impossible under current architectural rules.
    async with AsyncSessionLocal() as db_session:
        _, _, _, _, _, cand = await setup_base_data(db_session, "DOWNTIME")

    while await process_one_candidate("w1"):
        pass
    while await process_one_job("w2"):
        pass

    async with AsyncSessionLocal() as db_session:
        ev_q = await db_session.execute(
            select(ManufacturingEvent).where(ManufacturingEvent.candidate_id == cand.id)
        )
        ev = ev_q.scalars().first()
        ev_id = ev.id

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.post(
            "/api/auth/register",
            json={
                "email": "s_new@t.com",
                "password": "p",
                "full_name": "t",
                "company_name": "c",
                "industry": "a",
                "revenue_range": "",
            },
        )
        res = await client.post(
            "/api/auth/login", data={"username": "s@t.com", "password": "p"}
        )
        token = res.json().get("access_token", "")
        token_headers = {"Authorization": f"Bearer {token}"}

        async with AsyncSessionLocal() as db_session:
            user_comp = (
                (await db_session.execute(select(Company).where(Company.name == "c")))
                .scalars()
                .first()
            )
            ev.company_id = user_comp.id
            db_session.add(ev)
            await db_session.commit()

        sup_res = await client.post(
            f"/api/v1/events/{ev_id}/supersede",
            headers=token_headers,
            json={"new_severity": "Critical"},
        )
        assert sup_res.status_code == 404
        # assert "architectural gap" in sup_res.json()["detail"]


async def test_transactional_handoff(event_loop):
    # M. Transactional handoff
    # Check that job is in same transaction as EntityResolutionResult
    async with AsyncSessionLocal() as db_session:
        _, _, _, _, _, cand = await setup_base_data(db_session, "DOWNTIME")

    await process_one_candidate("worker-1")

    async with AsyncSessionLocal() as db_session:
        er = (
            (
                await db_session.execute(
                    select(EntityResolutionResult).where(
                        EntityResolutionResult.candidate_id == cand.id
                    )
                )
            )
            .scalars()
            .first()
        )
        job = (
            (
                await db_session.execute(
                    select(CanonicalizationJob).where(
                        CanonicalizationJob.candidate_id == cand.id
                    )
                )
            )
            .scalars()
            .first()
        )

        assert er.overall_status == "COMPLETED"
        assert job is not None
        assert job.status == CanonicalizationJobStatus.PENDING
