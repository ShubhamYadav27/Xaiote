import datetime
from sqlalchemy import Column, DateTime, ForeignKeyConstraint, String, UniqueConstraint
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base

class UserPlant(Base):
    __tablename__ = "user_plants"

    user_id = Column(String, nullable=False, primary_key=True)
    plant_id = Column(String, nullable=False, primary_key=True)
    company_id = Column(String, nullable=False)
    
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "plant_id", name="uq_user_plants_user_id_plant_id"),
        ForeignKeyConstraint(
            ["company_id", "user_id"],
            ["users.company_id", "users.id"],
            name="fk_user_plants_user_company"
        ),
        ForeignKeyConstraint(
            ["company_id", "plant_id"],
            ["plants.company_id", "plants.id"],
            name="fk_user_plants_plant_company"
        ),
    )
