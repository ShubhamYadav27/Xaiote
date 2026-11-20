"""Phase 3C: PostgreSQL-backed durable Speech-to-Text worker.

This module implements a polling/claim mechanism for STT processing.
FastAPI BackgroundTasks, Redis, and Celery are explicitly excluded.

Processing loop:
1. SELECT transcript WHERE status = 'PENDING' OR (status = 'PROCESSING' AND lease_until < NOW()) FOR UPDATE SKIP LOCKED
2. Transition to PROCESSING, set lease_until, set worker_id
3. COMMIT claim transaction
4. Stream audio from MinIO into a bounded temp file
5. Validate MIME, size, and duration using mutagen
6. Stream AudioInput to STT Provider
7. Finalize transaction: Verify worker_id match, Transition to COMPLETED, NO_SPEECH, NEEDS_REVIEW, or FAILED
"""

import asyncio
import datetime
import logging
import os
import tempfile
import time
import uuid
from collections.abc import AsyncGenerator

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.interfaces import AudioInput
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.storage.s3_storage import storage_client
from app.infrastructure.stt import get_stt_provider
from app.infrastructure.stt.exceptions import (
    STTPermanentError,
    STTTransientError,
    STTUnsupportedDurationError,
)
from app.models.communication import CommunicationAttachment, CommunicationTranscript

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
POLL_INTERVAL_SECONDS = 5
LEASE_DURATION_SECONDS = 300  # 5 minutes for STT
MAX_AUDIO_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_AUDIO_DURATION_SECONDS = 900.0  # 15 minutes
ALLOWED_AUDIO_FORMATS = [
    "audio/ogg",
    "audio/mp4",
    "audio/aac",
    "audio/wav",
    "audio/amr",
    "audio/mpeg",
]
_provider = None


def _get_provider():
    """Lazy-initialize the STT provider singleton.

    This avoids failing at module import when SARVAM_API_KEY is not yet
    configured (e.g., during test collection before monkeypatching).
    """
    global _provider
    if _provider is None:
        _provider = get_stt_provider()
    return _provider


async def claim_pending_transcript(
    db: AsyncSession, worker_id: str
) -> CommunicationTranscript | None:
    now = datetime.datetime.now(datetime.timezone.utc)
    lease_until = now + datetime.timedelta(seconds=LEASE_DURATION_SECONDS)

    result = await db.execute(
        text(
            "SELECT id FROM communication_transcripts "
            "WHERE (status = 'PENDING' OR (status = 'PROCESSING' AND lease_until < :now)) "
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

    transcript_id = row[0]

    await db.execute(
        update(CommunicationTranscript)
        .where(CommunicationTranscript.id == transcript_id)
        .values(status="PROCESSING", lease_until=lease_until, worker_id=worker_id)
    )
    await db.flush()

    from sqlalchemy.future import select

    result = await db.execute(
        select(CommunicationTranscript).where(
            CommunicationTranscript.id == transcript_id
        )
    )
    return result.scalars().first()


def normalize_mime_type(raw_mime: str) -> str:
    """Extract the base MIME type, stripping any parameters.

    RFC 2045 MIME types may include parameters separated by semicolons, e.g.
    ``audio/ogg; codecs=opus``.  WhatsApp consistently sends voice notes with
    the ``codecs=opus`` parameter.  We normalize to the base type for allowlist
    validation while the original ``raw_mime`` is preserved elsewhere for
    evidence/audit purposes.

    Returns the lowercased base MIME type (e.g. ``audio/ogg``), or the
    original string stripped and lowercased if no semicolon is present.
    """
    base = raw_mime.split(";", 1)[0].strip().lower()
    return base


async def validate_audio(file_path: str, declared_mime: str, file_size: int) -> float:
    """Validate audio constraints before sending to provider.

    Returns duration in seconds. Raises STTPermanentError on validation failure.
    """
    if file_size > MAX_AUDIO_BYTES:
        raise STTPermanentError(
            f"File size {file_size} exceeds maximum {MAX_AUDIO_BYTES}"
        )
    if file_size == 0:
        raise STTPermanentError("Empty audio file")
    normalized_mime = normalize_mime_type(declared_mime)
    if normalized_mime not in ALLOWED_AUDIO_FORMATS:
        raise STTPermanentError(f"Unsupported MIME type: {declared_mime}")

    try:
        import mutagen

        audio = mutagen.File(file_path)
        if audio is None or not hasattr(audio.info, "length"):
            raise STTPermanentError("Malformed audio container or unknown duration")

        duration = float(audio.info.length)
        if duration <= 0:
            raise STTPermanentError("Invalid zero or negative duration")
        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise STTPermanentError(
                f"Duration {duration} exceeds maximum {MAX_AUDIO_DURATION_SECONDS}"
            )

        return duration
    except Exception as e:
        if isinstance(e, STTPermanentError):
            raise
        raise STTPermanentError(f"Validation failed: {e!s}")


async def stream_file(
    file_path: str, chunk_size: int = 65536
) -> AsyncGenerator[bytes, None]:
    """Yield file chunks."""
    # Using thread pool implicitly via asyncio is better, but MVP:
    # Aiofiles would be better, but we can't install too many packages.
    # Using standard blocking I/O for reading local temp file is usually fine.
    # We will simulate async read.
    with open(file_path, "rb") as f:  # noqa: ASYNC230
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


async def process_one_transcript(worker_id: str) -> bool:
    transcript_id = None
    attachment_id = None

    # TRANSACTION 1: Claim
    async with AsyncSessionLocal() as db:
        try:
            transcript = await claim_pending_transcript(db, worker_id)
            if not transcript:
                await db.rollback()
                return False

            transcript_id = transcript.id
            attachment_id = transcript.attachment_id

            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"STT Worker claim error: {exc}")
            return False

    # NETWORK IO / PROCESSING
    error_msg = None
    is_transient = False
    is_unsupported_duration = False
    result = None
    stt_start_time = time.monotonic()

    try:
        # Retrieve Attachment Details
        async with AsyncSessionLocal() as db:
            from sqlalchemy.future import select

            att_result = await db.execute(
                select(CommunicationAttachment).where(
                    CommunicationAttachment.id == attachment_id
                )
            )
            att = att_result.scalars().first()
            if not att or not att.object_storage_key:
                raise STTPermanentError("Attachment or object storage key missing")
            object_key = att.object_storage_key
            mime_type = att.media_type
            file_size = att.file_size or 0

        # Download to bounded temp file
        temp_fd, temp_path = tempfile.mkstemp(suffix=".audio")
        os.close(temp_fd)
        try:
            # We don't have a streaming download in S3Storage interface currently,
            # so download() returns bytes. We must handle this safely.
            audio_bytes = await storage_client.download(
                settings.MINIO_BUCKET, object_key
            )
            if len(audio_bytes) > MAX_AUDIO_BYTES:
                raise STTPermanentError("Storage object exceeds limits")

            with open(temp_path, "wb") as f:  # noqa: ASYNC230
                f.write(audio_bytes)

            # Free memory
            del audio_bytes

            # Validate
            duration = await validate_audio(temp_path, mime_type, file_size)

            # STT
            audio_input = AudioInput(
                stream=stream_file(temp_path),
                content_type=mime_type,
                filename="audio.bin",
                size_bytes=file_size,
                duration_seconds=duration,
            )

            result = await _get_provider().transcribe(audio_input, {})

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except STTUnsupportedDurationError as exc:
        error_msg = str(exc)[:500]
        is_unsupported_duration = True
    except STTTransientError as exc:
        error_msg = str(exc)[:500]
        is_transient = True
    except STTPermanentError as exc:
        error_msg = str(exc)[:500]
        is_transient = False
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)[:500]
        # Unknown errors (like network timeout downloading from minio) are transient
        is_transient = True

    stt_latency_ms = int((time.monotonic() - stt_start_time) * 1000)

    # TRANSACTION 2: Finalize
    async with AsyncSessionLocal() as db:
        try:
            from sqlalchemy.future import select

            t_result = await db.execute(
                select(CommunicationTranscript).where(
                    CommunicationTranscript.id == transcript_id,
                    CommunicationTranscript.worker_id == worker_id,
                )
            )
            t = t_result.scalars().first()
            if not t:
                # Lease lost
                await db.rollback()
                return True

            if is_unsupported_duration:
                # >30s audio: NEEDS_REVIEW, do NOT increment retry_count
                t.status = "NEEDS_REVIEW"
                t.last_error = error_msg
                logger.warning(
                    "STT unsupported duration",
                    extra={
                        "transcript_id": transcript_id,
                        "stt_provider": settings.STT_PROVIDER,
                        "stt_model": settings.STT_MODEL,
                        "stt_status": "NEEDS_REVIEW",
                        "stt_reason": "UNSUPPORTED_DURATION",
                        "stt_latency_ms": stt_latency_ms,
                    },
                )
            elif error_msg:
                t.retry_count += 1
                t.last_error = error_msg

                if is_transient and t.retry_count < MAX_RETRIES:
                    t.status = "PENDING"
                else:
                    t.status = "FAILED"

                logger.error(
                    "STT processing failed",
                    extra={
                        "transcript_id": transcript_id,
                        "error": error_msg[:200],
                        "stt_provider": settings.STT_PROVIDER,
                        "stt_model": settings.STT_MODEL,
                        "stt_status": t.status,
                        "stt_latency_ms": stt_latency_ms,
                        "stt_is_transient": is_transient,
                    },
                )
            else:
                t.provider_transcript = result.transcript
                t.confidence = result.confidence
                t.language = result.language
                t.duration_seconds = result.duration_seconds
                t.provider_request_id = result.provider_request_id

                if not result.transcript or not result.transcript.strip():
                    t.status = "NO_SPEECH"
                else:
                    t.status = "COMPLETED"
                    # Phase 3D Handoff: Create PENDING ExtractedEventCandidate
                    from sqlalchemy.dialects.postgresql import insert

                    from app.models.communication import ExtractedEventCandidate

                    stmt = (
                        insert(ExtractedEventCandidate)
                        .values(
                            id=str(uuid.uuid4()),
                            company_id=t.company_id,
                            transcript_id=t.id,
                            processing_status="PENDING",
                        )
                        .on_conflict_do_nothing(index_elements=["transcript_id"])
                    )
                    await db.execute(stmt)

                logger.info(
                    "STT processing successful",
                    extra={
                        "transcript_id": transcript_id,
                        "stt_provider": settings.STT_PROVIDER,
                        "stt_model": settings.STT_MODEL,
                        "stt_status": t.status,
                        "stt_latency_ms": stt_latency_ms,
                    },
                )

            await db.commit()
            return True

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"STT Worker finalize error: {exc}")
            return False


async def stt_worker_loop() -> None:
    worker_id = str(uuid.uuid4())
    logger.info(f"STT worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_transcript(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"STT Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
