import enum
import uuid

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base

class RecommendationState(str, enum.Enum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"
    CONVERTED = "CONVERTED"

class ActionRecommendation(Base):
    __tablename__ = "action_recommendations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=True)
    generation_request_id = Column(String, nullable=False)
    
    context_hash = Column(String, nullable=False)
    prompt_hash = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)
    model_provider_id = Column(String, nullable=True)
    
    action_type = Column(String, nullable=False)
    target_work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    target_machine_id = Column(String, ForeignKey("machines.id"), nullable=True)
    target_product_id = Column(String, ForeignKey("products.id"), nullable=True)
    
    rationale = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    action_parameters = Column(JSONB, nullable=True)
    
    policy_id = Column(String, nullable=False)
    policy_version = Column(Integer, nullable=False)
    
    status = Column(String, nullable=False, default=RecommendationState.PROPOSED.value)
    stale_reason = Column(String, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("company_id", "generation_request_id", name="uq_recommendation_generation_request"),
        CheckConstraint(
            "(target_work_order_id IS NOT NULL)::int + "
            "(target_machine_id IS NOT NULL)::int + "
            "(target_product_id IS NOT NULL)::int = 1",
            name="ck_recommendation_target_xor"
        ),
    )

class RecommendationEvidenceLink(Base):
    __tablename__ = "recommendation_evidence_links"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    recommendation_id = Column(String, ForeignKey("action_recommendations.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)

    evidence_alert_id = Column(String, ForeignKey("alert_instances.id"), nullable=True)
    evidence_risk_history_id = Column(String, ForeignKey("work_order_risk_history.id"), nullable=True)
    evidence_root_cause_assessment_id = Column(String, ForeignKey("root_cause_assessments.id"), nullable=True)
    evidence_manufacturing_event_id = Column(String, ForeignKey("manufacturing_events.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(evidence_alert_id IS NOT NULL)::int + "
            "(evidence_risk_history_id IS NOT NULL)::int + "
            "(evidence_root_cause_assessment_id IS NOT NULL)::int + "
            "(evidence_manufacturing_event_id IS NOT NULL)::int = 1",
            name="ck_recommendation_evidence_xor"
        ),
    )

class RecommendationConversion(Base):
    __tablename__ = "recommendation_conversions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    recommendation_id = Column(String, ForeignKey("action_recommendations.id"), nullable=False)
    action_instance_id = Column(String, ForeignKey("action_instances.id"), nullable=False)
    conversion_idempotency_key = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("recommendation_id", name="uq_conversion_recommendation"),
        UniqueConstraint("action_instance_id", name="uq_conversion_action_instance"),
        UniqueConstraint("conversion_idempotency_key", name="uq_conversion_idempotency_key"),
    )
