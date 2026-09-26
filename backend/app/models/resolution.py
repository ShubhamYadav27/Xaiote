import datetime
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.infrastructure.database.session import Base


class EntityResolutionResult(Base):
    __tablename__ = "entity_resolution_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    candidate_id = Column(
        String, ForeignKey("extracted_event_candidates.id"), unique=True, nullable=False
    )

    processing_status = Column(String, nullable=False, default="PENDING", index=True)
    overall_status = Column(String, nullable=False, default="PENDING", index=True)

    machine_state = Column(String, nullable=False, default="PENDING")
    work_order_state = Column(String, nullable=False, default="PENDING")
    customer_state = Column(String, nullable=False, default="PENDING")
    product_state = Column(String, nullable=False, default="PENDING")
    vendor_state = Column(String, nullable=False, default="PENDING")

    machine_id = Column(String, ForeignKey("machines.id"), nullable=True)
    work_order_id = Column(String, ForeignKey("work_orders.id"), nullable=True)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    vendor_id = Column(String, ForeignKey("vendors.id"), nullable=True)

    automated_audit = Column(JSONB, nullable=True)
    human_review_audit = Column(JSONB, nullable=True)

    lease_until = Column(DateTime(timezone=True), nullable=True, index=True)
    worker_id = Column(String, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
