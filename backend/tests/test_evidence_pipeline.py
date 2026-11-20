import pytest
import uuid
import json
from sqlalchemy.future import select

from app.models.company import Company
from app.models.communication import CommunicationMessage, CommunicationAttachment, CommunicationTranscript, ExtractedEventCandidate
from app.workers.evidence_worker import process_one_message

@pytest.fixture
async def base_data(db_session):
    c1 = Company(id="c1", name="C1")
    db_session.add(c1)
    await db_session.commit()
    return c1

@pytest.mark.asyncio
async def test_evidence_worker_text(db_session, base_data):
    c1 = base_data
    msg_id = str(uuid.uuid4())
    payload = {
        "entry": [{"changes": [{"value": {"messages": [{"type": "text", "text": {"body": "Test text message"}}]}}]}]
    }
    msg = CommunicationMessage(
        id=msg_id,
        company_id=c1.id,
        source_channel="WHATSAPP",
        external_message_id=str(uuid.uuid4()),
        sender_identity="123",
        raw_payload=json.dumps(payload),
        status="RECEIVED"
    )
    db_session.add(msg)
    await db_session.commit()

    # Run worker
    worker_id = "test-worker"
    found = await process_one_message(worker_id)
    assert found is True

    # Verify
    await db_session.refresh(msg)
    assert msg.status == "EVIDENCE_PERSISTED"

    res = await db_session.execute(select(CommunicationAttachment).where(CommunicationAttachment.message_id == msg.id))
    att = res.scalars().first()
    assert att.media_type == "text/plain"
    assert att.status == "MEDIA_PERSISTED"

    res = await db_session.execute(select(CommunicationTranscript).where(CommunicationTranscript.attachment_id == att.id))
    transcript = res.scalars().first()
    assert transcript.provider_transcript == "Test text message"
    assert transcript.status == "COMPLETED"

    res = await db_session.execute(select(ExtractedEventCandidate).where(ExtractedEventCandidate.transcript_id == transcript.id))
    candidate = res.scalars().first()
    assert candidate.processing_status == "PENDING"

@pytest.mark.asyncio
async def test_evidence_worker_audio(db_session, base_data):
    c1 = base_data
    msg_id = str(uuid.uuid4())
    payload = {
        "entry": [{"changes": [{"value": {"messages": [{"type": "audio", "audio": {"id": "audio123", "mime_type": "audio/ogg"}}]}}]}]
    }
    msg = CommunicationMessage(
        id=msg_id,
        company_id=c1.id,
        source_channel="WHATSAPP",
        external_message_id=str(uuid.uuid4()),
        sender_identity="123",
        raw_payload=json.dumps(payload),
        status="RECEIVED"
    )
    db_session.add(msg)
    await db_session.commit()

    found = await process_one_message("w1")
    assert found is True

    res = await db_session.execute(select(CommunicationAttachment).where(CommunicationAttachment.message_id == msg.id))
    att = res.scalars().first()
    assert att.media_type == "audio/ogg"
    assert att.status == "MEDIA_PENDING"
    assert att.provider_media_id == "audio123"

    res = await db_session.execute(select(CommunicationTranscript).where(CommunicationTranscript.attachment_id == att.id))
    transcript = res.scalars().first()
    assert transcript is None # STT handles audio
