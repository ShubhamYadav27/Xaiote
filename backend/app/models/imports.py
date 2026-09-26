import datetime
import enum
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String

from app.infrastructure.database.session import Base


class ImportJobStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    VALIDATING = "VALIDATING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class ImportEntityType(str, enum.Enum):
    CUSTOMERS = "CUSTOMERS"
    VENDORS = "VENDORS"
    PRODUCTS = "PRODUCTS"
    MACHINES = "MACHINES"
    WORK_ORDERS = "WORK_ORDERS"


class ValidationStatus(str, enum.Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    status = Column(String, nullable=False, default=ImportJobStatus.RECEIVED.value)
    import_type = Column(String, nullable=False)

    source_filename = Column(String, nullable=False)
    source_file_hash = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)

    total_rows = Column(Integer, default=0)
    valid_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)
    needs_review_rows = Column(Integer, default=0)
    created_rows = Column(Integer, default=0)
    updated_rows = Column(Integer, default=0)
    unchanged_rows = Column(Integer, default=0)

    error_message = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ImportAuditAction(str, enum.Enum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"
    REJECTED = "REJECTED"


class ImportAudit(Base):
    __tablename__ = "import_audits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    import_job_id = Column(
        String, ForeignKey("import_jobs.id"), nullable=False, index=True
    )

    source_row_number = Column(Integer, nullable=False)
    target_entity_type = Column(String, nullable=False)
    target_record_id = Column(String, nullable=True)

    validation_status = Column(String, nullable=False)
    validation_reason = Column(String, nullable=True)

    action = Column(String, nullable=True)
    previous_source_import_job_id = Column(
        String, ForeignKey("import_jobs.id"), nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
