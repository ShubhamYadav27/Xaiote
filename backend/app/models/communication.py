import datetime
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.infrastructure.database.session import Base


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "source_channel",
            "external_message_id",
            name="uq_comm_msg_external_id",
        ),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    source_channel = Column(String, nullable=False)
    external_message_id = Column(String, nullable=False)
    sender_identity = Column(String, nullable=False)
    raw_payload = Column(String, nullable=True)
    status = Column(String, nullable=False, default="RECEIVED")
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    attachments = relationship(
        "CommunicationAttachment", back_populates="message", lazy="selectin"
    )


class CommunicationAttachment(Base):
    __tablename__ = "communication_attachments"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message_id = Column(String, ForeignKey("communication_messages.id"), nullable=False)
    media_type = Column(String, nullable=False)
    object_storage_key = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="MEDIA_PENDING")
    provider_media_id = Column(String, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(String, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    message = relationship(
        "CommunicationMessage", back_populates="attachments", lazy="selectin"
    )
    transcript = relationship(
        "CommunicationTranscript",
        back_populates="attachment",
        uselist=False,
        lazy="selectin",
    )


class CommunicationTranscript(Base):
    __tablename__ = "communication_transcripts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    attachment_id = Column(
        String, ForeignKey("communication_attachments.id"), unique=True, nullable=False
    )

    # Provenance
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    language = Column(String, nullable=True)

    # Transcripts
    provider_transcript = Column(Text, nullable=True)
    corrected_transcript = Column(Text, nullable=True)
    correction_metadata = Column(JSONB, nullable=True)

    # Telemetry
    confidence = Column(Float, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    provider_request_id = Column(String, nullable=True)

    # Durable State Machine
    status = Column(String, nullable=False, default="PENDING")
    retry_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True)
    worker_id = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    attachment = relationship("CommunicationAttachment", back_populates="transcript")
    extracted_candidate = relationship(
        "ExtractedEventCandidate",
        back_populates="transcript",
        uselist=False,
        lazy="selectin",
    )


class ExtractedEventCandidate(Base):
    __tablename__ = "extracted_event_candidates"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String, ForeignKey("companies.id"), nullable=False)
    transcript_id = Column(
        String, ForeignKey("communication_transcripts.id"), unique=True, nullable=False
    )

    # State tracking
    processing_status = Column(String, nullable=False, default="PENDING", index=True)
    validation_status = Column(String, nullable=True)

    # Reproducibility
    provider = Column(String, nullable=True)
    model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    prompt_hash = Column(String, nullable=True)
    schema_version = Column(String, nullable=True)
    schema_hash = Column(String, nullable=True)

    # Outputs
    payload = Column(JSONB, nullable=True)
    raw_llm_response = Column(Text, nullable=True)

    # Human Review
    human_correction_payload = Column(JSONB, nullable=True)
    corrected_by = Column(String, nullable=True)
    corrected_at = Column(DateTime(timezone=True), nullable=True)
    correction_reason = Column(Text, nullable=True)

    # Cost & Observability
    input_tokens = Column(Integer, nullable=True)
    output_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    provider_request_id = Column(String, nullable=True)

    # Worker & Recovery
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    lease_until = Column(DateTime(timezone=True), nullable=True, index=True)
    worker_id = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
    )

    transcript = relationship(
        "CommunicationTranscript", back_populates="extracted_candidate"
    )
