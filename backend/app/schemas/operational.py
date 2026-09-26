from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class TimelineEntry(BaseModel):
    source_id: str
    source_type: str
    occurrence_time: datetime | None = None
    decision_time: datetime | None = None
    recorded_time: datetime
    presentation_time: datetime
    presentation_time_provenance: Literal[
        "OCCURRENCE_FALLBACK_RECORDED",
        "DECISION_FALLBACK_RECORDED",
        "EXPLICIT_OCCURRENCE",
        "EXPLICIT_DECISION",
    ]
    data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        orm_mode = True


class TimelineResponse(BaseModel):
    data: list[TimelineEntry]
    next_cursor: str | None = None
    context_generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class WorkOrderContextResponse(BaseModel):
    work_order: dict[str, Any]
    current_risk: dict[str, Any] | None = None
    active_impacts: list[dict[str, Any]] = Field(default_factory=list)
    manufacturing_events: list[dict[str, Any]] = Field(default_factory=list)
    incidents: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_assessments: list[dict[str, Any]] = Field(default_factory=list)
    active_alerts: list[dict[str, Any]] | None = None  # None for MVP
    context_generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class IncidentContextResponse(BaseModel):
    incident: dict[str, Any]
    manufacturing_events: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confirmed_root_cause: dict[str, Any] | None = None
    affected_work_orders: list[dict[str, Any]] = Field(default_factory=list)
    current_risk: dict[str, dict[str, Any] | None] = Field(
        default_factory=dict
    )  # work_order_id -> risk
    active_alerts: list[dict[str, Any]] | None = None  # None for MVP
    context_generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class OperationalContextEnvelope(BaseModel):
    data: Any
