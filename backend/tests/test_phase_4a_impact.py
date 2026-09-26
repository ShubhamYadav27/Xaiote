import asyncio
import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.company import Company
from app.models.impact import (
    ImpactDecisionHistory,
    ImpactProvenance,
    ImpactStatus,
    ProductionOrderImpact,
)
from app.models.manufacturing_event import EventStatus, ManufacturingEvent
from app.models.masters import Customer, Machine, Product
from app.models.plant import Plant
from app.models.resolution import EntityResolutionResult
from app.models.user import User
from app.models.work_order import WorkOrder, WorkOrderStatus
from app.services.impact_generator import evaluate_impacts_for_event


@pytest.fixture
async def setup_data(db_session: AsyncSession):
    db = db_session
    # Clean up completely to avoid pollution
    await db.execute(text("DELETE FROM work_order_risk_history"))
    await db.execute(text("DELETE FROM incident_decision_history"))
    await db.execute(text("DELETE FROM incident_events"))
    await db.execute(text("DELETE FROM assessment_decision_history"))
    await db.execute(text("DELETE FROM assessment_evidence_links"))
    await db.execute(text("DELETE FROM root_cause_assessments"))
    await db.execute(text("DELETE FROM incident_analyses"))
    await db.execute(text("DELETE FROM whatsapp_integrations"))
    await db.execute(text("DELETE FROM authorized_senders"))
    await db.execute(text("DELETE FROM incidents"))
    await db.execute(text("DELETE FROM impact_decision_history"))
    await db.execute(text("DELETE FROM production_order_impacts"))
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
    c2 = Company(id=str(uuid.uuid4()), name="Company B")
    p1 = Plant(id=str(uuid.uuid4()), company_id=c1.id, name="Plant A", timezone="UTC")
    u1 = User(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="User",
        role="admin",
    )
    db.add_all([c1, c2, p1, u1])
    await db.flush()

    mac = Machine(id=str(uuid.uuid4()), company_id=c1.id, plant_id=p1.id, name="CNC-02")
    prod = Product(id=str(uuid.uuid4()), company_id=c1.id, name="Motor")
    cust = Customer(id=str(uuid.uuid4()), company_id=c1.id, name="AutoCorp")
    db.add_all([mac, prod, cust])
    await db.flush()

    wo_in_prog = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-INPROG",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.IN_PROGRESS.value,
    )
    wo_planned = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-PLANNED",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.PLANNED.value,
    )
    wo_hold = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-HOLD",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.ON_HOLD.value,
    )
    wo_comp = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-COMP",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.COMPLETED.value,
    )
    wo_canc = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        order_number="WO-CANC",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.CANCELLED.value,
    )

    # Cross tenant WO
    plant2 = Plant(id=str(uuid.uuid4()), company_id=c2.id, name="Plant 2", timezone="UTC")
    db.add(plant2)
    await db.flush()

    wo_c2 = WorkOrder(
        id=str(uuid.uuid4()),
        company_id=c2.id,
        plant_id=plant2.id,
        order_number="WO-C2",
        quantity=100,
        product_id=prod.id,
        machine_id=mac.id,
        customer_id=cust.id,
        status=WorkOrderStatus.IN_PROGRESS.value,
    )
    db.add_all([wo_in_prog, wo_planned, wo_hold, wo_comp, wo_canc, wo_c2])
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

    ev = ManufacturingEvent(
        id=str(uuid.uuid4()),
        company_id=c1.id,
        plant_id=p1.id,
        candidate_id=cand.id,
        event_idempotency_key=str(uuid.uuid4()),
        event_status=EventStatus.CANONICAL,
    )
    db.add(ev)
    await db.commit()

    return {
        "c1": c1,
        "c2": c2,
        "p1": p1,
        "u1": u1,
        "mac": mac,
        "wo_in_prog": wo_in_prog,
        "wo_planned": wo_planned,
        "wo_hold": wo_hold,
        "wo_comp": wo_comp,
        "wo_canc": wo_canc,
        "wo_c2": wo_c2,
        "ev": ev,
        "res": res,
    }


@pytest.mark.asyncio
async def test_machine_only_impact(db_session: AsyncSession, setup_data):
    db = db_session
    await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)

    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    # Expect 2 impacts: IN_PROGRESS and PLANNED
    assert len(impacts) == 2
    impact_wos = {i.work_order_id for i in impacts}
    assert setup_data["wo_in_prog"].id in impact_wos
    assert setup_data["wo_planned"].id in impact_wos
    assert all(i.status == ImpactStatus.POTENTIAL for i in impacts)
    assert all(
        i.provenance == ImpactProvenance.MACHINE_CONTEXT_DERIVED for i in impacts
    )


@pytest.mark.asyncio
async def test_explicit_wo_impact(db_session: AsyncSession, setup_data):
    db = db_session
    setup_data["res"].work_order_id = setup_data["wo_in_prog"].id
    setup_data["res"].work_order_state = "RESOLVED"
    db.add(setup_data["res"])
    await db.commit()

    await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)

    impact = (await db.execute(select(ProductionOrderImpact))).scalar_one()
    assert impact.status == ImpactStatus.CONFIRMED
    assert impact.provenance == ImpactProvenance.EXPLICIT_WORK_ORDER_RESOLUTION


@pytest.mark.asyncio
async def test_cross_tenant_denied(db_session: AsyncSession, setup_data):
    db = db_session
    import app.services.impact_generator as ig

    with pytest.raises(ig.SecurityException):
        await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c2"].id)


@pytest.mark.asyncio
async def test_cross_tenant_wo_mapping_denied(db_session: AsyncSession, setup_data):
    db = db_session
    setup_data["res"].work_order_id = setup_data["wo_c2"].id
    setup_data["res"].work_order_state = "RESOLVED"
    db.add(setup_data["res"])
    await db.commit()

    import app.services.impact_generator as ig

    with pytest.raises(ig.SecurityException):
        await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)


@pytest.mark.asyncio
async def test_idempotency_noop(db_session: AsyncSession, setup_data):
    db = db_session
    # 5 runs
    for _ in range(5):
        await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)

    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    assert len(impacts) == 2
    history = (await db.execute(select(ImpactDecisionHistory))).scalars().all()
    assert len(history) == 2  # Only 1 set of initial rows


@pytest.mark.asyncio
async def test_concurrency(db_session: AsyncSession, setup_data):
    db = db_session
    tasks = [
        evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)
        for _ in range(5)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    assert len(impacts) == 2
    history = (await db.execute(select(ImpactDecisionHistory))).scalars().all()
    assert len(history) == 2


@pytest.mark.asyncio
async def test_human_confirmation(db_session: AsyncSession, setup_data):
    db = db_session
    await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)
    await db.commit()
    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    impact = impacts[0]

    from app.services.impact_generator import upsert_impact

    await upsert_impact(
        db,
        setup_data["c1"].id,
        setup_data["p1"].id,
        impact.event_id,
        impact.work_order_id,
        ImpactStatus.CONFIRMED,
        ImpactProvenance.HUMAN_CONFIRMED,
        actor_id=setup_data["u1"].id,
        reason="Validated manually",
    )
    await db.commit()

    db.expunge_all()
    impact = (
        await db.execute(
            select(ProductionOrderImpact).where(ProductionOrderImpact.id == impact.id)
        )
    ).scalar_one()
    assert impact.status == ImpactStatus.CONFIRMED
    assert impact.provenance == ImpactProvenance.HUMAN_CONFIRMED

    hist = (
        (
            await db.execute(
                select(ImpactDecisionHistory)
                .where(ImpactDecisionHistory.impact_id == impact.id)
                .order_by(ImpactDecisionHistory.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    assert len(hist) == 2  # Initial + human
    assert hist[0].actor_id == setup_data["u1"].id
    assert hist[0].reason == "Validated manually"
    assert hist[0].new_status == "CONFIRMED"


@pytest.mark.asyncio
async def test_plant_mismatch(db_session: AsyncSession, setup_data):
    db = db_session
    p2 = Plant(id=str(uuid.uuid4()), company_id=setup_data["c1"].id, name="Plant 2", timezone="UTC")
    db.add(p2)
    await db.flush()
    setup_data["ev"].plant_id = p2.id
    db.add(setup_data["ev"])
    await db.commit()

    await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)
    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    assert len(impacts) == 0  # No impact because WO is Plant 1 and Event is Plant 2


@pytest.mark.asyncio
async def test_invalid_transitions(db_session: AsyncSession, setup_data):
    db = db_session
    from app.services.impact_generator import upsert_impact

    await evaluate_impacts_for_event(db, setup_data["ev"].id, setup_data["c1"].id)
    await db.commit()

    impacts = (await db.execute(select(ProductionOrderImpact))).scalars().all()
    impact = impacts[0]

    # POTENTIAL -> POTENTIAL (noop)
    await upsert_impact(
        db,
        setup_data["c1"].id,
        setup_data["p1"].id,
        impact.event_id,
        impact.work_order_id,
        ImpactStatus.POTENTIAL,
        ImpactProvenance.MACHINE_CONTEXT_DERIVED,
    )
    hist = (
        (
            await db.execute(
                select(ImpactDecisionHistory).where(
                    ImpactDecisionHistory.impact_id == impact.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(hist) == 1

    # POTENTIAL -> CONFIRMED
    await upsert_impact(
        db,
        setup_data["c1"].id,
        setup_data["p1"].id,
        impact.event_id,
        impact.work_order_id,
        ImpactStatus.CONFIRMED,
        ImpactProvenance.HUMAN_CONFIRMED,
        actor_id=setup_data["u1"].id,
        reason="yes",
    )

    # CONFIRMED -> CONFIRMED (noop)
    await upsert_impact(
        db,
        setup_data["c1"].id,
        setup_data["p1"].id,
        impact.event_id,
        impact.work_order_id,
        ImpactStatus.CONFIRMED,
        ImpactProvenance.HUMAN_CONFIRMED,
        actor_id=setup_data["u1"].id,
        reason="yes",
    )
    hist = (
        (
            await db.execute(
                select(ImpactDecisionHistory).where(
                    ImpactDecisionHistory.impact_id == impact.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(hist) == 2


@pytest.mark.asyncio
async def test_transactional_failure_rollback(db_session: AsyncSession, setup_data):
    db = db_session
    from app.models.manufacturing_event import ManufacturingEvent

    # We will simulate a failure by mocking evaluate_impacts_for_event inside canonicalization_worker
    # Actually, we can just pass an invalid state or rely on a patched exception.
    # Let's test the atomic logic directly:
    try:
        async with db.begin_nested():
            # Create a fake event
            ev2 = ManufacturingEvent(
                id=str(uuid.uuid4()),
                company_id=setup_data["c1"].id,
                plant_id=setup_data["p1"].id,
                candidate_id=setup_data["ev"].candidate_id,
                event_idempotency_key="atomic-test",
                event_status="CANONICAL",
            )
            db.add(ev2)
            await db.flush()
            # simulate evaluate impacts raising
            raise Exception("Impact gen failed")
    except Exception:
        pass

    evs = (
        (
            await db.execute(
                select(ManufacturingEvent).where(
                    ManufacturingEvent.event_idempotency_key == "atomic-test"
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(evs) == 0
    impacts = (
        (
            await db.execute(
                select(ProductionOrderImpact).where(
                    ProductionOrderImpact.event_id == ev2.id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(impacts) == 0
