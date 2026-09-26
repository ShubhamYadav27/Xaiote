# mypy: disable-error-code="var-annotated"
from datetime import datetime

from sqlalchemy import (
    DateTime,
    String,
    and_,
    case,
    desc,
    func,
    literal_column,
    or_,
    select,
    union_all,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import (
    AssessmentDecisionHistory,
    IncidentAnalysis,
    RootCauseAssessment,
)
from app.models.impact import ImpactDecisionHistory, ProductionOrderImpact
from app.models.incident import Incident, IncidentDecisionHistory, IncidentEvent
from app.models.manufacturing_event import ManufacturingEvent
from app.models.risk import WorkOrderRiskHistory
from app.schemas.operational import TimelineEntry


def _build_timeline_query(
    company_id: str, entity_type: str, entity_id: str, chronology: str = "operational"
):
    queries = []

    if entity_type == "incident":
        # Incident Creation / Status Changes
        q1 = (
            select(
                IncidentDecisionHistory.id.label("source_id"),
                literal_column("'IncidentDecisionHistory'").label("source_type"),
                func.cast(None, DateTime).label("occurrence_time"),
                IncidentDecisionHistory.created_at.label("decision_time"),
                IncidentDecisionHistory.created_at.label("recorded_time"),
                func.cast(IncidentDecisionHistory.action, String).label("action"),
                func.cast(IncidentDecisionHistory.new_state, String).label("state"),
            )
            .where(IncidentDecisionHistory.incident_id == entity_id)
            .join(Incident, IncidentDecisionHistory.incident_id == Incident.id)
            .where(Incident.company_id == company_id)
        )
        queries.append(q1)

        # Manufacturing Events linked to Incident
        q2 = (
            select(
                ManufacturingEvent.id.label("source_id"),
                literal_column("'ManufacturingEvent'").label("source_type"),
                ManufacturingEvent.canonical_occurrence_timestamp.label(
                    "occurrence_time"
                ),
                func.cast(None, DateTime).label("decision_time"),
                ManufacturingEvent.created_at.label("recorded_time"),
                ManufacturingEvent.canonical_event_type.label("action"),
                ManufacturingEvent.description.label("state"),
            )
            .join(IncidentEvent, IncidentEvent.event_id == ManufacturingEvent.id)
            .join(Incident, Incident.id == IncidentEvent.incident_id)
            .where(
                Incident.id == entity_id,
                Incident.company_id == company_id,
                IncidentEvent.link_state == "LINKED",
            )
        )
        queries.append(q2)

        # Root Cause Assessment decisions
        q3 = (
            select(
                AssessmentDecisionHistory.id.label("source_id"),
                literal_column("'AssessmentDecisionHistory'").label("source_type"),
                func.cast(None, DateTime).label("occurrence_time"),
                AssessmentDecisionHistory.timestamp.label("decision_time"),
                AssessmentDecisionHistory.timestamp.label("recorded_time"),
                func.cast(AssessmentDecisionHistory.action, String).label("action"),
                func.cast(AssessmentDecisionHistory.new_state, String).label("state"),
            )
            .join(
                RootCauseAssessment,
                RootCauseAssessment.id == AssessmentDecisionHistory.assessment_id,
            )
            .join(
                IncidentAnalysis, IncidentAnalysis.id == RootCauseAssessment.analysis_id
            )
            .join(Incident, Incident.id == IncidentAnalysis.incident_id)
            .where(Incident.id == entity_id, Incident.company_id == company_id)
        )
        queries.append(q3)

        # Impacts generated from this incident
        q4 = (
            select(
                ProductionOrderImpact.id.label("source_id"),
                literal_column("'ProductionOrderImpact'").label("source_type"),
                func.cast(None, DateTime).label("occurrence_time"),
                func.cast(None, DateTime).label("decision_time"),
                ProductionOrderImpact.created_at.label("recorded_time"),
                literal_column("'IMPACT_CREATED'").label("action"),
                func.cast(None, String).label("state"),
            )
            .join(Incident, Incident.id == ProductionOrderImpact.incident_id)
            .where(Incident.id == entity_id, Incident.company_id == company_id)
        )
        queries.append(q4)

    elif entity_type == "work_order":
        # Impacts on this WorkOrder
        q1_wo = select(
            ProductionOrderImpact.id.label("source_id"),
            literal_column("'ProductionOrderImpact'").label("source_type"),
            func.cast(None, DateTime).label("occurrence_time"),
            func.cast(None, DateTime).label("decision_time"),
            ProductionOrderImpact.created_at.label("recorded_time"),
            literal_column("'IMPACT_CREATED'").label("action"),
            func.cast(None, String).label("state"),
        ).where(
            ProductionOrderImpact.work_order_id == entity_id,
            ProductionOrderImpact.company_id == company_id,
        )
        queries.append(q1_wo)

        # Impact Decisions
        q2_wo = (
            select(
                ImpactDecisionHistory.id.label("source_id"),
                literal_column("'ImpactDecisionHistory'").label("source_type"),
                func.cast(None, DateTime).label("occurrence_time"),
                ImpactDecisionHistory.created_at.label("decision_time"),
                ImpactDecisionHistory.created_at.label("recorded_time"),
                literal_column("'DECISION'").label("action"),
                func.cast(None, String).label("state"),
            )
            .join(
                ProductionOrderImpact,
                ProductionOrderImpact.id == ImpactDecisionHistory.impact_id,
            )
            .where(
                ProductionOrderImpact.work_order_id == entity_id,
                ProductionOrderImpact.company_id == company_id,
            )
        )
        queries.append(q2_wo)

        # Risk History
        q3_wo = select(
            WorkOrderRiskHistory.id.label("source_id"),
            literal_column("'WorkOrderRiskHistory'").label("source_type"),
            func.cast(None, DateTime).label("occurrence_time"),
            WorkOrderRiskHistory.created_at.label("decision_time"),
            WorkOrderRiskHistory.created_at.label("recorded_time"),
            func.cast(WorkOrderRiskHistory.trigger_type, String).label("action"),
            func.cast(WorkOrderRiskHistory.new_state, String).label("state"),
        ).where(
            WorkOrderRiskHistory.work_order_id == entity_id,
            WorkOrderRiskHistory.company_id == company_id,
        )
        queries.append(q3_wo)

        # Manufacturing Events linked via Impact
        q4_wo = (
            select(
                ManufacturingEvent.id.label("source_id"),
                literal_column("'ManufacturingEvent'").label("source_type"),
                ManufacturingEvent.canonical_occurrence_timestamp.label(
                    "occurrence_time"
                ),
                func.cast(None, DateTime).label("decision_time"),
                ManufacturingEvent.created_at.label("recorded_time"),
                ManufacturingEvent.canonical_event_type.label("action"),
                ManufacturingEvent.description.label("state"),
            )
            .join(
                ProductionOrderImpact,
                ProductionOrderImpact.event_id == ManufacturingEvent.id,
            )
            .where(
                ProductionOrderImpact.work_order_id == entity_id,
                ProductionOrderImpact.company_id == company_id,
            )
        )
        queries.append(q4_wo)

    if not queries:
        return None

    union_q = union_all(*queries).subquery("raw_timeline")

    if chronology == "audit":
        presentation_time_col = func.coalesce(
            union_q.c.decision_time, union_q.c.recorded_time
        ).label("presentation_time")
        prov_expr = case(
            (union_q.c.decision_time.is_not(None), "EXPLICIT_DECISION"),
            else_="DECISION_FALLBACK_RECORDED",
        ).label("presentation_time_provenance")
    else:
        presentation_time_col = func.coalesce(
            union_q.c.occurrence_time, union_q.c.recorded_time
        ).label("presentation_time")
        prov_expr = case(
            (union_q.c.occurrence_time.is_not(None), "EXPLICIT_OCCURRENCE"),
            else_="OCCURRENCE_FALLBACK_RECORDED",
        ).label("presentation_time_provenance")

    final_q = select(
        union_q.c.source_id,
        union_q.c.source_type,
        union_q.c.occurrence_time,
        union_q.c.decision_time,
        union_q.c.recorded_time,
        union_q.c.action,
        union_q.c.state,
        presentation_time_col,
        prov_expr,
    )

    return final_q


async def get_timeline(
    db: AsyncSession,
    company_id: str,
    entity_type: str,
    entity_id: str,
    chronology: str = "operational",
    limit: int = 50,
    cursor_time: datetime | None = None,
    cursor_id: str | None = None,
) -> tuple[list[TimelineEntry], str | None]:

    final_q = _build_timeline_query(company_id, entity_type, entity_id, chronology)
    if final_q is None:
        return [], None

    subq = final_q.subquery("timeline_data")

    q = select(subq)

    if cursor_time and cursor_id:
        cursor_time = cursor_time.replace(tzinfo=None)
        q = q.where(
            or_(
                subq.c.presentation_time < cursor_time,
                and_(
                    subq.c.presentation_time == cursor_time,
                    subq.c.source_id < cursor_id,
                ),
            )
        )

    q = q.order_by(desc(subq.c.presentation_time), desc(subq.c.source_id)).limit(limit)

    result = await db.execute(q)
    rows = result.mappings().all()

    entries = []
    for row in rows:
        # Convert timezone-naive or naive-utc dates accurately?
        # Actually sqlalchemy returns datetime objects.
        entries.append(
            TimelineEntry(
                source_id=row["source_id"],
                source_type=row["source_type"],
                occurrence_time=row["occurrence_time"],
                decision_time=row["decision_time"],
                recorded_time=row["recorded_time"],
                presentation_time=row["presentation_time"],
                presentation_time_provenance=row["presentation_time_provenance"],
                data={"action": row["action"], "state": row["state"]},
            )
        )

    next_cursor = None
    if len(entries) == limit:
        last = entries[-1]
        next_cursor = f"{last.presentation_time.isoformat()}|{last.source_id}"

    return entries, next_cursor
