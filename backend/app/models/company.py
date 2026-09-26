import datetime
import uuid

from sqlalchemy import Column, DateTime, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    industry = Column(String, nullable=True)
    revenue_range = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    users = relationship("User", back_populates="company")
    plants = relationship("Plant", back_populates="company")
