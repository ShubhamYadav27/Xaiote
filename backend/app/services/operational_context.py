from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import (
    AssessmentEvidenceLink,
    IncidentAnalysis,
    RootCauseAssessment,
)
from app.models.impact import ProductionOrderImpact
from app.models.incident import Incident, IncidentEvent
from app.models.manufacturing_event import ManufacturingEvent
from app.models.risk import WorkOrderRiskHistory
from app.models.work_order import WorkOrder
from app.schemas.operational import IncidentContextResponse, WorkOrderContextResponse


async def get_work_order_context(
    db: AsyncSession, company_id: str, work_order_id: str
) -> WorkOrderContextResponse:
    wo_result = await db.execute(
        select(WorkOrder).filter(
            WorkOrder.id == work_order_id, WorkOrder.company_id == company_id
        )
    )
    wo = wo_result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="WorkOrder not found")

    impacts_result = await db.execute(
        select(ProductionOrderImpact).filter(
            ProductionOrderImpact.work_order_id == work_order_id,
            ProductionOrderImpact.company_id == company_id,
        )
    )
    impacts = impacts_result.scalars().all()

    events_by_id = {}
    incidents_by_id = {}
    for imp in impacts:
        if imp.event_id and imp.event_id not in events_by_id:
            evt_result = await db.execute(
                select(ManufacturingEvent).filter(ManufacturingEvent.id == imp.event_id)
            )
            evt = evt_result.scalar_one_or_none()
            if evt:
                events_by_id[evt.id] = {
                    "id": evt.id,
                    "canonical_event_type": evt.canonical_event_type,
                    "description": evt.description,
                    "severity": evt.severity,
                }
        if imp.incident_id and imp.incident_id not in incidents_by_id:
            inc_result = await db.execute(
                select(Incident).filter(Incident.id == imp.incident_id)
            )
            inc = inc_result.scalar_one_or_none()
            if inc:
                incidents_by_id[inc.id] = {
                    "id": inc.id,
                    "title": inc.title,
                    "status": inc.status,
                }

    assessments_list = []
    for inc_id in incidents_by_id:
        analysis_result = await db.execute(
            select(IncidentAnalysis).filter(IncidentAnalysis.incident_id == inc_id)
        )
        analysis = analysis_result.scalar_one_or_none()
        if analysis:
            assessments_result = await db.execute(
                select(RootCauseAssessment).filter(
                    RootCauseAssessment.analysis_id == analysis.id
                )
            )
            assessments = assessments_result.scalars().all()
            for a in assessments:
                assessments_list.append(
                    {"id": a.id, "explanation": a.explanation, "incident_id": inc_id}
                )

    risk_result = await db.execute(
        select(WorkOrderRiskHistory)
        .filter(WorkOrderRiskHistory.work_order_id == work_order_id)
        .order_by(WorkOrderRiskHistory.created_at.desc())
    )
    latest_risk = risk_result.scalars().first()

    current_risk = None
    if latest_risk:
        current_risk = {
            "state": latest_risk.new_state,
            "calculated_at": latest_risk.created_at.isoformat(),
        }

    return WorkOrderContextResponse(
        work_order={"id": wo.id, "status": wo.status, "plant_id": wo.plant_id},
        current_risk=current_risk,
        active_impacts=[{"id": i.id, "status": "CONFIRMED"} for i in impacts],
        manufacturing_events=list(events_by_id.values()),
        incidents=list(incidents_by_id.values()),
        root_cause_assessments=assessments_list,
        active_alerts=None,
        context_generated_at=datetime.now(timezone.utc),
    )


async def get_incident_context(
    db: AsyncSession, company_id: str, incident_id: str
) -> IncidentContextResponse:
    inc_result = await db.execute(
        select(Incident).filter(
            Incident.id == incident_id, Incident.company_id == company_id
        )
    )
    inc = inc_result.scalar_one_or_none()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found")

    links_result = await db.execute(
        select(IncidentEvent).filter(
            IncidentEvent.incident_id == incident_id,
            IncidentEvent.link_state == "LINKED",
        )
    )
    links = links_result.scalars().all()

    events = []
    for ln in links:
        evt_result = await db.execute(
            select(ManufacturingEvent).filter(ManufacturingEvent.id == ln.event_id)
        )
        evt = evt_result.scalar_one_or_none()
        if evt:
            events.append(
                {
                    "id": evt.id,
                    "canonical_event_type": evt.canonical_event_type,
                    "description": evt.description,
                }
            )

    analysis_result = await db.execute(
        select(IncidentAnalysis)
        .filter(IncidentAnalysis.incident_id == incident_id)
        .order_by(IncidentAnalysis.version.desc())
    )
    analysis = analysis_result.scalars().first()

    confirmed_assessment = None
    evidence = []
    if analysis:
        assessments_result = await db.execute(
            select(RootCauseAssessment).filter(
                RootCauseAssessment.analysis_id == analysis.id
            )
        )
        assessments = assessments_result.scalars().all()
        if assessments:
            a = assessments[0]
            confirmed_assessment = {"id": a.id, "explanation": a.explanation}
            ev_links_result = await db.execute(
                select(AssessmentEvidenceLink).filter(
                    AssessmentEvidenceLink.assessment_id == a.id
                )
            )
            ev_links = ev_links_result.scalars().all()
            for el in ev_links:
                evidence.append({"event_id": el.event_id})

    impacts_result = await db.execute(
        select(ProductionOrderImpact).filter(
            ProductionOrderImpact.incident_id == incident_id,
            ProductionOrderImpact.company_id == company_id,
        )
    )
    impacts = impacts_result.scalars().all()

    affected_wos = []
    wo_risks = {}
    for imp in impacts:
        if imp.work_order_id:
            wo_result = await db.execute(
                select(WorkOrder).filter(WorkOrder.id == imp.work_order_id)
            )
            wo = wo_result.scalar_one_or_none()
            if wo:
                affected_wos.append({"id": wo.id, "status": wo.status})
                risk_result = await db.execute(
                    select(WorkOrderRiskHistory)
                    .filter(WorkOrderRiskHistory.work_order_id == wo.id)
                    .order_by(WorkOrderRiskHistory.created_at.desc())
                )
                latest_risk = risk_result.scalars().first()
                if latest_risk:
                    wo_risks[wo.id] = {"state": latest_risk.new_state}

    return IncidentContextResponse(
        incident={
            "id": inc.id,
            "status": inc.status,
            "title": inc.title,
            "plant_id": inc.plant_id,
        },
        manufacturing_events=events,
        evidence=evidence,
        confirmed_root_cause=confirmed_assessment,
        affected_work_orders=affected_wos,
        current_risk=wo_risks,
        active_alerts=None,
        context_generated_at=datetime.now(timezone.utc),
    )
