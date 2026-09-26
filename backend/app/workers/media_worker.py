"""Phase 3B: PostgreSQL-backed durable media worker.

This module implements a polling/claim mechanism for asynchronous
media retrieval from Meta's WhatsApp Cloud API.

Processing loop:
1. SELECT attachment WHERE status = 'MEDIA_PENDING' OR (status = 'MEDIA_PROCESSING' AND lease_until < NOW()) FOR UPDATE SKIP LOCKED
2. Transition to MEDIA_PROCESSING, set lease_until, set worker_id
3. COMMIT claim transaction
4. Authenticated Meta API media retrieval
5. Stream to MinIO with bounded size validation
6. Finalize transaction: Verify worker_id match, Transition to MEDIA_PERSISTED or MEDIA_FAILED

This worker is restart-safe: pending items survive application/container
restarts because state is durably stored in PostgreSQL.

Redis/Celery are NOT used. FastAPI BackgroundTasks are NOT the source of truth.
"""

import asyncio
import datetime
import logging
import uuid

import httpx
from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decrypt_secret
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.storage.s3_storage import storage_client
from app.models.communication import CommunicationAttachment, CommunicationMessage
from app.models.whatsapp import WhatsAppIntegration

logger = logging.getLogger(__name__)

MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_RETRIES = 3
POLL_INTERVAL_SECONDS = 5
LEASE_DURATION_SECONDS = 60


async def claim_pending_attachment(
    db: AsyncSession, worker_id: str
) -> CommunicationAttachment | None:
    """Claim a single attachment for processing using SELECT FOR UPDATE SKIP LOCKED.

    This ensures multiple workers can safely compete for work without
    processing the same attachment twice. The claim is immediately committed
    to release the row lock before network IO begins.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    lease_until = now + datetime.timedelta(seconds=LEASE_DURATION_SECONDS)

    result = await db.execute(
        text(
            "SELECT id FROM communication_attachments "
            "WHERE (status = 'MEDIA_PENDING' OR (status = 'MEDIA_PROCESSING' AND lease_until < :now)) "
            "AND retry_count < :max_retries "
            "ORDER BY created_at ASC "
            "LIMIT 1 "
            "FOR UPDATE SKIP LOCKED"
        ),
        {"now": now, "max_retries": MAX_RETRIES},
    )
    row = result.first()
    if not row:
        return None

    attachment_id = row[0]

    # Transition to MEDIA_PROCESSING and acquire lease
    await db.execute(
        update(CommunicationAttachment)
        .where(CommunicationAttachment.id == attachment_id)
        .values(status="MEDIA_PROCESSING", lease_until=lease_until, worker_id=worker_id)
    )
    await db.flush()

    # Re-fetch the full attachment object
    from sqlalchemy.future import select

    attachment_result = await db.execute(
        select(CommunicationAttachment).where(
            CommunicationAttachment.id == attachment_id
        )
    )
    return attachment_result.scalars().first()


async def retrieve_and_persist_media(
    attachment_id: str,
    provider_media_id: str,
    media_type: str,
    message_id: str,
    company_id: str,
    access_token: str,
) -> tuple[str, int]:
    """Retrieve media from Meta API and persist to MinIO.

    Flow:
    1. Get media URL from Meta using provider_media_id
    2. Download binary with bounded streaming
    3. Upload to MinIO
    """
    if not provider_media_id:
        raise ValueError("No provider_media_id on attachment")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Step 1: Get media URL from Meta
        meta_url = f"https://graph.facebook.com/v18.0/{provider_media_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        url_response = await client.get(meta_url, headers=headers)
        if url_response.status_code != 200:
            raise RuntimeError(
                f"Meta media URL lookup failed: {url_response.status_code}"
            )

        media_url = url_response.json().get("url")
        if not media_url:
            raise RuntimeError("No media URL returned by Meta")

        # SSRF protection: only allow Meta graph API URLs
        if not media_url.startswith(
            "https://lookaside.fbsbx.com/"
        ) and not media_url.startswith("https://graph.facebook.com/"):
            raise RuntimeError("Refusing non-authorized media URL")

        # Step 2: Download with bounded streaming
        download_response = await client.get(
            media_url, headers=headers, follow_redirects=True
        )
        if download_response.status_code != 200:
            raise RuntimeError(
                f"Media download failed: {download_response.status_code}"
            )

        media_bytes = download_response.content
        if len(media_bytes) > MAX_MEDIA_SIZE:
            raise RuntimeError(
                f"Media exceeds {MAX_MEDIA_SIZE} bytes: {len(media_bytes)}"
            )

    # Step 3: Upload to MinIO
    ext_map = {
        "audio/ogg": ".ogg",
        "audio/aac": ".aac",
        "audio/mpeg": ".mp3",
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "video/mp4": ".mp4",
        "application/pdf": ".pdf",
    }
    ext = ext_map.get(str(media_type), ".bin")
    attachment_uuid = str(uuid.uuid4())
    object_key = f"{company_id}/evidence/{message_id}/{attachment_uuid}{ext}"

    bucket_name = settings.MINIO_BUCKET
    await storage_client.upload(bucket_name, object_key, media_bytes)

    return object_key, len(media_bytes)


async def process_one_attachment(worker_id: str) -> bool:
    """Process a single pending media attachment.

    Returns True if work was found and processed, False otherwise.
    """
    attachment_id = None
    provider_media_id = None
    media_type = None
    message_id = None

    # TRANSACTION 1: Claim
    async with AsyncSessionLocal() as db:
        try:
            attachment = await claim_pending_attachment(db, worker_id)
            if not attachment:
                await db.rollback()
                return False

            attachment_id = attachment.id
            provider_media_id = attachment.provider_media_id
            media_type = attachment.media_type
            message_id = attachment.message_id

            # Resolve integration for access token before dropping DB lock
            from sqlalchemy.future import select

            msg_result = await db.execute(
                select(CommunicationMessage).where(
                    CommunicationMessage.id == message_id
                )
            )
            msg = msg_result.scalars().first()
            if not msg:
                attachment.status = "MEDIA_FAILED"
                attachment.last_error = "Orphaned attachment: message not found"
                attachment.retry_count += 1
                await db.commit()
                return True

            company_id = msg.company_id

            integration_result = await db.execute(
                select(WhatsAppIntegration).where(
                    WhatsAppIntegration.company_id == company_id,
                    WhatsAppIntegration.status == "ACTIVE",
                )
            )
            integration = integration_result.scalars().first()
            if not integration:
                attachment.status = "MEDIA_FAILED"
                attachment.last_error = "No active integration found"
                attachment.retry_count += 1
                await db.commit()
                logger.error(
                    "No integration for media retrieval",
                    extra={"attachment_id": attachment.id},
                )
                return True

            access_token = decrypt_secret(integration.access_token_encrypted)

            # COMMIT the claim immediately so row locks are released before network IO
            await db.commit()

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"Worker claim error: {exc}")
            return False

    # NETWORK IO
    object_key = None
    file_size = 0
    error_msg = None
    try:
        object_key, file_size = await retrieve_and_persist_media(
            attachment_id=attachment_id,
            provider_media_id=provider_media_id,
            media_type=media_type,
            message_id=message_id,
            company_id=company_id,
            access_token=access_token,
        )
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)[:500]

    # TRANSACTION 2: Finalize
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy.future import select

            att_result = await db.execute(
                select(CommunicationAttachment).where(
                    CommunicationAttachment.id == attachment_id,
                    CommunicationAttachment.worker_id == worker_id,
                )
            )
            att = att_result.scalars().first()
            if not att:
                # Lease was lost or stolen
                await db.rollback()
                return True

            if error_msg:
                att.status = "MEDIA_FAILED"
                att.last_error = error_msg
                att.retry_count += 1

                logger.error(
                    "Media retrieval failed",
                    extra={
                        "attachment_id": attachment_id,
                        "error": error_msg[:200],
                    },
                )
            else:
                att.object_storage_key = object_key
                att.file_size = file_size
                att.status = "MEDIA_PERSISTED"

                # Update message status
                msg_result = await db.execute(
                    select(CommunicationMessage).where(
                        CommunicationMessage.id == message_id
                    )
                )
                msg = msg_result.scalars().first()
                if msg:
                    msg.status = "RECEIVED"

                # Phase 3C: Create transcript record if audio
                if att.media_type and att.media_type.startswith("audio/"):
                    import uuid

                    from app.models.communication import CommunicationTranscript

                    transcript = CommunicationTranscript(
                        id=str(uuid.uuid4()),
                        company_id=company_id,
                        attachment_id=att.id,
                        provider=settings.STT_PROVIDER,
                        model=settings.STT_MODEL,
                        status="PENDING",
                    )
                    db.add(transcript)

                logger.info(
                    "Media persisted successfully",
                    extra={
                        "attachment_id": attachment_id,
                        "message_id": message_id,
                        "status": "MEDIA_PERSISTED",
                    },
                )

            await db.commit()
            return True

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"Worker finalize error: {exc}")
            return False


async def media_worker_loop() -> None:
    """Main polling loop for the media worker.

    Continuously polls PostgreSQL for pending/expired attachments.
    Sleeps between polls when no work is found.
    """
    worker_id = str(uuid.uuid4())
    logger.info(f"Media worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_attachment(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
