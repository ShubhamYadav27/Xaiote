from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies.auth import get_current_company
from app.core.interfaces import ObjectStorage
from app.infrastructure.database.session import get_db
from app.infrastructure.storage.s3_storage import get_storage
from app.models.communication import CommunicationAttachment, CommunicationMessage
from app.models.company import Company
from app.schemas.communication import (
    CommunicationAttachmentResponse,
    CommunicationMessageCreate,
    CommunicationMessageResponse,
)

router = APIRouter()


import uuid
from pathlib import Path

from sqlalchemy.exc import IntegrityError


@router.post("")
async def ingest_evidence(
    message_in: CommunicationMessageCreate,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_company.id
    raw_payload_str = None
    if message_in.raw_payload is not None:
        import json

        raw_payload_str = (
            message_in.raw_payload
            if isinstance(message_in.raw_payload, str)
            else json.dumps(message_in.raw_payload)
        )
    message = CommunicationMessage(
        company_id=company_id,
        source_channel=message_in.source_channel,
        external_message_id=message_in.external_message_id,
        sender_identity=message_in.sender_identity,
        raw_payload=raw_payload_str,
        status=message_in.status if message_in.status else "RECEIVED",
    )
    db.add(message)

    try:
        await db.commit()
        await db.refresh(message)
        return {"data": CommunicationMessageResponse.model_validate(message)}
    except IntegrityError:
        await db.rollback()
        # Race collision, fallback to returning the existing record
        existing = await db.execute(
            select(CommunicationMessage).where(
                CommunicationMessage.company_id == company_id,
                CommunicationMessage.source_channel == message_in.source_channel,
                CommunicationMessage.external_message_id
                == message_in.external_message_id,
            )
        )
        existing_msg = existing.scalars().first()
        if existing_msg:
            return {"data": CommunicationMessageResponse.model_validate(existing_msg)}
        raise HTTPException(
            status_code=500, detail="Failed to resolve identical record"
        )


@router.post("/{message_id}/attachments")
async def upload_attachment(
    message_id: str,
    file: UploadFile = File(...),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
    storage: ObjectStorage = Depends(get_storage),
):
    company_id = current_company.id
    # Check if message exists and belongs to current company
    result = await db.execute(
        select(CommunicationMessage).where(
            CommunicationMessage.id == message_id,
            CommunicationMessage.company_id == company_id,
        )
    )
    message = result.scalars().first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    file_content = await file.read()
    file_size = len(file_content)

    # Block huge files immediately (50MB)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Payload Too Large")

    media_type = file.content_type or "application/octet-stream"
    original_filename = file.filename or "unknown_file"
    ext = Path(original_filename).suffix

    # Restrict extensions to safe types only (e.g. no .exe or .sh)
    unsafe_extensions = {".exe", ".sh", ".bat", ".cmd", ".msi"}
    if ext.lower() in unsafe_extensions:
        raise HTTPException(status_code=400, detail="Invalid attachment extension")

    # Using 'storage' bucket as default
    from app.core.config import settings

    bucket_name = settings.MINIO_BUCKET

    # Server generated unique attachment ID
    attachment_id = str(uuid.uuid4())
    object_storage_key = f"{company_id}/evidence/{message_id}/{attachment_id}{ext}"

    attachment = CommunicationAttachment(
        message_id=message_id,
        object_storage_key=object_storage_key,
        media_type=media_type,
        file_size=file_size,
    )
    db.add(attachment)

    try:
        await db.flush()  # flush to generate ID and check DB constraints
    except Exception:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail="Database write failed")

    try:
        await storage.upload(bucket_name, object_storage_key, file_content)
    except Exception:  # noqa: BLE001
        await db.rollback()
        raise HTTPException(status_code=500, detail="Storage upload failed")

    await db.commit()
    await db.refresh(attachment)

    return {"data": CommunicationAttachmentResponse.model_validate(attachment)}


@router.get("")
async def list_messages(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_company.id
    base_query = select(CommunicationMessage).where(
        CommunicationMessage.company_id == company_id
    )

    count_query = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = (
        base_query.order_by(CommunicationMessage.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    messages = result.scalars().all()

    return {
        "data": {
            "items": [CommunicationMessageResponse.model_validate(m) for m in messages],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }


@router.get("/{message_id}")
async def get_message(
    message_id: str,
    current_company: Company = Depends(get_current_company),
    db: AsyncSession = Depends(get_db),
):
    company_id = current_company.id
    result = await db.execute(
        select(CommunicationMessage).where(
            CommunicationMessage.id == message_id,
            CommunicationMessage.company_id == company_id,
        )
    )
    message = result.scalars().first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    return {"data": CommunicationMessageResponse.model_validate(message)}
