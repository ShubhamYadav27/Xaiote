import uuid
import enum

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, CheckConstraint, ForeignKeyConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base

class ActionLifecycleState(str, enum.Enum):
    PROPOSED = "PROPOSED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class ActorType(str, enum.Enum):
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"

class ActionOutcomeState(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    PARTIAL = "PARTIAL"

class ActionPolicy(Base):
    __tablename__ = "action_policies"
    pk = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    id = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    approval_level = Column(Integer, nullable=False, default=2)

    __table_args__ = (
        UniqueConstraint("company_id", "id", "version", name="uq_action_policy_identity"),
    )

class ActionInstance(Base):
    __tablename__ = "action_instances"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=True)

    policy_id = Column(String, nullable=False)
    policy_version = Column(Integer, nullable=False)

    action_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default=ActionLifecycleState.PROPOSED.value)
    version = Column(Integer, nullable=False, default=1)

    target_work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    target_machine_id = Column(String, ForeignKey("machines.id"), nullable=True)
    target_product_id = Column(String, ForeignKey("products.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "policy_id", "policy_version"],
            ["action_policies.company_id", "action_policies.id", "action_policies.version"],
            name="fk_action_instance_policy"
        ),
        CheckConstraint(
            """
            (target_work_order_id IS NOT NULL)::int +
            (target_machine_id IS NOT NULL)::int +
            (target_product_id IS NOT NULL)::int = 1
            """,
            name="ck_action_instance_target_xor"
        ),
    )

class ActionEvidenceLink(Base):
    __tablename__ = "action_evidence_links"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_instance_id = Column(String, ForeignKey("action_instances.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)

    evidence_alert_id = Column(String, ForeignKey("alert_instances.id"), nullable=True)
    evidence_risk_history_id = Column(String, ForeignKey("work_order_risk_history.id"), nullable=True)
    evidence_root_cause_assessment_id = Column(String, ForeignKey("root_cause_assessments.id"), nullable=True)
    evidence_manufacturing_event_id = Column(String, ForeignKey("manufacturing_events.id"), nullable=True)

    __table_args__ = (
        CheckConstraint(
            """
            (evidence_alert_id IS NOT NULL)::int +
            (evidence_risk_history_id IS NOT NULL)::int +
            (evidence_root_cause_assessment_id IS NOT NULL)::int +
            (evidence_manufacturing_event_id IS NOT NULL)::int = 1
            """,
            name="ck_action_evidence_xor"
        ),
    )

class ActionHistory(Base):
    __tablename__ = "action_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String, ForeignKey("action_instances.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    previous_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)

    actor_id = Column(String, nullable=False)
    actor_type = Column(String, nullable=False)

    reason = Column(String, nullable=True)
    
    policy_id = Column(String, nullable=False)
    policy_version = Column(Integer, nullable=False)
    action_version = Column(Integer, nullable=False)

    correlation_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ActionOutcome(Base):
    __tablename__ = "action_outcomes"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id = Column(String, ForeignKey("action_instances.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    outcome_state = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

