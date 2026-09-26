import datetime
import enum
import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)

from app.infrastructure.database.session import Base


class WorkOrderStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ON_HOLD = "ON_HOLD"


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False, index=True)

    customer_id = Column(String, ForeignKey("customers.id"), nullable=True, index=True)
    product_id = Column(String, ForeignKey("products.id"), nullable=False, index=True)
    machine_id = Column(String, ForeignKey("machines.id"), nullable=True, index=True)

    order_number = Column(String, nullable=False, index=True)
    quantity = Column(Numeric(precision=10, scale=2), nullable=False)
    planned_production_info = Column(String, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(String, nullable=False, default=WorkOrderStatus.PLANNED.value)
    production_progress = Column(
        Numeric(precision=5, scale=2), nullable=True, default=0.0
    )

    external_id = Column(String, nullable=True)
    source_import_job_id = Column(
        String, ForeignKey("import_jobs.id"), nullable=True
    )  # FK to import_jobs (Phase 2D)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "plant_id",
            "order_number",
            name="uq_work_order_company_plant_order_number",
        ),
        CheckConstraint("quantity >= 0", name="chk_work_order_quantity_positive"),
        CheckConstraint(
            "production_progress >= 0 AND production_progress <= 100",
            name="chk_work_order_progress_range",
        ),
    )
