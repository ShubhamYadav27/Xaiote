import hashlib
import logging

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.analysis import (
    AnalysisStatus,
    AssessmentDecisionHistory,
    AssessmentEvidenceLink,
    AssessmentStatus,
    IncidentAnalysis,
    RootCauseAssessment,
)
from app.models.incident import Incident, IncidentEvent
from app.models.manufacturing_event import ManufacturingEvent

logger = logging.getLogger(__name__)


def generate_evidence_snapshot_hash(event_ids: list[str]) -> str:
    """Generate a deterministic hash from a sorted list of event IDs."""
    sorted_ids = sorted(event_ids)
    joined_ids = ",".join(sorted_ids)
    return hashlib.sha256(joined_ids.encode("utf-8")).hexdigest()


def generate_generation_fingerprint(
    snapshot_hash: str, prompt_version: str, schema_version: str, provider_config: str
) -> str:
    """Generate a fingerprint combining the evidence snapshot and config."""
    content = f"{snapshot_hash}|{prompt_version}|{schema_version}|{provider_config}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class MockAnalysisLLMProvider:
    """
    A mock provider strictly behind an abstraction.
    Produces valid structured output with real event IDs.
    """

    def __init__(
        self,
        prompt_version: str = "1.0",
        schema_version: str = "1.0",
        model_name: str = "mock-model",
    ):
        self.prompt_version = prompt_version
        self.schema_version = schema_version
        self.model_name = model_name

    async def analyze(self, events: list[ManufacturingEvent]) -> dict:
        if not events:
            return {"candidates": []}

        # Mock logic: if any event has 'stopped', suggest Mechanical.
        candidates = []
        event_ids = [e.id for e in events]

        # We simulate finding a candidate if there are events
        candidates.append(
            {
                "category": "MECHANICAL",
                "role": "PRIMARY",
                "explanation": "Mocked mechanical failure based on provided evidence.",
                "supporting_event_ids": event_ids[:1],  # Just use the first one
                "conflicting_event_ids": [],
                "model_confidence": 0.95,
            }
        )

        return {"candidates": candidates}


def transition_assessment_status(
    session,
    assessment,
    new_status,
    actor_id: str | None = None,
    reason: str | None = None,
    analysis_version: int = 1,
):
    """State machine enforcing canonical lifecycle."""
    valid_transitions = {
        AssessmentStatus.CANDIDATE: [AssessmentStatus.NEEDS_REVIEW],
        AssessmentStatus.NEEDS_REVIEW: [
            AssessmentStatus.CONFIRMED,
            AssessmentStatus.REJECTED,
        ],
        AssessmentStatus.CONFIRMED: [AssessmentStatus.SUPERSEDED],
        AssessmentStatus.REJECTED: [AssessmentStatus.SUPERSEDED],
        AssessmentStatus.SUPERSEDED: [],
    }

    if new_status not in valid_transitions.get(assessment.status, []):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail=f"Invalid transition from {assessment.status.value} to {new_status.value}",
        )

    prev_status = assessment.status
    assessment.status = new_status
    assessment.revision += 1
    session.add(assessment)

    if actor_id:
        hist = AssessmentDecisionHistory(
            assessment_id=assessment.id,
            company_id=assessment.company_id,
            actor_id=actor_id,
            action=new_status.value,
            previous_state=prev_status.value,
            new_state=new_status.value,
            reason=reason,
            analysis_version=analysis_version,
        )
        session.add(hist)


async def generate_analysis_for_incident(
    session: AsyncSession,
    incident_id: str,
    company_id: str,
    idempotency_key: str | None = None,
    manual_reanalysis: bool = False,
) -> IncidentAnalysis:
    """
    Generates a new IncidentAnalysis version.
    """
    # 1. Fetch Incident and Events
    incident = await session.get(Incident, incident_id)
    if not incident or incident.company_id != company_id:
        raise HTTPException(status_code=404, detail="Incident not found")

    q_events = (
        select(ManufacturingEvent)
        .join(IncidentEvent, IncidentEvent.event_id == ManufacturingEvent.id)
        .where(
            IncidentEvent.incident_id == incident_id,
            ManufacturingEvent.company_id == company_id,
        )
    )
    result = await session.execute(q_events)
    events = result.scalars().all()
    event_ids = [e.id for e in events]

    snapshot_hash = generate_evidence_snapshot_hash(event_ids)

    provider = MockAnalysisLLMProvider()
    fingerprint = generate_generation_fingerprint(
        snapshot_hash,
        provider.prompt_version,
        provider.schema_version,
        provider.model_name,
    )

    # 2. Check Request Idempotency
    if idempotency_key:
        q_idem = select(IncidentAnalysis).where(
            IncidentAnalysis.incident_id == incident_id,
            IncidentAnalysis.company_id == company_id,
            IncidentAnalysis.request_idempotency_key == idempotency_key,
        )
        existing = (await session.execute(q_idem)).scalars().first()
        if existing:
            return existing

    # 3. Determine next version
    q_latest = (
        select(IncidentAnalysis)
        .where(
            IncidentAnalysis.incident_id == incident_id,
            IncidentAnalysis.company_id == company_id,
        )
        .order_by(IncidentAnalysis.version.desc())
    )
    latest_analysis = (await session.execute(q_latest)).scalars().first()

    next_version = 1
    if latest_analysis:
        if (
            not manual_reanalysis
            and latest_analysis.generation_fingerprint == fingerprint
        ):
            # Not a manual trigger and fingerprint is identical -> Do not generate
            return latest_analysis
        next_version = latest_analysis.version + 1

    # 4. Create PENDING analysis
    analysis = IncidentAnalysis(
        incident_id=incident_id,
        company_id=company_id,
        version=next_version,
        status=AnalysisStatus.PENDING,
        evidence_snapshot_hash=snapshot_hash,
        generation_fingerprint=fingerprint,
        request_idempotency_key=idempotency_key,
    )
    session.add(analysis)

    if latest_analysis:
        latest_analysis.status = AnalysisStatus.SUPERSEDED

    await session.commit()
    await session.refresh(analysis)

    # 5. Execute LLM (synchronous for simplicity in this implementation)
    analysis.status = AnalysisStatus.PROCESSING
    await session.commit()

    try:
        output = await provider.analyze(events)

        candidates = output.get("candidates", [])

        for cand in candidates:
            # Validate Event IDs strictly
            for ev_id in cand.get("supporting_event_ids", []) + cand.get(
                "conflicting_event_ids", []
            ):
                if ev_id not in event_ids:
                    raise ValueError(f"AI returned invalid event_id: {ev_id}")

            assessment = RootCauseAssessment(
                analysis_id=analysis.id,
                company_id=company_id,
                status=AssessmentStatus.CANDIDATE,
                category=cand["category"],
                role=cand["role"],
                explanation=cand["explanation"],
                provenance="MODEL_DERIVED",
                model_confidence=cand.get("model_confidence"),
            )
            session.add(assessment)
            await session.flush()

            for ev_id in cand.get("supporting_event_ids", []):
                link = AssessmentEvidenceLink(
                    assessment_id=assessment.id,
                    event_id=ev_id,
                    company_id=company_id,
                    relationship_type="SUPPORTING",
                )
                session.add(link)

            for ev_id in cand.get("conflicting_event_ids", []):
                link = AssessmentEvidenceLink(
                    assessment_id=assessment.id,
                    event_id=ev_id,
                    company_id=company_id,
                    relationship_type="CONFLICTING",
                )
                session.add(link)

            # Enforce CANDIDATE -> NEEDS_REVIEW lifecycle transition
            await session.flush()

            transition_assessment_status(
                session,
                assessment,
                AssessmentStatus.NEEDS_REVIEW,
                actor_id=None,
                reason="AI Generation",
            )

        analysis.status = AnalysisStatus.COMPLETED
        await session.commit()
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        await session.rollback()
        analysis.status = AnalysisStatus.FAILED
        session.add(analysis)
        await session.commit()
        raise

    return analysis


async def confirm_assessment(
    session: AsyncSession,
    assessment_id: str,
    company_id: str,
    actor_id: str,
    expected_revision: int,
) -> RootCauseAssessment:
    """Atomically confirm an assessment and supersede existing PRIMARY if necessary."""
    from fastapi import HTTPException

    assessment = await session.get(RootCauseAssessment, assessment_id)
    if not assessment or assessment.company_id != company_id:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.revision != expected_revision:
        raise HTTPException(
            status_code=409, detail="Stale revision: concurrent modification detected"
        )

    analysis = await session.get(IncidentAnalysis, assessment.analysis_id)

    # If this is PRIMARY, supersede existing primary
    if assessment.role == "PRIMARY":
        from sqlalchemy import select

        q = select(RootCauseAssessment).where(
            RootCauseAssessment.analysis_id == assessment.analysis_id,
            RootCauseAssessment.role == "PRIMARY",
            RootCauseAssessment.status == AssessmentStatus.CONFIRMED,
            RootCauseAssessment.id != assessment.id,
        )
        existing = (await session.execute(q)).scalars().first()
        if existing:
            transition_assessment_status(
                session,
                existing,
                AssessmentStatus.SUPERSEDED,
                actor_id=actor_id,
                reason=f"Superseded by {assessment.id}",
                analysis_version=analysis.version,
            )

    transition_assessment_status(
        session,
        assessment,
        AssessmentStatus.CONFIRMED,
        actor_id=actor_id,
        reason=None,
        analysis_version=analysis.version,
    )

    await session.commit()
    await session.refresh(assessment)
    return assessment


async def reject_assessment(
    session: AsyncSession,
    assessment_id: str,
    company_id: str,
    actor_id: str,
    expected_revision: int,
    reason: str | None = None,
) -> RootCauseAssessment:
    """Atomically reject an assessment."""
    from fastapi import HTTPException

    assessment = await session.get(RootCauseAssessment, assessment_id)
    if not assessment or assessment.company_id != company_id:
        raise HTTPException(status_code=404, detail="Assessment not found")

    if assessment.revision != expected_revision:
        raise HTTPException(
            status_code=409, detail="Stale revision: concurrent modification detected"
        )

    analysis = await session.get(IncidentAnalysis, assessment.analysis_id)

    transition_assessment_status(
        session,
        assessment,
        AssessmentStatus.REJECTED,
        actor_id=actor_id,
        reason=reason,
        analysis_version=analysis.version,
    )

    await session.commit()
    await session.refresh(assessment)
    return assessment


async def get_latest_analysis(session, incident_id: str, company_id: str):
    from sqlalchemy import select

    from app.models.analysis import IncidentAnalysis
    from app.models.incident import IncidentEvent

    q = (
        select(IncidentAnalysis)
        .where(
            IncidentAnalysis.incident_id == incident_id,
            IncidentAnalysis.company_id == company_id,
        )
        .order_by(IncidentAnalysis.version.desc())
    )

    analysis = (await session.execute(q)).scalars().first()
    if not analysis:
        return None, False

    q_events = (
        select(ManufacturingEvent)
        .join(IncidentEvent, IncidentEvent.event_id == ManufacturingEvent.id)
        .where(
            IncidentEvent.incident_id == incident_id,
            ManufacturingEvent.company_id == company_id,
        )
    )
    events = (await session.execute(q_events)).scalars().all()
    event_ids = [e.id for e in events]

    current_hash = generate_evidence_snapshot_hash(event_ids)
    is_stale = current_hash != analysis.evidence_snapshot_hash

    return analysis, is_stale
