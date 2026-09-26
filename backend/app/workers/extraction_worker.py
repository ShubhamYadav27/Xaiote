"""Phase 3D: LLM Extraction Worker."""

import asyncio
import datetime
import logging
import uuid

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.interfaces import ExtractionMetadata
from app.core.prompts import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SYSTEM_PROMPT,
    get_prompt_hash,
    get_schema_hash,
)
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.llm.exceptions import (
    LLMPermanentException,
    LLMRequiresReviewException,
    LLMRetryableException,
)
from app.infrastructure.llm.openai_provider import OpenAIProvider
from app.models.communication import CommunicationTranscript, ExtractedEventCandidate
from app.schemas.extraction import ExtractionEventSchema

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
POLL_INTERVAL_SECONDS = 5
LEASE_DURATION_SECONDS = 120
MAX_TRANSCRIPT_CHARS = 10000

provider = OpenAIProvider()


async def claim_pending_candidate(
    db: AsyncSession, worker_id: str
) -> ExtractedEventCandidate | None:
    now = datetime.datetime.now(datetime.timezone.utc)
    lease_until = now + datetime.timedelta(seconds=LEASE_DURATION_SECONDS)

    result = await db.execute(
        text(
            "SELECT id FROM extracted_event_candidates "
            "WHERE (processing_status = 'PENDING' OR (processing_status = 'PROCESSING' AND lease_until < :now)) "
            "AND attempt_count < :max_attempts "
            "ORDER BY created_at ASC "
            "LIMIT 1 "
            "FOR UPDATE SKIP LOCKED"
        ),
        {"now": now, "max_attempts": MAX_ATTEMPTS},
    )
    row = result.first()
    if not row:
        return None

    candidate_id = row[0]

    await db.execute(
        update(ExtractedEventCandidate)
        .where(ExtractedEventCandidate.id == candidate_id)
        .values(
            processing_status="PROCESSING", lease_until=lease_until, worker_id=worker_id
        )
    )
    await db.flush()

    res = await db.execute(
        select(ExtractedEventCandidate).where(
            ExtractedEventCandidate.id == candidate_id
        )
    )
    return res.scalars().first()


async def process_one_candidate(worker_id: str) -> bool:
    candidate_id = None
    transcript_id = None
    transcript_text = None

    # TRANSACTION 1: Claim
    async with AsyncSessionLocal() as db:
        try:
            candidate = await claim_pending_candidate(db, worker_id)
            if not candidate:
                await db.rollback()
                return False

            candidate_id = candidate.id
            transcript_id = candidate.transcript_id

            # Get the transcript
            t_res = await db.execute(
                select(CommunicationTranscript).where(
                    CommunicationTranscript.id == transcript_id
                )
            )
            transcript = t_res.scalars().first()
            if not transcript or not transcript.provider_transcript:
                # Should not happen, but if it does:
                transcript_text = ""
            else:
                transcript_text = transcript.provider_transcript

            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"Extraction Worker claim error: {exc}")
            return False

    # Validation: Oversized Input
    if len(transcript_text) > MAX_TRANSCRIPT_CHARS:
        async with AsyncSessionLocal() as db:
            try:
                res = await db.execute(
                    select(ExtractedEventCandidate).where(
                        ExtractedEventCandidate.id == candidate_id,
                        ExtractedEventCandidate.worker_id == worker_id,
                    )
                )
                c = res.scalars().first()
                if c:
                    c.processing_status = "NEEDS_REVIEW"
                    c.last_error = "OVERSIZED_INPUT"
                    await db.commit()
            except Exception:  # noqa: BLE001
                await db.rollback()
        return True

    # NETWORK IO / PROCESSING
    error_msg = None
    failure_type = None  # "RETRYABLE", "PERMANENT", "REQUIRES_REVIEW"
    result = None

    schema_dict = ExtractionEventSchema.model_json_schema()
    schema_hash = get_schema_hash(schema_dict)
    prompt_hash = get_prompt_hash()

    metadata = ExtractionMetadata(
        transcript_id=transcript_id,
        attempt_count=0,  # In a real system, fetch real count, but LLM abstraction just passes it
    )

    # Needs real attempt count for metadata
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(ExtractedEventCandidate).where(
                ExtractedEventCandidate.id == candidate_id
            )
        )
        c_temp = res.scalars().first()
        if c_temp:
            metadata.attempt_count = c_temp.attempt_count + 1

    try:
        result = await provider.extract_event(
            transcript_text=transcript_text,
            schema=schema_dict,
            prompt_instructions=SYSTEM_PROMPT,
            metadata=metadata,
        )
    except LLMRetryableException as exc:
        error_msg = str(exc)[:500]
        failure_type = "RETRYABLE"
    except LLMPermanentException as exc:
        error_msg = str(exc)[:500]
        failure_type = "PERMANENT"
    except LLMRequiresReviewException as exc:
        error_msg = str(exc)[:500]
        failure_type = "REQUIRES_REVIEW"
    except Exception as exc:  # noqa: BLE001
        error_msg = str(exc)[:500]
        failure_type = "RETRYABLE"

    # TRANSACTION 2: Finalize
    async with AsyncSessionLocal() as db:
        try:
            res = await db.execute(
                select(ExtractedEventCandidate).where(
                    ExtractedEventCandidate.id == candidate_id,
                    ExtractedEventCandidate.worker_id == worker_id,
                )
            )
            c = res.scalars().first()
            if not c:
                # Lease lost
                await db.rollback()
                return True

            c.attempt_count += 1
            c.provider = "openai"
            c.model = "gpt-4o-mini"
            c.prompt_version = PROMPT_VERSION
            c.prompt_hash = prompt_hash
            c.schema_version = SCHEMA_VERSION
            c.schema_hash = schema_hash

            if failure_type == "RETRYABLE":
                c.last_error = error_msg
                if c.attempt_count < MAX_ATTEMPTS:
                    c.processing_status = "PENDING"
                else:
                    c.processing_status = "FAILED"
            elif failure_type == "PERMANENT":
                c.last_error = error_msg
                c.processing_status = "FAILED"
            elif failure_type == "REQUIRES_REVIEW":
                c.last_error = error_msg
                c.processing_status = "NEEDS_REVIEW"
            else:
                c.payload = result.payload
                c.raw_llm_response = result.raw_response
                c.input_tokens = result.input_tokens
                c.output_tokens = result.output_tokens
                c.provider_request_id = result.provider_request_id
                c.processing_status = "COMPLETED"

                # Deterministic Validation
                try:
                    ExtractionEventSchema(**result.payload)
                    c.validation_status = "VALID"
                except Exception:  # noqa: BLE001
                    c.validation_status = "INVALID"

            await db.commit()
            return True

        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            logger.error(f"Extraction Worker finalize error: {exc}")
            return False


async def extraction_worker_loop() -> None:
    worker_id = str(uuid.uuid4())
    logger.info(f"Extraction worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_candidate(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Extraction Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
