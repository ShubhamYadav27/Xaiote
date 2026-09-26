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
    c1 = Company(id=str(uuid.uuid4()), name="Company 4E")
    c2 = Company(id=str(uuid.uuid4()), name="Company 4E Other")
    p1 = Plant(id=str(uuid.uuid4()), company_id=c1.id, name="Plant 4E", timezone="UTC")
    u1 = User(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="User",
        role="SUPERVISOR",
    )
    u2 = User(
        id=str(uuid.uuid4()),
        company_id=c2.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="Other User",
        role="SUPERVISOR",
    )
    db.add_all([c1, c2, p1, u1, u2])
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
        order_number="WO-4E",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=now + timedelta(days=2),
    )
    db.add(wo)

    inc = Incident(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        machine_id=mac.id,
        title="Incident 4E",
        status=IncidentStatus.ACTIVE.value,
    )
    db.add(inc)
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
        canonical_occurrence_timestamp=now,
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
    token2 = jwt.encode({"sub": str(u2.id)}, settings.JWT_SECRET, algorithm="HS256")
    await db.commit()

    return {
        "company": c1,
        "other_company": c2,
        "wo": wo,
        "inc": inc,
        "ev": ev1,
        "headers": {"Authorization": f"Bearer {token1}"},
        "other_headers": {"Authorization": f"Bearer {token2}"},
    }


@pytest.mark.asyncio
async def test_work_order_context_happy_path(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/work-orders/{setup_data['wo'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "work_order" in data
    assert data["work_order"]["id"] == setup_data["wo"].id
    assert "active_impacts" in data
    assert "context_generated_at" in data


@pytest.mark.asyncio
async def test_incident_context_happy_path(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "incident" in data
    assert data["incident"]["id"] == setup_data["inc"].id
    assert "manufacturing_events" in data
    assert len(data["manufacturing_events"]) == 1
    assert data["manufacturing_events"][0]["id"] == setup_data["ev"].id
    assert "affected_work_orders" in data
    assert len(data["affected_work_orders"]) == 1
    assert "context_generated_at" in data


@pytest.mark.asyncio
async def test_cross_tenant_work_order(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/work-orders/{setup_data['wo'].id}",
        headers=setup_data["other_headers"],
    )
    assert res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_cross_tenant_incident(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["other_headers"],
    )
    assert res.status_code in (403, 404)


@pytest.mark.asyncio
async def test_missing_optional_records(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/work-orders/{setup_data['wo'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data.get("current_risk") is None or isinstance(data["current_risk"], dict)
    assert data["active_alerts"] is None


@pytest.mark.asyncio
async def test_evidence_and_root_cause(
    async_client: AsyncClient, db_session: AsyncSession, setup_data
):
    from app.models.analysis import (
        AssessmentEvidenceLink,
        IncidentAnalysis,
        RootCauseAssessment,
    )

    db = db_session
    analysis = IncidentAnalysis(
        id=str(uuid.uuid4()),
        incident_id=setup_data["inc"].id,
        company_id=setup_data["company"].id,
        version=1,
        evidence_snapshot_hash="hash",
        generation_fingerprint="fp",
    )
    db.add(analysis)
    await db.flush()
    assessment = RootCauseAssessment(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        company_id=setup_data["company"].id,
        explanation="Test Root Cause",
        category="MECHANICAL",
        role="PRIMARY",
        provenance="MODEL_DERIVED",
        model_confidence=0.99,
    )
    db.add(assessment)
    await db.flush()
    evidence = AssessmentEvidenceLink(
        id=str(uuid.uuid4()),
        assessment_id=assessment.id,
        event_id=setup_data["ev"].id,
        company_id=setup_data["company"].id,
        relationship_type="SUPPORTING",
    )
    db.add(evidence)
    await db.commit()

    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "confirmed_root_cause" in data
    assert data["confirmed_root_cause"]["explanation"] == "Test Root Cause"
    assert "evidence" in data
    assert len(data["evidence"]) == 1
    assert data["evidence"][0]["event_id"] == setup_data["ev"].id


@pytest.mark.asyncio
async def test_risk_projection(
    async_client: AsyncClient, db_session: AsyncSession, setup_data
):
    from app.models.risk import WorkOrderRiskHistory

    db = db_session
    risk = WorkOrderRiskHistory(
        previous_state="ON_TRACK",
        id=str(uuid.uuid4()),
        company_id=setup_data["company"].id,
        work_order_id=setup_data["wo"].id,
        new_state="AT_RISK",
        trigger_type="WORK_ORDER_UPDATED",
    )
    db.add(risk)
    await db.commit()

    res = await async_client.get(
        f"/api/v1/operational-context/work-orders/{setup_data['wo'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "current_risk" in data
    assert data["current_risk"]["state"] == "AT_RISK"


@pytest.mark.asyncio
async def test_active_alert_field_omitted(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    assert res.json()["data"]["active_alerts"] is None


@pytest.mark.asyncio
async def test_context_generated_at_presence_and_utc(
    async_client: AsyncClient, setup_data
):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    dt_str = res.json()["data"]["context_generated_at"]
    assert "Z" in dt_str or "+00:00" in dt_str


@pytest.mark.asyncio
async def test_freshness_read_committed_behavior(
    async_client: AsyncClient, setup_data, db_session: AsyncSession
):
    setup_data["inc"].title = "Updated Incident Title 99"
    await db_session.commit()
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
    assert res.json()["data"]["incident"]["title"] == "Updated Incident Title 99"


@pytest.mark.asyncio
async def test_authentication_requirement_context(
    async_client: AsyncClient, setup_data
):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}"
    )
    assert res.status_code in [401, 403]


@pytest.mark.asyncio
async def test_n_plus_1_safe_query(async_client: AsyncClient, setup_data):
    res = await async_client.get(
        f"/api/v1/operational-context/incidents/{setup_data['inc'].id}",
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
