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
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


class ImpactStatus(str, enum.Enum):
    POTENTIAL = "POTENTIAL"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"


class ImpactProvenance(str, enum.Enum):
    EXPLICIT_WORK_ORDER_RESOLUTION = "EXPLICIT_WORK_ORDER_RESOLUTION"
    MACHINE_CONTEXT_DERIVED = "MACHINE_CONTEXT_DERIVED"
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"
    HUMAN_REJECTED = "HUMAN_REJECTED"


class ProductionOrderImpact(Base):
    __tablename__ = "production_order_impacts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False, index=True)
    event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=False, index=True
    )
    work_order_id = Column(
        String, ForeignKey("work_orders.id"), nullable=False, index=True
    )
    incident_id = Column(String, ForeignKey("incidents.id"), nullable=True, index=True)

    status: ImpactStatus = Column(
        SQLEnum(ImpactStatus, name="impactstatus", create_constraint=False),
        nullable=False,
    )
    provenance: ImpactProvenance = Column(
        SQLEnum(ImpactProvenance, name="impactprovenance", create_constraint=False),
        nullable=False,
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
        UniqueConstraint("event_id", "work_order_id", name="uq_impact_event_wo"),
    )

    incident = relationship("Incident", lazy="joined")


class ImpactDecisionHistory(Base):
    __tablename__ = "impact_decision_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    impact_id = Column(
        String, ForeignKey("production_order_impacts.id"), nullable=False, index=True
    )
    actor_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)

    previous_status: ImpactStatus = Column(String, nullable=True)
    new_status: ImpactStatus = Column(String, nullable=False)
    provenance: ImpactProvenance = Column(String, nullable=False)
    reason = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
