import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import text
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
    IncidentStatus,
)
from app.models.manufacturing_event import EventStatus, ManufacturingEvent
from app.models.masters import Customer, Machine, Product
from app.models.plant import Plant
from app.models.resolution import EntityResolutionResult
from app.models.risk import RiskState
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderStatus


@pytest.fixture
async def setup_data(db_session: AsyncSession):
    db = db_session
    # Correct order
    await db.execute(text("DELETE FROM work_order_risk_history"))
    await db.execute(text("DELETE FROM impact_decision_history"))
    await db.execute(text("DELETE FROM production_order_impacts"))
    await db.execute(text("DELETE FROM incident_decision_history"))
    await db.execute(text("DELETE FROM incident_events"))
    await db.execute(text("DELETE FROM assessment_decision_history"))
    await db.execute(text("DELETE FROM assessment_evidence_links"))
    await db.execute(text("DELETE FROM root_cause_assessments"))
    await db.execute(text("DELETE FROM incident_analyses"))
    await db.execute(text("DELETE FROM whatsapp_integrations"))
    await db.execute(text("DELETE FROM authorized_senders"))
    await db.execute(text("DELETE FROM incidents"))
    await db.execute(text("DELETE FROM manufacturing_event_revisions"))
    await db.execute(text("DELETE FROM manufacturing_events"))
    await db.execute(text("DELETE FROM canonicalization_jobs"))
    await db.execute(text("DELETE FROM entity_resolution_results"))
    await db.execute(text("DELETE FROM extracted_event_candidates"))
    await db.execute(text("DELETE FROM communication_transcripts"))
    await db.execute(text("DELETE FROM communication_attachments"))
    await db.execute(text("DELETE FROM communication_messages"))
    await db.execute(text("DELETE FROM work_orders"))
    await db.execute(text("DELETE FROM machines"))
    await db.execute(text("DELETE FROM products"))
    await db.execute(text("DELETE FROM customers"))
    await db.execute(text("DELETE FROM import_audits"))
    await db.execute(text("DELETE FROM import_jobs"))
    await db.execute(text("DELETE FROM refresh_tokens"))
    await db.execute(text("DELETE FROM users"))
    await db.execute(text("DELETE FROM plants"))
    await db.execute(text("DELETE FROM companies"))
    await db.commit()

    c1 = Company(id=str(uuid.uuid4()), name="Company A")
    p1 = Plant(id=str(uuid.uuid4()), company_id=c1.id, name="Plant A", timezone="UTC")
    u1 = User(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="User",
        role="USER",
    )
    db.add_all([c1, p1, u1])
    await db.flush()

    mac = Machine(id=str(uuid.uuid4()), company_id=c1.id, plant_id=p1.id, name="CNC-02")
    prod = Product(id=str(uuid.uuid4()), company_id=c1.id, name="Motor")
    cust = Customer(id=str(uuid.uuid4()), company_id=c1.id, name="AutoCorp")
    db.add_all([mac, prod, cust])
    await db.flush()

    now = datetime.now(timezone.utc)
    wo = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-INPROG",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.IN_PROGRESS.value,
        due_date=now + timedelta(days=2),
    )
    db.add(wo)
    await db.flush()

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
    cand = ExtractedEventCandidate(
        id=str(uuid.uuid4()), company_id=c1.id, transcript_id=tr.id
    )
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
        candidate_id=cand.id,
        event_idempotency_key=str(uuid.uuid4()),
        event_status=EventStatus.CANONICAL,
    )
    db.add(ev1)
    await db.flush()

    token = jwt.encode({"sub": str(u1.id)}, settings.JWT_SECRET, algorithm="HS256")
    await db.commit()

    return {
        "company": c1,
        "plant": p1,
        "user": u1,
        "machine": mac,
        "wo": wo,
        "ev1": ev1,
        "headers": {"Authorization": f"Bearer {token}"},
        "token": token,
    }


@pytest.mark.asyncio
async def test_incident_creation_and_linking(db_session: AsyncSession, setup_data):
    from app.services.incident_service import create_incident_from_failure

    incident = await create_incident_from_failure(
        db_session, setup_data["ev1"], "Machine Failure", setup_data["user"].id
    )
    await db_session.commit()
    assert incident.status == IncidentStatus.ACTIVE


@pytest.mark.asyncio
async def test_incident_resolution_risk_evaluation(
    db_session: AsyncSession, setup_data
):
    from app.services.incident_service import (
        create_incident_from_failure,
        resolve_incident,
    )

    inc = await create_incident_from_failure(db_session, setup_data["ev1"], "Failure")

    imp = ProductionOrderImpact(
        id=str(uuid.uuid4()),
        company_id=setup_data["company"].id,
        plant_id=setup_data["plant"].id,
        event_id=setup_data["ev1"].id,
        work_order_id=setup_data["wo"].id,
        incident_id=inc.id,
        status=ImpactStatus.CONFIRMED,
        provenance=ImpactProvenance.MACHINE_CONTEXT_DERIVED,
    )
    db_session.add(imp)
    await db_session.commit()

    # Check risk before resolve
    from app.services.risk_service import fetch_current_risk

    assert (
        await fetch_current_risk(
            db_session, setup_data["wo"].id, datetime.now(timezone.utc)
        )
        == RiskState.AT_RISK
    )

    inc, changes = await resolve_incident(
        db_session, inc.id, setup_data["company"].id, setup_data["user"].id
    )
    assert inc.status == IncidentStatus.RESOLVED
    assert changes[0]["new_state"] == "ON_TRACK"

    # Check risk after resolve
    assert (
        await fetch_current_risk(
            db_session, setup_data["wo"].id, datetime.now(timezone.utc)
        )
        == RiskState.ON_TRACK
    )


@pytest.mark.asyncio
async def test_legacy_impact_still_counted(db_session: AsyncSession, setup_data):
    imp = ProductionOrderImpact(
        id=str(uuid.uuid4()),
        company_id=setup_data["company"].id,
        plant_id=setup_data["plant"].id,
        event_id=setup_data["ev1"].id,
        work_order_id=setup_data["wo"].id,
        incident_id=None,
        status=ImpactStatus.CONFIRMED,
        provenance=ImpactProvenance.MACHINE_CONTEXT_DERIVED,
    )
    db_session.add(imp)
    await db_session.commit()
    from app.services.risk_service import fetch_current_risk

    assert (
        await fetch_current_risk(
            db_session, setup_data["wo"].id, datetime.now(timezone.utc)
        )
        == RiskState.AT_RISK
    )


@pytest.mark.asyncio
async def test_api_list_incidents(async_client: AsyncClient, setup_data):
    res = await async_client.get("/api/v1/incidents", headers=setup_data["headers"])
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_api_resolve_incident(
    async_client: AsyncClient, db_session: AsyncSession, setup_data
):
    from app.services.incident_service import create_incident_from_failure

    inc = await create_incident_from_failure(db_session, setup_data["ev1"], "Failure")
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/incidents/{inc.id}/resolve",
        json={"reason": "test"},
        headers=setup_data["headers"],
    )
    assert res.status_code == 200
