import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)

from app.infrastructure.database.session import Base


class AlertStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"



class AlertEvaluationJobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AlertSeverity(str, enum.Enum):
    AT_RISK = "AT_RISK"
    DELAYED = "DELAYED"
    CRITICAL = "CRITICAL"


class AlertPolicy(Base):
    __tablename__ = "alert_policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(
        String, ForeignKey("companies.id"), nullable=False, primary_key=True
    )
    version = Column(Integer, nullable=False, primary_key=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

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
        UniqueConstraint("company_id", "id", "version", name="uq_alert_policy_version"),
    )


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(
        String, ForeignKey("companies.id"), nullable=False, primary_key=True
    )
    version = Column(Integer, nullable=False, primary_key=True)

    policy_id = Column(String, nullable=False)
    policy_version = Column(Integer, nullable=False)

    alert_family = Column(String, nullable=False)
    severity = Column(String, nullable=False)

    trigger_condition = Column(JSON, nullable=False)
    clear_condition = Column(JSON, nullable=False)

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
        UniqueConstraint("company_id", "id", "version", name="uq_alert_rule_version"),
        ForeignKeyConstraint(
            ["company_id", "policy_id", "policy_version"],
            [
                "alert_policies.company_id",
                "alert_policies.id",
                "alert_policies.version",
            ],
            name="fk_alert_rule_policy",
        ),
    )


class AlertInstance(Base):
    __tablename__ = "alert_instances"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False)

    alert_family = Column(String, nullable=False)

    target_work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    target_incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)

    originating_policy_id = Column(String, nullable=False)
    originating_policy_version = Column(Integer, nullable=False)
    originating_rule_id = Column(String, nullable=False)
    originating_rule_version = Column(Integer, nullable=False)

    current_policy_id = Column(String, nullable=False)
    current_policy_version = Column(Integer, nullable=False)
    current_rule_id = Column(String, nullable=False)
    current_rule_version = Column(Integer, nullable=False)

    status = Column(String, nullable=False)
    severity = Column(String, nullable=False)

    version = Column(Integer, default=1, nullable=False)  # OCC

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
            ["company_id", "originating_rule_id", "originating_rule_version"],
            ["alert_rules.company_id", "alert_rules.id", "alert_rules.version"],
            name="fk_alert_instance_originating_rule",
        ),
        ForeignKeyConstraint(
            ["company_id", "current_rule_id", "current_rule_version"],
            ["alert_rules.company_id", "alert_rules.id", "alert_rules.version"],
            name="fk_alert_instance_current_rule",
        ),
        CheckConstraint(
            "(CASE WHEN target_work_order_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN target_incident_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_alert_instance_target_xor",
        ),
        Index(
            "ix_alert_instances_dedup_wo",
            "company_id",
            "alert_family",
            "target_work_order_id",
            unique=True,
            postgresql_where=text(
                "status IN ('ACTIVE', 'ACKNOWLEDGED') AND target_work_order_id IS NOT NULL"
            ),
        ),
        Index(
            "ix_alert_instances_dedup_inc",
            "company_id",
            "alert_family",
            "target_incident_id",
            unique=True,
            postgresql_where=text(
                "status IN ('ACTIVE', 'ACKNOWLEDGED') AND target_incident_id IS NOT NULL"
            ),
        ),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_instance_id = Column(String, ForeignKey("alert_instances.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)

    action = Column(
        String, nullable=False
    )  # e.g. ESCALATED, ACKNOWLEDGED, RESOLVED, CREATED
    previous_severity = Column(String, nullable=True)
    new_severity = Column(String, nullable=True)

    previous_policy_id = Column(String, nullable=True)
    previous_policy_version = Column(Integer, nullable=True)
    previous_rule_id = Column(String, nullable=True)
    previous_rule_version = Column(Integer, nullable=True)

    new_policy_id = Column(String, nullable=True)
    new_policy_version = Column(Integer, nullable=True)
    new_rule_id = Column(String, nullable=True)
    new_rule_version = Column(Integer, nullable=True)

    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "previous_rule_id", "previous_rule_version"],
            ["alert_rules.company_id", "alert_rules.id", "alert_rules.version"],
            name="fk_alert_history_prev_rule",
        ),
        ForeignKeyConstraint(
            ["company_id", "new_rule_id", "new_rule_version"],
            ["alert_rules.company_id", "alert_rules.id", "alert_rules.version"],
            name="fk_alert_history_new_rule",
        ),
    )


class AlertEvidenceLink(Base):
    __tablename__ = "alert_evidence_links"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_instance_id = Column(String, ForeignKey("alert_instances.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)

    evidence_manufacturing_event_id = Column(
        String, ForeignKey("manufacturing_events.id"), nullable=True
    )
    evidence_production_order_impact_id = Column(
        String, ForeignKey("production_order_impacts.id"), nullable=True
    )
    evidence_risk_history_id = Column(
        String, ForeignKey("work_order_risk_history.id"), nullable=True
    )
    evidence_root_cause_assessment_id = Column(
        String, ForeignKey("root_cause_assessments.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN evidence_manufacturing_event_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN evidence_production_order_impact_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN evidence_risk_history_id IS NOT NULL THEN 1 ELSE 0 END) + "
            "(CASE WHEN evidence_root_cause_assessment_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_alert_evidence_xor",
        ),
    )


class AlertEvaluationJob(Base):
    __tablename__ = "alert_evaluation_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False)

    target_work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    target_incident_id = Column(String, ForeignKey("incidents.id"), nullable=True)

    status = Column(String, default=AlertEvaluationJobStatus.PENDING.value, nullable=False)
    worker_id = Column(String, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    error_detail = Column(String, nullable=True)

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
        CheckConstraint(
            "(CASE WHEN target_work_order_id IS NOT NULL THEN 1 ELSE 0 END) + (CASE WHEN target_incident_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_alert_eval_job_target_xor"
        ),
    )


class AlertEvaluationJobRetryAudit(Base):
    __tablename__ = "alert_evaluation_job_retry_audits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey("alert_evaluation_jobs.id"), nullable=False)
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    
    actor_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    previous_state = Column(String, nullable=False)
    new_state = Column(String, nullable=False)
    
    original_error = Column(String, nullable=True)
    retry_reason = Column(String, nullable=False)
    
    timestamp = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
