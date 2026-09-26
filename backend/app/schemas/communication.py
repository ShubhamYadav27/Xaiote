from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CommunicationAttachmentBase(BaseModel):
    media_type: str


class CommunicationAttachmentResponse(CommunicationAttachmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    message_id: str
    object_storage_key: str | None = None
    file_size: int | None = 0
    status: str = "MEDIA_PENDING"
    provider_media_id: str | None = None
    created_at: datetime
    updated_at: datetime


class CommunicationMessageBase(BaseModel):
    source_channel: str
    external_message_id: str
    sender_identity: str
    raw_payload: Any = None
    status: str | None = "RECEIVED"


class CommunicationMessageCreate(CommunicationMessageBase):
    pass


class CommunicationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    company_id: str
    source_channel: str
    external_message_id: str
    sender_identity: str
    raw_payload: str | None = None
    status: str | None = "RECEIVED"
    created_at: datetime
    updated_at: datetime
    attachments: list[CommunicationAttachmentResponse] = []
