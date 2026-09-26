import enum
import uuid

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.sql import func

from app.infrastructure.database.session import Base


class RiskState(enum.Enum):
    RESOLVED = "RESOLVED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    ON_TRACK = "ON_TRACK"
    PENDING_EVALUATION = "PENDING_EVALUATION"
    AT_RISK = "AT_RISK"
    DELAYED = "DELAYED"
    CRITICAL = "CRITICAL"


class RiskTriggerType(enum.Enum):
    IMPACT_GENERATED = "IMPACT_GENERATED"
    IMPACT_CONFIRMED = "IMPACT_CONFIRMED"
    IMPACT_REJECTED = "IMPACT_REJECTED"
    WORK_ORDER_UPDATED = "WORK_ORDER_UPDATED"
    INCIDENT_RESOLVED = "INCIDENT_RESOLVED"
    EVENT_UNLINKED = "EVENT_UNLINKED"


class WorkOrderRiskHistory(Base):
    __tablename__ = "work_order_risk_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    work_order_id = Column(
        String, ForeignKey("work_orders.id"), nullable=False, index=True
    )
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)

    previous_state = Column(Enum(RiskState, name="riskstate"), nullable=False)
    new_state = Column(Enum(RiskState, name="riskstate"), nullable=False)
    trigger_type = Column(Enum(RiskTriggerType, name="risktriggertype"), nullable=False)

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
