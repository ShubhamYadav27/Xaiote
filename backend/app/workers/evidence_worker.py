import asyncio
import logging
import uuid
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.infrastructure.database.session import AsyncSessionLocal
from app.models.communication import (
    CommunicationMessage,
    CommunicationAttachment,
    CommunicationTranscript,
    ExtractedEventCandidate,
)

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 5.0

async def process_one_message(worker_id: str) -> bool:
    async with AsyncSessionLocal() as db:
        try:
            # 1. Claim a RECEIVED message
            msg_result = await db.execute(
                text(
                    "SELECT id FROM communication_messages "
                    "WHERE status = 'RECEIVED' "
                    "FOR UPDATE SKIP LOCKED LIMIT 1"
                )
            )
            row = msg_result.fetchone()
            if not row:
                await db.rollback()
                return False
                
            msg_id = row[0]
            
            # Fetch full object
            msg_obj_res = await db.execute(
                select(CommunicationMessage).where(CommunicationMessage.id == msg_id)
            )
            msg = msg_obj_res.scalars().first()
            if not msg:
                await db.rollback()
                return False
                
            company_id = msg.company_id
            payload_str = msg.raw_payload
            source = msg.source_channel
            
            if not payload_str:
                msg.status = "EVIDENCE_PERSISTED"
                await db.commit()
                return True
                
            payload = json.loads(payload_str)
            
            # Parse based on channel (currently WhatsApp is primary)
            if source == "WHATSAPP":
                try:
                    entry = payload.get("entry", [])[0]
                    changes = entry.get("changes", [])[0]
                    value = changes.get("value", {})
                    messages = value.get("messages", [])
                    if not messages:
                        msg.status = "EVIDENCE_PERSISTED"
                        await db.commit()
                        return True
                        
                    wmsg = messages[0]
                    message_type = wmsg.get("type", "text")
                    
                    MAX_MEDIA_TYPES = {"image", "video", "audio", "document"}
                    has_media = message_type in MAX_MEDIA_TYPES
                    
                    if has_media:
                        media_data = wmsg.get(message_type, {})
                        provider_media_id = media_data.get("id", "")
                        mime_type = media_data.get("mime_type", "application/octet-stream")
                        
                        if provider_media_id:
                            attachment = CommunicationAttachment(
                                id=str(uuid.uuid4()),
                                message_id=msg.id,
                                media_type=mime_type,
                                status="MEDIA_PENDING",
                                provider_media_id=provider_media_id,
                            )
                            db.add(attachment)
                    else:
                        text_body = wmsg.get("text", {}).get("body", "")
                        if text_body:
                            attachment = CommunicationAttachment(
                                id=str(uuid.uuid4()),
                                message_id=msg.id,
                                media_type="text/plain",
                                status="MEDIA_PERSISTED",
                                file_size=len(text_body)
                            )
                            db.add(attachment)
                            
                            transcript = CommunicationTranscript(
                                id=str(uuid.uuid4()),
                                company_id=company_id,
                                attachment_id=attachment.id,
                                provider="META_WHATSAPP_TEXT",
                                model="DIRECT",
                                language="en",
                                status="COMPLETED",
                                provider_transcript=text_body,
                                corrected_transcript=text_body
                            )
                            db.add(transcript)
                            
                            candidate = ExtractedEventCandidate(
                                id=str(uuid.uuid4()),
                                company_id=company_id,
                                transcript_id=transcript.id,
                                processing_status="PENDING"
                            )
                            db.add(candidate)
                            
                except Exception as e:
                    logger.error(f"Error parsing WHATSAPP payload: {e}")
            
            # 2. Mark as processed
            msg.status = "EVIDENCE_PERSISTED"
            await db.commit()
            return True
            
        except Exception as exc:
            await db.rollback()
            logger.error(f"Evidence Worker claim error: {exc}")
            return False

async def evidence_worker_loop() -> None:
    worker_id = str(uuid.uuid4())
    logger.info(f"Evidence worker started with id: {worker_id}")
    while True:
        try:
            found_work = await process_one_message(worker_id)
            if not found_work:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("Evidence worker cancelled")
            break
        except Exception as exc:
            logger.error(f"Evidence Worker loop error: {exc}")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

