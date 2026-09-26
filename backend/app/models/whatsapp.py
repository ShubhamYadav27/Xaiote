import datetime
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


class WhatsAppIntegration(Base):
    __tablename__ = "whatsapp_integrations"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False, unique=True)
    external_business_account_id = Column(String, nullable=False)
    phone_number_id = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="PENDING")
    app_secret_encrypted = Column(String, nullable=False)
    access_token_encrypted = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


class AuthorizedSender(Base):
    __tablename__ = "authorized_senders"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    phone_number = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="ACTIVE")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    user = relationship("User", backref="authorized_senders")
    company = relationship("Company", backref="authorized_senders")
