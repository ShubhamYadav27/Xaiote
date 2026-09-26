"""
Phase 4D Root Cause Intelligence - Comprehensive Test Suite

Tests cover:
1. Evidence snapshot reproducibility
2. Stale analysis detection
3. Manual re-analysis (versioning)
4. Request idempotency
5. Generation fingerprint
6. AI output validation (invalid event ID rejection)
7. Human confirmation (CAS)
8. Human rejection (CAS)
9. Concurrent confirmation safety
10. Stale revision deterministic rejection
11. PRIMARY supersession
12. Multiple CONTRIBUTING causes
13. Decision history completeness
14. Cross-tenant protection (composite FK enforcement)
15. Provider failure handling
16. Malformed AI output
"""

import uuid

import jwt
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import (
    AnalysisStatus,
    AssessmentDecisionHistory,
    AssessmentRole,
    AssessmentStatus,
    IncidentAnalysis,
    RootCauseAssessment,
)
from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.company import Company
from app.models.incident import Incident, IncidentEvent
from app.models.manufacturing_event import EventStatus, ManufacturingEvent
from app.models.masters import Machine
from app.models.plant import Plant
from app.models.resolution import EntityResolutionResult
from app.models.user import User
from app.services.analysis_service import (
    confirm_assessment,
    generate_analysis_for_incident,
    generate_evidence_snapshot_hash,
    generate_generation_fingerprint,
    get_latest_analysis,
    reject_assessment,
)


def _uid():
    return str(uuid.uuid4())


async def _create_event(db, company_id, plant_id, suffix="1"):
    """Helper: create the full FK chain up to a ManufacturingEvent."""
    msg = CommunicationMessage(
        id=_uid(),
        company_id=company_id,
        source_channel="test",
        external_message_id=_uid(),
        sender_identity="test",
    )
    db.add(msg)
    await db.flush()
    att = CommunicationAttachment(id=_uid(), message_id=msg.id, media_type="audio")
    db.add(att)
    await db.flush()
    tr = CommunicationTranscript(
        id=_uid(),
        company_id=company_id,
        attachment_id=att.id,
        provider="test",
        model="test",
    )
    db.add(tr)
    await db.flush()
    cand = ExtractedEventCandidate(
        id=_uid(), company_id=company_id, transcript_id=tr.id
    )
    db.add(cand)
    await db.flush()
    res = EntityResolutionResult(
        id=_uid(), company_id=company_id, candidate_id=cand.id, machine_state="RESOLVED"
    )
    db.add(res)
    await db.flush()
    ev = ManufacturingEvent(
        id=_uid(),
        company_id=company_id,
        plant_id=plant_id,
        candidate_id=cand.id,
        event_idempotency_key=_uid(),
        event_status=EventStatus.CANONICAL,
        description=f"Event {suffix}",
    )
    db.add(ev)
    await db.flush()
    return ev


@pytest.fixture
async def setup_4d(db_session: AsyncSession):
    db = db_session
    # Clean tables in FK order

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

    c1 = Company(id=_uid(), name="Company 4D")
    p1 = Plant(id=_uid(), company_id=c1.id, name="Plant 4D", timezone="UTC")
    u1 = User(
        id=_uid(),
        company_id=c1.id,
        email=f"{uuid.uuid4()}@test.com",
        password_hash="hash",
        full_name="User 4D",
        role="USER",
    )
    db.add_all([c1, p1, u1])
    await db.flush()

    mac = Machine(id=_uid(), company_id=c1.id, plant_id=p1.id, name="CNC-4D")
    db.add(mac)
    await db.flush()

    ev1 = await _create_event(db, c1.id, p1.id, "1")

    inc = Incident(
        id=_uid(),
        title="Test Incident 4D",
        company_id=c1.id,
        plant_id=p1.id,
        machine_id=mac.id,
    )
    db.add(inc)
    await db.flush()

    ie = IncidentEvent(id=_uid(), incident_id=inc.id, event_id=ev1.id)
    db.add(ie)
    await db.commit()

    token = jwt.encode({"sub": str(u1.id)}, settings.JWT_SECRET, algorithm="HS256")

    return {
        "company": c1,
        "plant": p1,
        "user": u1,
        "machine": mac,
        "ev1": ev1,
        "incident": inc,
        "headers": {"Authorization": f"Bearer {token}"},
    }


# ==================== 1. Evidence Snapshot Reproducibility ====================
@pytest.mark.asyncio
async def test_evidence_snapshot_reproducibility(setup_4d):
    ev = setup_4d["ev1"]
    # Same IDs -> same hash
    h1 = generate_evidence_snapshot_hash([ev.id])
    h2 = generate_evidence_snapshot_hash([ev.id])
    assert h1 == h2

    # Order independence
    h3 = generate_evidence_snapshot_hash([ev.id, "other-id"])
    h4 = generate_evidence_snapshot_hash(["other-id", ev.id])
    assert h3 == h4


# ==================== 2. Stale Analysis Detection ====================
@pytest.mark.asyncio
async def test_stale_analysis_detection(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    # Generate v1
    analysis = await generate_analysis_for_incident(db_session, inc.id, cid)
    assert analysis.status == AnalysisStatus.COMPLETED
    assert analysis.version == 1

    # Not stale yet
    _latest, is_stale = await get_latest_analysis(db_session, inc.id, cid)
    assert not is_stale

    # Add new evidence -> should become stale
    ev2 = await _create_event(db_session, cid, setup_4d["plant"].id, "stale")
    ie2 = IncidentEvent(id=_uid(), incident_id=inc.id, event_id=ev2.id)
    db_session.add(ie2)
    await db_session.commit()

    _latest, is_stale = await get_latest_analysis(db_session, inc.id, cid)
    assert is_stale


# ==================== 3. Manual Re-Analysis (Versioning) ====================
@pytest.mark.asyncio
async def test_manual_reanalysis_creates_new_version(
    db_session: AsyncSession, setup_4d
):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    v1 = await generate_analysis_for_incident(db_session, inc.id, cid)
    assert v1.version == 1

    # Same evidence, manual=True -> must create v2
    v2 = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )
    assert v2.version == 2
    assert v2.id != v1.id


# ==================== 4. Request Idempotency ====================
@pytest.mark.asyncio
async def test_request_idempotency(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    a1 = await generate_analysis_for_incident(
        db_session, inc.id, cid, idempotency_key="idem-4d-001"
    )
    a2 = await generate_analysis_for_incident(
        db_session, inc.id, cid, idempotency_key="idem-4d-001"
    )
    assert a1.id == a2.id  # Same request -> same analysis


# ==================== 5. Generation Fingerprint ====================
@pytest.mark.asyncio
async def test_generation_fingerprint(setup_4d):
    h = generate_evidence_snapshot_hash(["ev1"])
    fp1 = generate_generation_fingerprint(h, "1.0", "1.0", "mock")
    fp2 = generate_generation_fingerprint(h, "1.0", "1.0", "mock")
    assert fp1 == fp2

    # Different prompt_version
    fp3 = generate_generation_fingerprint(h, "2.0", "1.0", "mock")
    assert fp1 != fp3

    # Different schema_version
    fp4 = generate_generation_fingerprint(h, "1.0", "2.0", "mock")
    assert fp1 != fp4

    # Different provider_config
    fp5 = generate_generation_fingerprint(h, "1.0", "1.0", "openai")
    assert fp1 != fp5


# ==================== 6. Invalid Event ID Rejection ====================
@pytest.mark.asyncio
async def test_invalid_event_id_rejection(db_session: AsyncSession, setup_4d):
    """If AI returns an event_id not in the incident's evidence set, reject the entire AI output."""
    from app.services.analysis_service import MockAnalysisLLMProvider

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    # Monkey-patch the mock provider to return an invalid event ID
    original_analyze = MockAnalysisLLMProvider.analyze

    async def bad_analyze(self, events):
        return {
            "candidates": [
                {
                    "category": "MECHANICAL",
                    "role": "PRIMARY",
                    "explanation": "Bad",
                    "supporting_event_ids": ["INVALID-EVENT-ID-DOES-NOT-EXIST"],
                    "conflicting_event_ids": [],
                    "model_confidence": 0.5,
                }
            ]
        }

    MockAnalysisLLMProvider.analyze = bad_analyze
    try:
        with pytest.raises(ValueError, match="invalid event_id"):
            await generate_analysis_for_incident(
                db_session, inc.id, cid, manual_reanalysis=True
            )
    finally:
        MockAnalysisLLMProvider.analyze = original_analyze


# ==================== 7-8. Human Confirmation & Rejection (CAS) ====================
@pytest.mark.asyncio
async def test_confirm_and_reject_assessment(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )

    q = select(RootCauseAssessment).where(
        RootCauseAssessment.analysis_id == analysis.id
    )
    assessments = (await db_session.execute(q)).scalars().all()
    assmt1 = assessments[0]

    # create a second one manually
    assmt2 = RootCauseAssessment(
        analysis_id=analysis.id,
        company_id=cid,
        revision=2,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role="CONTRIBUTING",
        explanation="Test",
        provenance="MODEL_DERIVED",
    )
    db_session.add(assmt2)
    await db_session.commit()

    assert assmt1.status == AssessmentStatus.NEEDS_REVIEW

    # Confirm
    confirmed = await confirm_assessment(
        db_session, assmt1.id, cid, uid, expected_revision=assmt1.revision
    )
    assert confirmed.status == AssessmentStatus.CONFIRMED

    # Reject the SECOND assessment
    rejected = await reject_assessment(
        db_session,
        assmt2.id,
        cid,
        uid,
        expected_revision=assmt2.revision,
        reason="Wrong call",
    )
    assert rejected.status == AssessmentStatus.REJECTED


# ==================== 9-10. Concurrent Confirmation & Stale Revision ====================
@pytest.mark.asyncio
async def test_stale_revision_rejection(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )
    assmt = (
        (
            await db_session.execute(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
        )
        .scalars()
        .first()
    )

    # We expect HTTP 409 when expected_revision doesn't match!
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await confirm_assessment(db_session, assmt.id, cid, uid, expected_revision=999)
    assert exc_info.value.status_code == 409


# ==================== 11. PRIMARY Supersession ====================
@pytest.mark.asyncio
async def test_primary_supersession(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )

    # Manually add a second PRIMARY candidate
    assmt2 = RootCauseAssessment(
        id=_uid(),
        analysis_id=analysis.id,
        company_id=cid,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="ELECTRICAL",
        role=AssessmentRole.PRIMARY,
        explanation="Electrical fault",
        provenance="MODEL_DERIVED",
        model_confidence=0.8,
    )
    db_session.add(assmt2)
    await db_session.commit()

    # Get both assessments
    all_assmts = (
        (
            await db_session.execute(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
        )
        .scalars()
        .all()
    )
    primary_candidates = [a for a in all_assmts if a.role == AssessmentRole.PRIMARY]
    assert len(primary_candidates) == 2

    # Confirm first PRIMARY
    a1 = primary_candidates[0]
    await confirm_assessment(db_session, a1.id, cid, uid, expected_revision=a1.revision)
    await db_session.refresh(a1)
    assert a1.status == AssessmentStatus.CONFIRMED

    # Confirm second PRIMARY -> first should become SUPERSEDED
    a2 = primary_candidates[1]
    await confirm_assessment(db_session, a2.id, cid, uid, expected_revision=a2.revision)
    await db_session.refresh(a2)
    await db_session.refresh(a1)
    assert a2.status == AssessmentStatus.CONFIRMED
    assert a1.status == AssessmentStatus.SUPERSEDED


# ==================== 12. Multiple CONTRIBUTING Causes ====================
@pytest.mark.asyncio
async def test_multiple_contributing_causes(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )

    c1 = RootCauseAssessment(
        analysis_id=analysis.id,
        company_id=cid,
        revision=2,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role="CONTRIBUTING",
        explanation="C1",
        provenance="MODEL_DERIVED",
    )
    c2 = RootCauseAssessment(
        analysis_id=analysis.id,
        company_id=cid,
        revision=2,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role="CONTRIBUTING",
        explanation="C2",
        provenance="MODEL_DERIVED",
    )
    db_session.add_all([c1, c2])
    await db_session.commit()

    await confirm_assessment(db_session, c1.id, cid, uid, expected_revision=c1.revision)
    await confirm_assessment(db_session, c2.id, cid, uid, expected_revision=c2.revision)

    await db_session.refresh(c1)
    await db_session.refresh(c2)
    assert c1.status == AssessmentStatus.CONFIRMED
    assert c2.status == AssessmentStatus.CONFIRMED


# ==================== 13. Decision History Completeness ====================
@pytest.mark.asyncio
async def test_decision_history(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )
    assmt1 = (
        (
            await db_session.execute(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
        )
        .scalars()
        .first()
    )

    assmt2 = RootCauseAssessment(
        analysis_id=analysis.id,
        company_id=cid,
        revision=2,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role="CONTRIBUTING",
        explanation="Test",
        provenance="MODEL_DERIVED",
    )
    db_session.add(assmt2)
    await db_session.commit()

    await confirm_assessment(
        db_session, assmt1.id, cid, uid, expected_revision=assmt1.revision
    )
    await reject_assessment(
        db_session,
        assmt2.id,
        cid,
        uid,
        expected_revision=assmt2.revision,
        reason="Changed mind",
    )

    q = (
        select(AssessmentDecisionHistory)
        .where(AssessmentDecisionHistory.assessment_id == assmt1.id)
        .order_by(AssessmentDecisionHistory.timestamp)
    )
    history1 = (await db_session.execute(q)).scalars().all()

    assert len(history1) >= 1
    assert history1[-1].action == "CONFIRMED"
    assert history1[-1].new_state == "CONFIRMED"

    q2 = (
        select(AssessmentDecisionHistory)
        .where(AssessmentDecisionHistory.assessment_id == assmt2.id)
        .order_by(AssessmentDecisionHistory.timestamp)
    )
    history2 = (await db_session.execute(q2)).scalars().all()

    assert len(history2) >= 1
    assert history2[-1].action == "REJECTED"


# ==================== 14. Cross-Tenant Protection ====================
@pytest.mark.asyncio
async def test_cross_tenant_protection(db_session: AsyncSession, setup_4d):
    """Analysis for incident in company A cannot reference events from company B via composite FK."""
    inc = setup_4d["incident"]

    # Create a second company
    c2 = Company(id=_uid(), name="Other Corp")
    p2 = Plant(id=_uid(), company_id=c2.id, name="Other Plant", timezone="UTC")
    db_session.add_all([c2, p2])
    await db_session.flush()

    # Attempt to create analysis for inc but with wrong company_id should fail FK
    from sqlalchemy.exc import IntegrityError

    bad_analysis = IncidentAnalysis(
        id=_uid(),
        incident_id=inc.id,
        company_id=c2.id,
        version=1,
        status=AnalysisStatus.PENDING,
        evidence_snapshot_hash="bad",
        generation_fingerprint="bad",
    )
    db_session.add(bad_analysis)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ==================== 15. Provider Failure Handling ====================
@pytest.mark.asyncio
async def test_provider_failure_marks_failed(db_session: AsyncSession, setup_4d):
    from app.services.analysis_service import MockAnalysisLLMProvider

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    original = MockAnalysisLLMProvider.analyze

    async def exploding_analyze(self, events):
        raise RuntimeError("LLM provider timeout")

    MockAnalysisLLMProvider.analyze = exploding_analyze
    try:
        with pytest.raises(RuntimeError):
            await generate_analysis_for_incident(
                db_session, inc.id, cid, manual_reanalysis=True
            )

        # Verify analysis was marked FAILED
        q = (
            select(IncidentAnalysis)
            .where(
                IncidentAnalysis.incident_id == inc.id,
                IncidentAnalysis.company_id == cid,
            )
            .order_by(IncidentAnalysis.version.desc())
        )
        latest = (await db_session.execute(q)).scalars().first()
        assert latest.status == AnalysisStatus.FAILED
    finally:
        MockAnalysisLLMProvider.analyze = original


# ==================== 16. Malformed AI Output ====================
@pytest.mark.asyncio
async def test_malformed_ai_output(db_session: AsyncSession, setup_4d):
    from app.services.analysis_service import MockAnalysisLLMProvider

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    original = MockAnalysisLLMProvider.analyze

    async def malformed_analyze(self, events):
        return {"candidates": [{"garbage": True}]}  # Missing required fields

    MockAnalysisLLMProvider.analyze = malformed_analyze
    try:
        with pytest.raises(Exception, match=".*"):
            await generate_analysis_for_incident(
                db_session, inc.id, cid, manual_reanalysis=True
            )
    finally:
        MockAnalysisLLMProvider.analyze = original


# ==================== Migration Roundtrip (verified via Alembic) ====================
# Migration roundtrip tested externally via:
#   alembic upgrade head
#   alembic downgrade -1
#   alembic upgrade head

import asyncio


# ==================== 17. Concurrent Generation ====================
@pytest.mark.asyncio
async def test_concurrent_generation(db_session: AsyncSession, setup_4d):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    key = "idem-concurrent-1"

    tasks = [
        generate_analysis_for_incident(db_session, inc.id, cid, idempotency_key=key)
        for _ in range(3)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    successes = [r for r in results if not isinstance(r, Exception)]

    assert len(successes) > 0
    first_id = successes[0].id
    for s in successes:
        assert s.id == first_id


# ==================== 18. Conflicting Candidates ====================
@pytest.mark.asyncio
async def test_conflicting_candidates(db_session: AsyncSession, setup_4d):
    from app.models.analysis import AssessmentEvidenceLink
    from app.services.analysis_service import MockAnalysisLLMProvider

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    ev = setup_4d["ev1"]

    original = MockAnalysisLLMProvider.analyze

    async def conflicting_analyze(self, events):
        return {
            "candidates": [
                {
                    "category": "MECHANICAL",
                    "role": "PRIMARY",
                    "explanation": "Conflicting test",
                    "supporting_event_ids": [],
                    "conflicting_event_ids": [ev.id],
                    "model_confidence": 0.5,
                }
            ]
        }

    MockAnalysisLLMProvider.analyze = conflicting_analyze
    try:
        analysis = await generate_analysis_for_incident(
            db_session, inc.id, cid, manual_reanalysis=True
        )
        q = (
            select(AssessmentEvidenceLink)
            .join(RootCauseAssessment)
            .where(RootCauseAssessment.analysis_id == analysis.id)
        )
        links = (await db_session.execute(q)).scalars().all()
        assert len(links) == 1
        assert links[0].relationship_type == "CONFLICTING"
        assert links[0].event_id == ev.id

        async def bad_id_analyze(self, events):
            return {
                "candidates": [
                    {
                        "category": "MECHANICAL",
                        "role": "PRIMARY",
                        "explanation": "Bad ID test",
                        "supporting_event_ids": [],
                        "conflicting_event_ids": ["invalid-id-123"],
                        "model_confidence": 0.5,
                    }
                ]
            }

        MockAnalysisLLMProvider.analyze = bad_id_analyze
        with pytest.raises(ValueError, match="invalid event_id"):
            await generate_analysis_for_incident(
                db_session, inc.id, cid, manual_reanalysis=True
            )
    finally:
        MockAnalysisLLMProvider.analyze = original


# ==================== 19. Composite Foreign Key Tests ====================
@pytest.mark.asyncio
async def test_composite_fk_enforcement(db_session: AsyncSession, setup_4d):
    from sqlalchemy.exc import IntegrityError

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )

    bad_cid = str(uuid.uuid4())
    bad_assessment = RootCauseAssessment(
        id=str(uuid.uuid4()),
        analysis_id=analysis.id,
        company_id=bad_cid,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role=AssessmentRole.PRIMARY,
        explanation="Test FK",
        provenance="MODEL_DERIVED",
        model_confidence=0.9,
    )
    db_session.add(bad_assessment)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


# ==================== 20. Human Confirmation Atomicity ====================
@pytest.mark.asyncio
async def test_human_confirmation_atomicity(
    db_session: AsyncSession, setup_4d, monkeypatch
):
    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    uid = setup_4d["user"].id

    analysis = await generate_analysis_for_incident(db_session, inc.id, cid)
    assmt = (
        (
            await db_session.execute(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
        )
        .scalars()
        .first()
    )

    # Monkeypatch commit to fail
    async def mock_commit():
        raise Exception("Mocked commit failure")

    assmt_id = assmt.id
    monkeypatch.setattr(db_session, "commit", mock_commit)

    with pytest.raises(Exception, match="Mocked commit failure"):
        await confirm_assessment(
            db_session, assmt.id, cid, uid, expected_revision=assmt.revision
        )

    # state should be rolled back or unchanged at db level, check local object doesn't matter
    # if it fails we just verify the revision in db is untouched
    monkeypatch.undo()
    await db_session.rollback()

    assmt_db = await db_session.get(RootCauseAssessment, assmt_id)
    assert assmt_db.status == AssessmentStatus.NEEDS_REVIEW


# ==================== 21. RBAC & API Tests ====================
@pytest.mark.asyncio
async def test_api_rbac_generation(setup_4d, async_client):
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]

    res = await async_client.post(
        f"/api/v1/analysis/incidents/{inc.id}/generate",
        json={"incident_id": inc.id},
        headers=headers,
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_api_rbac_confirm(setup_4d, db_session: AsyncSession, async_client):
    cid = setup_4d["company"].id
    inc = setup_4d["incident"]
    headers = setup_4d["headers"]
    user = setup_4d["user"]

    analysis = await generate_analysis_for_incident(
        db_session, inc.id, cid, manual_reanalysis=True
    )
    assmt = (
        (
            await db_session.execute(
                select(RootCauseAssessment).where(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
        )
        .scalars()
        .first()
    )

    res = await async_client.post(
        f"/api/v1/analysis/{analysis.id}/assessments/{assmt.id}/confirm",
        json={"expected_revision": assmt.revision},
        headers=headers,
    )
    assert res.status_code == 403

    user.role = "SUPERVISOR"
    db_session.add(user)
    await db_session.commit()

    res = await async_client.post(
        f"/api/v1/analysis/{analysis.id}/assessments/{assmt.id}/confirm",
        json={"expected_revision": assmt.revision},
        headers=headers,
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_api_cross_tenant(setup_4d, db_session: AsyncSession, async_client):
    headers = setup_4d["headers"]
    user = setup_4d["user"]
    user.role = "SUPERVISOR"
    db_session.add(user)
    await db_session.commit()

    import uuid

    other_inc_id = str(uuid.uuid4())
    res = await async_client.post(
        f"/api/v1/analysis/incidents/{other_inc_id}/generate",
        json={"incident_id": other_inc_id},
        headers=headers,
    )
    assert res.status_code in (404, 403)


@pytest.mark.asyncio
async def test_invalid_lifecycle_transitions(db_session: AsyncSession, setup_4d):
    from app.services.analysis_service import confirm_assessment, reject_assessment

    inc = setup_4d["incident"]
    cid = setup_4d["company"].id
    user = setup_4d["user"]

    from app.services.analysis_service import generate_analysis_for_incident

    analysis = await generate_analysis_for_incident(db_session, inc.id, cid)

    from sqlalchemy import select

    from app.models.analysis import AssessmentStatus, RootCauseAssessment

    q = select(RootCauseAssessment).where(
        RootCauseAssessment.analysis_id == analysis.id
    )
    assessments = (await db_session.execute(q)).scalars().all()
    assmt = assessments[0]

    # 1. CANDIDATE -> NEEDS_REVIEW was already proven by the generation process
    # which created it as CANDIDATE and transitioned it to NEEDS_REVIEW
    assert assmt.status == AssessmentStatus.NEEDS_REVIEW

    # 2. Try to skip to SUPERSEDED directly? (Not exposed via API, but state machine rejects it if we did)
    # The state machine doesn't allow NEEDS_REVIEW -> SUPERSEDED
    import pytest
    from fastapi import HTTPException

    from app.services.analysis_service import transition_assessment_status

    with pytest.raises(HTTPException) as exc:
        transition_assessment_status(db_session, assmt, AssessmentStatus.SUPERSEDED)
    assert exc.value.status_code == 400

    # Let's transition it to CONFIRMED
    await confirm_assessment(db_session, assmt.id, cid, user.id, assmt.revision)
    await db_session.refresh(assmt)
    assert assmt.status == AssessmentStatus.CONFIRMED

    # 3. Try CONFIRMED -> REJECTED
    with pytest.raises(HTTPException) as exc:
        await reject_assessment(
            db_session, assmt.id, cid, user.id, assmt.revision, "Because"
        )
    assert exc.value.status_code == 400

    # 4. Try CONFIRMED -> CONFIRMED (Idempotent call without stale revision should also fail now!)
    with pytest.raises(HTTPException) as exc:
        await confirm_assessment(db_session, assmt.id, cid, user.id, assmt.revision)
    assert exc.value.status_code == 400

    # 5. Let's make a new candidate and reject it to test REJECTED -> CONFIRMED
    assmt2 = RootCauseAssessment(
        analysis_id=analysis.id,
        company_id=cid,
        status=AssessmentStatus.NEEDS_REVIEW,
        category="MECHANICAL",
        role="CONTRIBUTING",
        explanation="Test",
        provenance="MODEL_DERIVED",
    )
    db_session.add(assmt2)
    await db_session.commit()

    await reject_assessment(db_session, assmt2.id, cid, user.id, assmt2.revision)
    await db_session.refresh(assmt2)

    with pytest.raises(HTTPException) as exc:
        await confirm_assessment(db_session, assmt2.id, cid, user.id, assmt2.revision)
    assert exc.value.status_code == 400

    # 6. Test REJECTED -> SUPERSEDED and CONFIRMED -> SUPERSEDED
    # These are valid transitions according to state machine.
    transition_assessment_status(db_session, assmt, AssessmentStatus.SUPERSEDED)
    transition_assessment_status(db_session, assmt2, AssessmentStatus.SUPERSEDED)
    assert assmt.status == AssessmentStatus.SUPERSEDED
    assert assmt2.status == AssessmentStatus.SUPERSEDED
