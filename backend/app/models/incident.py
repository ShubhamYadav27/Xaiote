import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum

from app.infrastructure.database.session import Base


class IncidentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"


class IncidentEventLinkState(str, enum.Enum):
    LINKED = "LINKED"
    UNLINKED = "UNLINKED"


class IncidentDecisionAction(str, enum.Enum):
    CREATED = "CREATED"
    EVENT_LINKED = "EVENT_LINKED"
    EVENT_UNLINKED = "EVENT_UNLINKED"
    RECOVERY_CONFIRMED = "RECOVERY_CONFIRMED"


class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False, index=True)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=True, index=True)

    title = Column(String, nullable=False)
    status = Column(
        SQLEnum(IncidentStatus, name="incidentstatus", create_constraint=False),
        nullable=False,
        default=IncidentStatus.ACTIVE,
    )

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
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("id", "company_id", name="uq_incident_company"),)


class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, index=True)
    event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=False, index=True
    )

    link_state = Column(
        SQLEnum(
            IncidentEventLinkState,
            name="incidenteventlinkstate",
            create_constraint=False,
        ),
        nullable=False,
        default=IncidentEventLinkState.LINKED,
    )

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
        UniqueConstraint("incident_id", "event_id", name="uq_incident_event"),
    )


class IncidentDecisionHistory(Base):
    __tablename__ = "incident_decision_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=True, index=True
    )

    action = Column(
        SQLEnum(
            IncidentDecisionAction,
            name="incidentdecisionaction",
            create_constraint=False,
        ),
        nullable=False,
    )

    previous_state = Column(String, nullable=True)
    new_state = Column(String, nullable=True)
    reason = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
