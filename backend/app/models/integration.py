import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, ForeignKeyConstraint, Index
from sqlalchemy.sql import func, text
from app.infrastructure.database.session import Base
from sqlalchemy.dialects.postgresql import JSONB

class ExternalIntegration(Base):
    __tablename__ = "external_integrations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    plant_id = Column(String, nullable=True)
    
    provider = Column(String, nullable=False)
    adapter_type = Column(String, nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    environment = Column(String, nullable=False) 
    
    credential_reference = Column(String, nullable=False)
    credential_version = Column(Integer, nullable=False, default=1)
    
    supported_operations = Column(JSONB, nullable=False)
    capability_metadata = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        ForeignKeyConstraint(
            ['company_id', 'plant_id'], 
            ['plants.company_id', 'plants.id'], 
            name="fk_ext_int_composite_plant"
        ),
        UniqueConstraint("company_id", "plant_id", "provider", "environment", name="uq_integration_scope"),
        Index(
            'uq_integration_scope_null_plant', 
            'company_id', 'provider', 'environment', 
            unique=True, 
            postgresql_where=text("plant_id IS NULL")
        )
    )
