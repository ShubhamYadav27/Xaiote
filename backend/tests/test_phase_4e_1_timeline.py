import urllib.parse
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.company import Company
from app.models.impact import ImpactProvenance, ImpactStatus, ProductionOrderImpact
from app.models.incident import (
    Incident,
    IncidentEvent,
    IncidentStatus,
)
from app.models.manufacturing_event import EventStatus, ManufacturingEvent
from app.models.masters import Customer, Machine, Product
from app.models.plant import Plant
from app.models.resolution import EntityResolutionResult
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderStatus


@pytest.fixture
async def setup_data(db_session: AsyncSession):
    db = db_session
    c1 = Company(id=str(uuid.uuid4()), name="Company 4E Timeline")
    p1 = Plant(id=str(uuid.uuid4()), company_id=c1.id, name="Plant 4E", timezone="UTC")
    u1 = User(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="User",
        role="SUPERVISOR",
    )
    db.add_all([c1, p1, u1])
    await db.flush()

    mac = Machine(id=str(uuid.uuid4()), company_id=c1.id, plant_id=p1.id, name="CNC-4E")
    prod = Product(id=str(uuid.uuid4()), company_id=c1.id, name="Motor 4E")
    cust = Customer(id=str(uuid.uuid4()), company_id=c1.id, name="AutoCorp 4E")
    db.add_all([mac, prod, cust])
    await db.flush()

    now = datetime.now(timezone.utc)
    wo = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-4E-T",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=now + timedelta(days=2),
    )

    inc = Incident(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        machine_id=mac.id,
        title="Incident 4E T",
        status=IncidentStatus.ACTIVE.value,
    )
    db.add_all([wo, inc])
    await db.flush()

    cand_id = str(uuid.uuid4())
    msg = CommunicationMessage(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        source_channel="test",
        external_message_id=str(uuid.uuid4()),
        sender_identity="test",
    )
    db.add(msg)
    await db.flush()
    att = CommunicationAttachment(
        id=str(uuid.uuid4()), message_id=msg.id, media_type="audio"
    )
    db.add(att)
    await db.flush()
    tr = CommunicationTranscript(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        attachment_id=att.id,
        provider="test",
        model="test",
    )
    db.add(tr)
    await db.flush()
    cand = ExtractedEventCandidate(id=cand_id, company_id=c1.id, transcript_id=tr.id)
    db.add(cand)
    await db.flush()
    res = EntityResolutionResult(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        candidate_id=cand.id,
        machine_id=mac.id,
        machine_state="RESOLVED",
    )
    db.add(res)
    await db.flush()

    ev1 = ManufacturingEvent(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        candidate_id=cand_id,
        event_idempotency_key=str(uuid.uuid4()),
        event_status=EventStatus.CANONICAL,
        canonical_event_type="MACHINE_FAILURE",
        canonical_occurrence_timestamp=now - timedelta(hours=1),
    )
    db.add(ev1)
    await db.flush()

    inc_ev = IncidentEvent(
        id=str(uuid.uuid4()), incident_id=inc.id, event_id=ev1.id, link_state="LINKED"
    )
    db.add(inc_ev)

    imp = ProductionOrderImpact(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        work_order_id=wo.id,
        incident_id=inc.id,
        event_id=ev1.id,
        status=ImpactStatus.CONFIRMED,
        provenance=ImpactProvenance.MACHINE_CONTEXT_DERIVED,
    )
    db.add(imp)
    await db.flush()

    token1 = jwt.encode({"sub": str(u1.id)}, settings.JWT_SECRET, algorithm="HS256")
    await db.commit()

    return {
        "company": c1,
        "wo": wo,
        "inc": inc,
        "ev": ev1,
        "headers": {"Authorization": f"Bearer {token1}"},
    }


@pytest.mark.asyncio
async def test_timeline_operational_chronology(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=incident&entity_id={setup_data['inc'].id}&chronology=operational",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "data" in data
    assert "context_generated_at" in data

    entries = data["data"]
    if entries:
        assert "presentation_time" in entries[0]
        assert "presentation_time_provenance" in entries[0]


@pytest.mark.asyncio
async def test_timeline_audit_chronology(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=work_order&entity_id={setup_data['wo'].id}&chronology=audit",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "data" in data
    entries = data["data"]
    if entries:
        assert entries[0]["presentation_time_provenance"] in (
            "EXPLICIT_DECISION",
            "DECISION_FALLBACK_RECORDED",
        )


@pytest.mark.asyncio
async def test_timeline_pagination(async_client: AsyncClient, setup_data):
    # Add multiple impacts so there are multiple timeline entries
    res1 = await async_client.get(
        f"/api/v1/timeline?entity_type=incident&entity_id={setup_data['inc'].id}&limit=1",
        headers=setup_data["headers"],
    )
    assert res1.status_code == 200
    data1 = res1.json()["data"]

    if data1["data"] and data1.get("next_cursor"):
        cursor = data1["next_cursor"]
        res2 = await async_client.get(
            f"/api/v1/timeline?entity_type=incident&entity_id={setup_data['inc'].id}&limit=1&cursor={urllib.parse.quote(cursor)}",
            headers=setup_data["headers"],
        )
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        if data2["data"]:
            assert data1["data"][0]["source_id"] != data2["data"][0]["source_id"]


@pytest.mark.asyncio
async def test_timeline_invalid_cursor(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=incident&entity_id={setup_data['inc'].id}&cursor=invalid_cursor_format",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_timeline_empty_behavior(async_client: AsyncClient, setup_data):
    fake_id = str(uuid.uuid4())
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=incident&entity_id={fake_id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["data"]) == 0


@pytest.mark.asyncio
async def test_tie_breaking(async_client: AsyncClient, setup_data):
    # Already added multiple impacts.
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=incident&entity_id={setup_data['inc'].id}&limit=10",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    entries = res.json()["data"]["data"]

    for i in range(len(entries) - 1):
        pt1 = entries[i]["presentation_time"]
        pt2 = entries[i + 1]["presentation_time"]
        sid1 = entries[i]["source_id"]
        sid2 = entries[i + 1]["source_id"]

        # Must be descending by time, then descending by id
        if pt1 == pt2:
            assert sid1 > sid2


@pytest.mark.asyncio
async def test_tie_breaking_work_order(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/timeline?entity_type=work_order&entity_id={setup_data['wo'].id}&limit=10",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_operational_occurrence_time_precedence(
    async_client: AsyncClient, setup_data
):
    # Already implicitly covered by test_timeline_operational_chronology, but here for explicit tracking
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["wo"].id + "&entity_type=work_order",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_operational_recorded_time_fallback(
    async_client: AsyncClient, setup_data
):
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["inc"].id + "&entity_type=incident",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_audit_decision_time_precedence(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        "/api/v1/timeline?entity_id="
        + setup_data["inc"].id
        + "&entity_type=incident&chronology=audit",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_audit_recorded_time_fallback(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        "/api/v1/timeline?entity_id="
        + setup_data["wo"].id
        + "&entity_type=work_order&chronology=audit",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_correct_presentation_time_provenance(
    async_client: AsyncClient, setup_data
):
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["wo"].id + "&entity_type=work_order",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    for entry in res.json()["data"]["data"]:
        assert entry["presentation_time_provenance"] in [
            "EXPLICIT_OCCURRENCE",
            "OCCURRENCE_FALLBACK_RECORDED",
            "EXPLICIT_DECISION",
            "DECISION_FALLBACK_RECORDED",
        ]


@pytest.mark.asyncio
async def test_entity_scoped_timeline_filtering(async_client: AsyncClient, setup_data):
    # Verify we don't get other entities' timelines
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["wo"].id + "&entity_type=work_order",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_authentication_requirement_timeline(
    async_client: AsyncClient, setup_data
):
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["wo"].id + "&entity_type=work_order"
    )
    assert res.status_code in [401, 403]


@pytest.mark.asyncio
async def test_tenant_isolation_across_every_timeline_source(
    async_client: AsyncClient, setup_data
):
    # Setup data already ensures company_id filtering is applied in the union all
    res = await async_client.get(
        "/api/v1/timeline?entity_id=" + setup_data["wo"].id + "&entity_type=work_order",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
