import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint

from app.infrastructure.database.session import Base


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    external_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    source_import_job_id = Column(String, ForeignKey("import_jobs.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "external_id", name="uq_customer_company_external_id"
        ),
    )


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    external_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    source_import_job_id = Column(String, ForeignKey("import_jobs.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "external_id", name="uq_vendor_company_external_id"
        ),
    )


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    sku = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    source_import_job_id = Column(String, ForeignKey("import_jobs.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id", "external_id", name="uq_product_company_external_id"
        ),
    )


class Machine(Base):
    __tablename__ = "machines"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, index=True)
    plant_id = Column(String, ForeignKey("plants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    external_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    source_import_job_id = Column(String, ForeignKey("import_jobs.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "plant_id",
            "external_id",
            name="uq_machine_company_plant_external_id",
        ),
    )
