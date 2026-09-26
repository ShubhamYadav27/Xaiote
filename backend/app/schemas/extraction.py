from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    MACHINE_FAILURE = "MACHINE_FAILURE"
    DOWNTIME = "DOWNTIME"
    MATERIAL_SHORTAGE = "MATERIAL_SHORTAGE"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    MAINTENANCE_ISSUE = "MAINTENANCE_ISSUE"
    PRODUCTION_DELAY = "PRODUCTION_DELAY"
    SAFETY_INCIDENT = "SAFETY_INCIDENT"
    OTHER = "OTHER"


class SeverityCandidate(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ProvenanceTag(str, Enum):
    EXPLICIT = "EXPLICIT"
    MODEL_DERIVED = "MODEL_DERIVED"
    UNKNOWN = "UNKNOWN"


class ProvenanceString(BaseModel):
    value: str | None = None
    provenance: ProvenanceTag


class ProvenanceInteger(BaseModel):
    value: int | None = None
    provenance: ProvenanceTag


class ExtractionEventSchema(BaseModel):
    event_type: EventType | None = None
    event_description: str | None = Field(None, max_length=500)

    machine_reference: ProvenanceString | None = None
    work_order_reference: ProvenanceString | None = None
    customer_reference: ProvenanceString | None = None
    product_reference: ProvenanceString | None = None
    vendor_reference: ProvenanceString | None = None

    issue_category: ProvenanceString | None = None
    root_cause_candidate: ProvenanceString | None = None

    downtime_minutes: ProvenanceInteger | None = None
    severity_candidate: SeverityCandidate | None = None
    quantity_affected: ProvenanceInteger | None = None

    event_time_reference: str | None = Field(None, max_length=100)
    model_confidence: float | None = Field(None, ge=0.0, le=1.0)
