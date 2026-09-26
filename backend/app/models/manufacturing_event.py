import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)

from app.infrastructure.database.session import Base


class ProvenanceType(str, enum.Enum):
    EXPLICIT = "EXPLICIT"
    MODEL_DERIVED = "MODEL_DERIVED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class TemporalProvenance(str, enum.Enum):
    EXPLICIT_TIMESTAMP = "EXPLICIT_TIMESTAMP"
    DETERMINISTIC_RELATIVE_REFERENCE = "DETERMINISTIC_RELATIVE_REFERENCE"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class EventStatus(str, enum.Enum):
    CANONICAL = "CANONICAL"
    SUPERSEDED = "SUPERSEDED"
    REJECTED = "REJECTED"


class CanonicalizationJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class CanonicalizationJob(Base):
    __tablename__ = "canonicalization_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    candidate_id = Column(
        String,
        ForeignKey("entity_resolution_results.candidate_id"),
        unique=True,
        nullable=False,
    )
    status: CanonicalizationJobStatus = Column(
        SQLEnum(
            CanonicalizationJobStatus,
            name="canonicalizationjobstatus",
            create_constraint=False,
        ),
        default=CanonicalizationJobStatus.PENDING,
        nullable=False,
    )

    attempt_count = Column(Integer, default=0, nullable=False)
    last_error = Column(String, nullable=True)

    lease_until = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ManufacturingEvent(Base):
    __tablename__ = "manufacturing_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=True)
    candidate_id = Column(
        String,
        ForeignKey("entity_resolution_results.candidate_id"),
        unique=True,
        nullable=False,
    )
    event_idempotency_key = Column(String, nullable=False)

    canonical_event_type = Column(String, nullable=True)
    canonical_event_type_provenance: ProvenanceType = Column(
        SQLEnum(ProvenanceType, name="provenancetype", create_constraint=False),
        nullable=True,
    )

    description = Column(String, nullable=True)

    severity = Column(String, nullable=True)
    severity_provenance: ProvenanceType = Column(
        SQLEnum(ProvenanceType, name="provenancetype", create_constraint=False),
        nullable=True,
    )

    root_cause = Column(String, nullable=True)
    root_cause_provenance: ProvenanceType = Column(
        SQLEnum(ProvenanceType, name="provenancetype", create_constraint=False),
        nullable=True,
    )

    extracted_severity_candidate = Column(String, nullable=True)
    extracted_root_cause_candidate = Column(String, nullable=True)

    reported_downtime_minutes = Column(Integer, nullable=True)
    quantity_affected = Column(Integer, nullable=True)

    event_time_reference = Column(String, nullable=True)
    canonical_occurrence_timestamp = Column(DateTime(timezone=True), nullable=True)
    temporal_provenance: TemporalProvenance = Column(
        SQLEnum(TemporalProvenance, name="temporalprovenance", create_constraint=False),
        nullable=True,
    )

    event_status: EventStatus = Column(
        SQLEnum(EventStatus, name="eventstatus", create_constraint=False),
        nullable=False,
    )
    superseded_by_event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=True
    )
    correlation_id = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "event_idempotency_key", name="uix_company_event_idempotency"
        ),
        UniqueConstraint("id", "company_id", name="uq_event_company"),
    )


class ManufacturingEventRevision(Base):
    __tablename__ = "manufacturing_event_revisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=False, index=True
    )
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    revision_timestamp = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    from sqlalchemy.dialects.postgresql import JSONB

    changed_fields = Column(JSONB, nullable=False)

    reason = Column(String, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
