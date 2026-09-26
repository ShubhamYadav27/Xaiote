"""
Phase 4C — Incident Correlation & Recovery Detection Service

Handles:
- Incident creation from failure events
- Deterministic event correlation
- Event link/unlink with audit
- Recovery confirmation with atomic risk re-evaluation
- Legacy (incident_id=NULL) impact fallback
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.impact import ImpactStatus, ProductionOrderImpact
from app.models.incident import (
    Incident,
    IncidentDecisionAction,
    IncidentDecisionHistory,
    IncidentEvent,
    IncidentEventLinkState,
    IncidentStatus,
)
from app.models.manufacturing_event import ManufacturingEvent
from app.models.risk import RiskTriggerType
from app.services.risk_service import (
    fetch_current_risk,
    record_risk_transition_if_changed,
)

logger = logging.getLogger(__name__)


class IncidentSecurityException(Exception):
    pass


class IncidentStateError(Exception):
    pass


# ---------- Incident Creation ----------


async def create_incident_from_failure(
    db: AsyncSession,
    event: ManufacturingEvent,
    title: str,
    actor_id: str | None = None,
) -> Incident:
    """Create a new ACTIVE Incident from a grounded FAILURE event."""
    incident = Incident(
        id=str(uuid.uuid4()),
        company_id=event.company_id,
        plant_id=event.plant_id or "",
        machine_id=getattr(event, "_resolved_machine_id", None),
        title=title,
        status=IncidentStatus.ACTIVE,
    )
    db.add(incident)
    await db.flush()

    # Link the originating event
    link = IncidentEvent(
        id=str(uuid.uuid4()),
        incident_id=incident.id,
        event_id=event.id,
        link_state=IncidentEventLinkState.LINKED,
    )
    db.add(link)

    # Audit history
    history = IncidentDecisionHistory(
        id=str(uuid.uuid4()),
        incident_id=incident.id,
        actor_id=actor_id,
        event_id=event.id,
        action=IncidentDecisionAction.CREATED,
        previous_state=None,
        new_state=IncidentStatus.ACTIVE.value,
        reason=f"Incident created from event: {event.id}",
    )
    db.add(history)
    await db.flush()

    return incident


# ---------- Deterministic Correlation ----------


async def find_active_incidents_for_context(
    db: AsyncSession,
    company_id: str,
    plant_id: str | None,
    machine_id: str | None,
) -> list[Incident]:
    """Find ACTIVE incidents matching the given context deterministically."""
    conditions = [
        Incident.company_id == company_id,
        Incident.status == IncidentStatus.ACTIVE,
    ]

    if machine_id:
        # Strong match: same machine
        conditions.append(Incident.machine_id == machine_id)
    elif plant_id:
        # Weaker match: same plant
        conditions.append(Incident.plant_id == plant_id)
    else:
        return []

    stmt = (
        select(Incident).where(and_(*conditions)).order_by(Incident.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def is_strong_correlation(
    incident: Incident,
    event: ManufacturingEvent,
    machine_id: str | None,
) -> bool:
    """Determine if the correlation between an event and an incident is strong (auto-linkable)."""
    # Strong: same machine_id on both incident and event resolution
    if incident.machine_id and machine_id and incident.machine_id == machine_id:
        return True
    return False


# ---------- Event Link ----------


async def link_event_to_incident(
    db: AsyncSession,
    incident_id: str,
    event_id: str,
    company_id: str,
    actor_id: str | None = None,
    reason: str | None = None,
) -> IncidentEvent:
    """Link a ManufacturingEvent to an Incident. Idempotent."""
    # Verify ownership
    incident = await _get_incident_owned(db, incident_id, company_id)
    event = await _get_event_owned(db, event_id, company_id)

    # Check for existing link
    stmt = select(IncidentEvent).where(
        and_(
            IncidentEvent.incident_id == incident_id,
            IncidentEvent.event_id == event_id,
        )
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        if existing.link_state == IncidentEventLinkState.LINKED:
            # Idempotent: already linked
            return existing
        # Re-linking a previously unlinked event
        existing.link_state = IncidentEventLinkState.LINKED
        existing.updated_at = datetime.now(timezone.utc)
    else:
        existing = IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=incident_id,
            event_id=event_id,
            link_state=IncidentEventLinkState.LINKED,
        )
        db.add(existing)

    # Audit
    history = IncidentDecisionHistory(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_id=actor_id,
        event_id=event_id,
        action=IncidentDecisionAction.EVENT_LINKED,
        previous_state=IncidentEventLinkState.UNLINKED.value if existing else None,
        new_state=IncidentEventLinkState.LINKED.value,
        reason=reason,
    )
    db.add(history)
    await db.flush()

    return existing


# ---------- Event Unlink ----------


async def unlink_event_from_incident(
    db: AsyncSession,
    incident_id: str,
    event_id: str,
    company_id: str,
    actor_id: str,
    reason: str,
) -> list[dict]:
    """
    Unlink a ManufacturingEvent from an Incident. Triggers risk re-evaluation
    for all affected Work Orders. Returns list of risk changes.
    """
    incident = await _get_incident_owned(db, incident_id, company_id)
    event = await _get_event_owned(db, event_id, company_id)

    stmt = select(IncidentEvent).where(
        and_(
            IncidentEvent.incident_id == incident_id,
            IncidentEvent.event_id == event_id,
        )
    )
    result = await db.execute(stmt)
    link = result.scalar_one_or_none()

    if not link or link.link_state == IncidentEventLinkState.UNLINKED:
        # Idempotent: already unlinked or never linked
        return []

    # Find affected WOs from this event and store previous risk BEFORE unlinking
    now = datetime.now(timezone.utc)
    stmt_impacts = (
        select(ProductionOrderImpact.work_order_id)
        .where(
            and_(
                ProductionOrderImpact.event_id == event.id,
                ProductionOrderImpact.status.in_(
                    [ImpactStatus.POTENTIAL, ImpactStatus.CONFIRMED]
                ),
            )
        )
        .distinct()
    )
    affected_wo_ids = [row[0] for row in (await db.execute(stmt_impacts)).all()]

    prev_risks = {}
    for wo_id in affected_wo_ids:
        prev_risks[wo_id] = await fetch_current_risk(db, wo_id, now)

    link.link_state = IncidentEventLinkState.UNLINKED
    link.updated_at = now

    # Audit
    history = IncidentDecisionHistory(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_id=actor_id,
        event_id=event_id,
        action=IncidentDecisionAction.EVENT_UNLINKED,
        previous_state=IncidentEventLinkState.LINKED.value,
        new_state=IncidentEventLinkState.UNLINKED.value,
        reason=reason,
    )
    db.add(history)
    await db.flush()

    # Re-evaluate risk for affected Work Orders
    risk_changes = []
    for wo_id in affected_wo_ids:
        new_risk = await record_risk_transition_if_changed(
            db,
            wo_id,
            incident.company_id,
            prev_risks[wo_id],
            RiskTriggerType.EVENT_UNLINKED,
            now,
        )
        if prev_risks[wo_id] != new_risk:
            risk_changes.append(
                {
                    "work_order_id": wo_id,
                    "previous_state": prev_risks[wo_id].value,
                    "new_state": new_risk.value,
                }
            )

    return risk_changes


# ---------- Recovery Confirmation ----------


async def resolve_incident(
    db: AsyncSession,
    incident_id: str,
    company_id: str,
    actor_id: str,
    reason: str | None = None,
) -> tuple[Incident, list[dict]]:
    """
    Atomically resolve an Incident and re-evaluate risk for all affected WOs.
    Returns the resolved incident and list of risk state changes.
    Raises IncidentStateError if incident is not ACTIVE.
    """
    # Lock the incident row for concurrency safety
    stmt = (
        select(Incident)
        .where(and_(Incident.id == incident_id, Incident.company_id == company_id))
        .with_for_update()
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()

    if not incident:
        raise IncidentSecurityException("Incident not found")

    if incident.status == IncidentStatus.RESOLVED:
        # Idempotent: already resolved, no-op
        return incident, []

    if incident.status != IncidentStatus.ACTIVE:
        raise IncidentStateError(f"Cannot resolve incident in state: {incident.status}")

    # Find affected WOs and store previous risk BEFORE modifying incident
    now = datetime.now(timezone.utc)
    stmt_impacts = (
        select(ProductionOrderImpact.work_order_id)
        .where(
            and_(
                ProductionOrderImpact.incident_id == incident.id,
                ProductionOrderImpact.status.in_(
                    [ImpactStatus.POTENTIAL, ImpactStatus.CONFIRMED]
                ),
            )
        )
        .distinct()
    )
    affected_wo_ids = [row[0] for row in (await db.execute(stmt_impacts)).all()]

    prev_risks = {}
    for wo_id in affected_wo_ids:
        prev_risks[wo_id] = await fetch_current_risk(db, wo_id, now)

    incident.status = IncidentStatus.RESOLVED
    incident.resolved_at = now
    incident.updated_at = now

    # Audit
    history = IncidentDecisionHistory(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        actor_id=actor_id,
        action=IncidentDecisionAction.RECOVERY_CONFIRMED,
        previous_state=IncidentStatus.ACTIVE.value,
        new_state=IncidentStatus.RESOLVED.value,
        reason=reason,
    )
    db.add(history)
    await db.flush()

    # Re-evaluate risk for all affected Work Orders
    risk_changes = []
    for wo_id in affected_wo_ids:
        new_risk = await record_risk_transition_if_changed(
            db,
            wo_id,
            incident.company_id,
            prev_risks[wo_id],
            RiskTriggerType.INCIDENT_RESOLVED,
            now,
        )
        if prev_risks[wo_id] != new_risk:
            risk_changes.append(
                {
                    "work_order_id": wo_id,
                    "previous_state": prev_risks[wo_id].value,
                    "new_state": new_risk.value,
                }
            )

    return incident, risk_changes


# ---------- Query Helpers ----------


async def get_incidents(
    db: AsyncSession,
    company_id: str,
    status: IncidentStatus | None = None,
    plant_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Incident], int]:
    """List incidents for a company with optional filters."""
    conditions = [Incident.company_id == company_id]
    if status:
        conditions.append(Incident.status == status)
    if plant_id:
        conditions.append(Incident.plant_id == plant_id)

    from sqlalchemy import func

    count_stmt = select(func.count(Incident.id)).where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    stmt = (
        select(Incident)
        .where(and_(*conditions))
        .order_by(Incident.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    incidents = list(result.scalars().all())

    return incidents, total


async def get_incident_detail(
    db: AsyncSession,
    incident_id: str,
    company_id: str,
) -> dict | None:
    """Get incident with linked events and affected work orders."""
    incident = await _get_incident_owned(db, incident_id, company_id)

    # Linked events
    stmt = (
        select(IncidentEvent)
        .where(
            and_(
                IncidentEvent.incident_id == incident_id,
                IncidentEvent.link_state == IncidentEventLinkState.LINKED,
            )
        )
        .order_by(IncidentEvent.created_at.asc())
    )
    result = await db.execute(stmt)
    linked_events = list(result.scalars().all())

    # Fetch event details
    event_ids = [le.event_id for le in linked_events]
    events = []
    if event_ids:
        stmt_e = select(ManufacturingEvent).where(ManufacturingEvent.id.in_(event_ids))
        res_e = await db.execute(stmt_e)
        events = list(res_e.scalars().all())

    # Affected impacts
    stmt_impacts = select(ProductionOrderImpact).where(
        ProductionOrderImpact.incident_id == incident_id
    )
    res_impacts = await db.execute(stmt_impacts)
    impacts = list(res_impacts.scalars().all())

    # Decision history
    stmt_hist = (
        select(IncidentDecisionHistory)
        .where(IncidentDecisionHistory.incident_id == incident_id)
        .order_by(IncidentDecisionHistory.created_at.asc())
    )
    res_hist = await db.execute(stmt_hist)
    history = list(res_hist.scalars().all())

    return {
        "incident": incident,
        "linked_events": events,
        "impacts": impacts,
        "decision_history": history,
    }


# ---------- Internal Helpers ----------


async def _get_incident_owned(
    db: AsyncSession, incident_id: str, company_id: str
) -> Incident:
    """Fetch an incident, verifying tenant ownership."""
    stmt = select(Incident).where(
        and_(Incident.id == incident_id, Incident.company_id == company_id)
    )
    result = await db.execute(stmt)
    incident = result.scalar_one_or_none()
    if not incident:
        raise IncidentSecurityException("Incident not found")
    return incident


async def _get_event_owned(
    db: AsyncSession, event_id: str, company_id: str
) -> ManufacturingEvent:
    """Fetch a manufacturing event, verifying tenant ownership."""
    stmt = select(ManufacturingEvent).where(
        and_(
            ManufacturingEvent.id == event_id,
            ManufacturingEvent.company_id == company_id,
        )
    )
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        raise IncidentSecurityException("Event not found")
    return event
