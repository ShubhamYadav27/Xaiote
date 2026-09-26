import uuid
import enum
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Enum, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base
from sqlalchemy.dialects.postgresql import JSONB

class ExecutionAttemptState(str, enum.Enum):
    ACCEPTED = "ACCEPTED"
    CONFIRMATION_TIMEOUT = "CONFIRMATION_TIMEOUT"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"

class ExecutionAttempt(Base):
    __tablename__ = "execution_attempts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    action_instance_id = Column(String, ForeignKey("action_instances.id"), nullable=False)
    
    attempt_number = Column(Integer, nullable=False)
    downstream_idempotency_key = Column(String, nullable=False)
    
    status = Column(String, nullable=False, default=ExecutionAttemptState.PENDING.value)
    provider_type = Column(String, nullable=False)
    
    worker_id = Column(String, nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    external_correlation_id = Column(String, nullable=True)
    
    # Store JSON natively for error structures
    error_payload = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("action_instance_id", "attempt_number", name="uq_execution_attempt_number"),
        UniqueConstraint("company_id", "downstream_idempotency_key", name="uq_execution_idempotency_key"),
    )

