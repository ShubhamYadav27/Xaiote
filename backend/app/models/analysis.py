import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum

from app.infrastructure.database.session import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class AssessmentStatus(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class CauseCategory(str, enum.Enum):
    MECHANICAL = "MECHANICAL"
    ELECTRICAL = "ELECTRICAL"
    MATERIAL = "MATERIAL"
    PROCESS = "PROCESS"
    HUMAN_OPERATIONAL = "HUMAN_OPERATIONAL"
    MAINTENANCE = "MAINTENANCE"
    QUALITY = "QUALITY"
    SUPPLIER = "SUPPLIER"
    ENVIRONMENTAL = "ENVIRONMENTAL"
    OTHER = "OTHER"


class AssessmentRole(str, enum.Enum):
    PRIMARY = "PRIMARY"
    CONTRIBUTING = "CONTRIBUTING"


class EvidenceRelationship(str, enum.Enum):
    SUPPORTING = "SUPPORTING"
    CONFLICTING = "CONFLICTING"


class ProvenanceType(str, enum.Enum):
    EXPLICIT = "EXPLICIT"
    MODEL_DERIVED = "MODEL_DERIVED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    # UNKNOWN is purposely omitted from assessment level as it's represented by 0 causes on completed analysis.


class IncidentAnalysis(Base):
    __tablename__ = "incident_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=False, index=True)

    version = Column(Integer, nullable=False, default=1)
    status: Any = Column(
        SQLEnum(AnalysisStatus, name="analysisstatus", create_constraint=False),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )

    # Hashed deterministic ordered list of event IDs for the snapshot
    evidence_snapshot_hash = Column(String, nullable=False)
    # Hashed inputs (evidence_snapshot_hash + prompt_v + schema_v + config)
    generation_fingerprint = Column(String, nullable=False)
    # E.g. client provided idempotency key (header) for the HTTP request to prevent retries
    request_idempotency_key = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["incident_id", "company_id"],
            ["incidents.id", "incidents.company_id"],
            name="fk_analysis_incident_company",
        ),
        UniqueConstraint("id", "company_id", name="uq_analysis_company"),
    )


class RootCauseAssessment(Base):
    __tablename__ = "root_cause_assessments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    analysis_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=False, index=True)

    revision = Column(Integer, nullable=False, default=1)

    status: Any = Column(
        SQLEnum(AssessmentStatus, name="assessmentstatus", create_constraint=False),
        nullable=False,
        default=AssessmentStatus.CANDIDATE,
    )
    category: Any = Column(
        SQLEnum(CauseCategory, name="causecategory", create_constraint=False),
        nullable=False,
    )
    role: Any = Column(
        SQLEnum(AssessmentRole, name="assessmentrole", create_constraint=False),
        nullable=False,
    )
    explanation = Column(String, nullable=False)

    provenance: Any = Column(
        SQLEnum(ProvenanceType, name="provenancetype", create_constraint=False),
        nullable=False,
    )

    model_confidence = Column(Float, nullable=True)  # Heuristic, not probability

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["analysis_id", "company_id"],
            ["incident_analyses.id", "incident_analyses.company_id"],
            name="fk_assessment_analysis_company",
        ),
        UniqueConstraint("id", "company_id", name="uq_assessment_company"),
    )


class AssessmentEvidenceLink(Base):
    __tablename__ = "assessment_evidence_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, nullable=False, index=True)
    event_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=False, index=True)

    relationship_type: Any = Column(
        SQLEnum(
            EvidenceRelationship, name="evidencerelationship", create_constraint=False
        ),
        nullable=False,
        default=EvidenceRelationship.SUPPORTING,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["assessment_id", "company_id"],
            ["root_cause_assessments.id", "root_cause_assessments.company_id"],
            name="fk_link_assessment_company",
        ),
        ForeignKeyConstraint(
            ["event_id", "company_id"],
            ["manufacturing_events.id", "manufacturing_events.company_id"],
            name="fk_link_event_company",
        ),
    )


class AssessmentDecisionHistory(Base):
    __tablename__ = "assessment_decision_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = Column(String, nullable=False, index=True)
    company_id = Column(String, nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    action = Column(
        String, nullable=False
    )  # e.g. "CONFIRMED", "REJECTED", "SUPERSEDED"
    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    analysis_version = Column(Integer, nullable=False)

    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["assessment_id", "company_id"],
            ["root_cause_assessments.id", "root_cause_assessments.company_id"],
            name="fk_history_assessment_company",
        ),
    )
