import os
import uuid
import wave

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.future import select

from app.core.config import settings
from app.infrastructure.database.session import AsyncSessionLocal
from app.infrastructure.storage.s3_storage import storage_client
from app.models.communication import (
    CommunicationAttachment,
    CommunicationMessage,
    CommunicationTranscript,
    ExtractedEventCandidate,
)
from app.models.manufacturing_event import ManufacturingEventRevision
from tests.test_webhooks import setup_integration


def create_dummy_wav(path: str, duration_seconds: int = 1):
    """Create a dummy WAV file for validation tests."""
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(b"\x00" * 44100 * 2 * duration_seconds)


@pytest_asyncio.fixture(autouse=True)
async def clear_transcripts(event_loop):
    async with AsyncSessionLocal() as db:
        from app.models.impact import ImpactDecisionHistory, ProductionOrderImpact
        from app.models.manufacturing_event import (
            CanonicalizationJob,
            ManufacturingEvent,
        )
        from app.models.resolution import EntityResolutionResult
        from app.models.risk import WorkOrderRiskHistory

        await db.execute(delete(WorkOrderRiskHistory))
        await db.execute(delete(ImpactDecisionHistory))
        await db.execute(delete(ProductionOrderImpact))
        await db.execute(delete(ManufacturingEventRevision))
        await db.execute(delete(ManufacturingEvent))
        await db.execute(delete(CanonicalizationJob))
        await db.execute(delete(EntityResolutionResult))
        await db.execute(delete(ExtractedEventCandidate))
        await db.execute(delete(CommunicationTranscript))
        await db.execute(delete(CommunicationAttachment))
        await db.commit()


@pytest.mark.asyncio
async def test_stt_worker_valid_audio(monkeypatch):
    """Test standard end-to-end processing with successful STT."""
    company_id = await setup_integration(
        company_name=f"STT Test {uuid.uuid4()}", phone_number_id=f"stt_{uuid.uuid4()}"
    )

    # 1. Create a dummy WAV file in MinIO
    wav_path = "dummy.wav"
    create_dummy_wav(wav_path, 2)
    with open(wav_path, "rb") as f:  # noqa: ASYNC230
        audio_bytes = f.read()
    os.remove(wav_path)

    msg_id = str(uuid.uuid4())
    object_key = f"{company_id}/evidence/{msg_id}/test.wav"
    await storage_client.upload(settings.MINIO_BUCKET, object_key, audio_bytes)

    # 2. Insert Attachment and Transcript
    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+111",
            status="RECEIVED",
        )
        db.add(msg)
        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="audio/wav",
            object_storage_key=object_key,
            file_size=len(audio_bytes),
            status="MEDIA_PERSISTED",
        )
        db.add(att)
        await db.flush()

        transcript = CommunicationTranscript(
            id=str(uuid.uuid4()),
            company_id=company_id,
            attachment_id=att.id,
            provider="openai",
            model="whisper-1",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    # 3. Mock Provider
    from app.core.interfaces import TranscriptResult

    async def mock_transcribe(*args, **kwargs):
        return TranscriptResult(
            transcript="Hello world",
            language="en",
            duration_seconds=2.0,
            provider_request_id="req-123",
        )

    from unittest.mock import MagicMock

    import app.workers.stt_worker as sw

    mock_provider = MagicMock()
    mock_provider.transcribe = mock_transcribe
    monkeypatch.setattr(sw, "_provider", mock_provider)

    # 4. Process
    result = await sw.process_one_transcript("worker-stt")
    assert result is True

    # 5. Verify
    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "COMPLETED", f"STT failed: {t.last_error}"
        assert t.provider_transcript == "Hello world"
        assert t.duration_seconds == 2.0


@pytest.mark.asyncio
async def test_stt_worker_no_speech(monkeypatch):
    """Test NO_SPEECH deterministic behavior when provider returns empty text."""
    company_id = await setup_integration(
        company_name=f"STT Test 2 {uuid.uuid4()}",
        phone_number_id=f"stt2_{uuid.uuid4()}",
    )

    wav_path = "dummy2.wav"
    create_dummy_wav(wav_path, 1)
    with open(wav_path, "rb") as f:  # noqa: ASYNC230
        audio_bytes = f.read()
    os.remove(wav_path)

    msg_id = str(uuid.uuid4())
    object_key = f"{company_id}/evidence/{msg_id}/test.wav"
    await storage_client.upload(settings.MINIO_BUCKET, object_key, audio_bytes)

    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+111",
            status="RECEIVED",
        )
        db.add(msg)
        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="audio/wav",
            object_storage_key=object_key,
            file_size=len(audio_bytes),
            status="MEDIA_PERSISTED",
        )
        db.add(att)
        await db.flush()

        transcript = CommunicationTranscript(
            id=str(uuid.uuid4()),
            company_id=company_id,
            attachment_id=att.id,
            provider="openai",
            model="whisper-1",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    from app.core.interfaces import TranscriptResult

    async def mock_transcribe(*args, **kwargs):
        return TranscriptResult(
            transcript="   ",  # EMPTY TEXT
            language="en",
            duration_seconds=1.0,
            provider_request_id="req-123",
        )

    from unittest.mock import MagicMock

    import app.workers.stt_worker as sw

    mock_provider = MagicMock()
    mock_provider.transcribe = mock_transcribe
    monkeypatch.setattr(sw, "_provider", mock_provider)

    await sw.process_one_transcript("worker-stt")

    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "NO_SPEECH"


@pytest.mark.asyncio
async def test_stt_worker_unsupported_codec():
    """Test validation rejection for unsupported container."""
    company_id = await setup_integration(
        company_name=f"STT Test 3 {uuid.uuid4()}",
        phone_number_id=f"stt3_{uuid.uuid4()}",
    )

    msg_id = str(uuid.uuid4())
    object_key = f"{company_id}/evidence/{msg_id}/test.jpg"
    await storage_client.upload(settings.MINIO_BUCKET, object_key, b"fake image bytes")

    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+111",
            status="RECEIVED",
        )
        db.add(msg)
        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="image/jpeg",  # UNSUPPORTED
            object_storage_key=object_key,
            file_size=16,
            status="MEDIA_PERSISTED",
        )
        db.add(att)
        await db.flush()

        transcript = CommunicationTranscript(
            id=str(uuid.uuid4()),
            company_id=company_id,
            attachment_id=att.id,
            provider="openai",
            model="whisper-1",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    import app.workers.stt_worker as sw

    await sw.process_one_transcript("worker-stt")

    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "FAILED"
        assert "Unsupported MIME type" in t.last_error


# ────────────────────────────────────────────────────────────────────
# MIME NORMALIZATION REGRESSION TESTS (WhatsApp OGG/Opus defect fix)
# ────────────────────────────────────────────────────────────────────


class TestNormalizeMimeType:
    """Unit tests for normalize_mime_type helper function."""

    def test_plain_audio_ogg(self):
        """Case A: audio/ogg without parameters → accepted as-is."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/ogg") == "audio/ogg"

    def test_ogg_with_codecs_opus(self):
        """Case B: audio/ogg; codecs=opus → normalized to audio/ogg."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/ogg; codecs=opus") == "audio/ogg"

    def test_ogg_no_space_codecs(self):
        """Case C: audio/ogg;codecs=opus (no space) → normalized to audio/ogg."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/ogg;codecs=opus") == "audio/ogg"

    def test_preserves_unsupported_types(self):
        """Case D: Unsupported MIME types are returned normalized but remain unsupported."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/mp3") == "audio/mp3"
        assert normalize_mime_type("application/octet-stream") == "application/octet-stream"

    def test_case_insensitive(self):
        """MIME types are case-insensitive per RFC 2045."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("Audio/OGG; Codecs=opus") == "audio/ogg"

    def test_empty_string(self):
        """Edge case: empty string → empty string (rejected downstream by allowlist)."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("") == ""

    def test_multiple_params(self):
        """Multiple MIME parameters → only base type extracted."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/ogg; codecs=opus; rate=44100") == "audio/ogg"

    def test_other_allowed_formats(self):
        """All other allowed formats normalize correctly."""
        from app.workers.stt_worker import normalize_mime_type

        assert normalize_mime_type("audio/mp4") == "audio/mp4"
        assert normalize_mime_type("audio/aac") == "audio/aac"
        assert normalize_mime_type("audio/wav") == "audio/wav"
        assert normalize_mime_type("audio/amr") == "audio/amr"
        assert normalize_mime_type("audio/mpeg") == "audio/mpeg"


@pytest.mark.asyncio
async def test_validate_audio_ogg_with_codecs_accepted():
    """Case B integration: audio/ogg; codecs=opus passes MIME validation
    and proceeds into the audio container validation stage (mutagen).

    We create a real WAV file labeled as audio/ogg to isolate the MIME
    check from actual container parsing — the test proves MIME validation
    no longer rejects the file.  Mutagen will raise because the container
    doesn't match, but that is a *different* error than "Unsupported MIME type".
    """
    import tempfile

    from app.infrastructure.stt.exceptions import STTPermanentError
    from app.workers.stt_worker import validate_audio

    # Create a minimal file to pass the empty/size checks
    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)  # Dummy bytes — will fail mutagen, not MIME

        try:
            await validate_audio(path, "audio/ogg; codecs=opus", 100)
            # If mutagen happens to accept it, that's fine too
        except STTPermanentError as e:
            error_msg = str(e)
            # Must NOT be a MIME rejection — must be a container/duration error
            assert "Unsupported MIME type" not in error_msg, (
                f"MIME normalization failed: {error_msg}"
            )
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_validate_audio_plain_ogg_accepted():
    """Case A integration: plain audio/ogg passes MIME validation."""
    import tempfile

    from app.infrastructure.stt.exceptions import STTPermanentError
    from app.workers.stt_worker import validate_audio

    fd, path = tempfile.mkstemp(suffix=".ogg")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)

        try:
            await validate_audio(path, "audio/ogg", 100)
        except STTPermanentError as e:
            assert "Unsupported MIME type" not in str(e)
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_validate_audio_unsupported_rejected():
    """Case D integration: unsupported MIME types are rejected with the correct error."""
    import tempfile

    from app.infrastructure.stt.exceptions import STTPermanentError
    from app.workers.stt_worker import validate_audio

    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)

        with pytest.raises(STTPermanentError, match="Unsupported MIME type"):
            await validate_audio(path, "application/octet-stream", 100)

        with pytest.raises(STTPermanentError, match="Unsupported MIME type"):
            await validate_audio(path, "audio/mp3", 100)
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_validate_audio_malformed_mime_rejected():
    """Case E: Malformed/invalid MIME strings are rejected safely."""
    import tempfile

    from app.infrastructure.stt.exceptions import STTPermanentError
    from app.workers.stt_worker import validate_audio

    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)

        with pytest.raises(STTPermanentError, match="Unsupported MIME type"):
            await validate_audio(path, "not-a-mime", 100)

        with pytest.raises(STTPermanentError, match="Unsupported MIME type"):
            await validate_audio(path, "", 100)
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_raw_mime_preserved_in_error_message():
    """Case F: The original raw MIME (with parameters) is preserved in
    the error message when rejection *does* occur, maintaining audit trail."""
    import tempfile

    from app.infrastructure.stt.exceptions import STTPermanentError
    from app.workers.stt_worker import validate_audio

    fd, path = tempfile.mkstemp(suffix=".bin")
    os.close(fd)
    try:
        with open(path, "wb") as f:
            f.write(b"\x00" * 100)

        raw_mime = "video/mp4; codecs=h264"
        with pytest.raises(STTPermanentError) as exc_info:
            await validate_audio(path, raw_mime, 100)

        # The error message must contain the ORIGINAL raw MIME, not the normalized one
        assert raw_mime in str(exc_info.value)
    finally:
        if os.path.exists(path):
            os.remove(path)


@pytest.mark.asyncio
async def test_stt_worker_whatsapp_ogg_opus_e2e(monkeypatch):
    """Full worker integration: audio/ogg; codecs=opus attachment is
    claimed, validated, sent to STT provider, and completed."""
    company_id = await setup_integration(
        company_name=f"STT MIME Test {uuid.uuid4()}",
        phone_number_id=f"stt_mime_{uuid.uuid4()}",
    )

    # Create a real WAV file (mutagen can parse it) but label it audio/ogg; codecs=opus
    wav_path = "dummy_mime.wav"
    create_dummy_wav(wav_path, 1)
    with open(wav_path, "rb") as f:
        audio_bytes = f.read()
    os.remove(wav_path)

    msg_id = str(uuid.uuid4())
    object_key = f"{company_id}/evidence/{msg_id}/voice.ogg"
    await storage_client.upload(settings.MINIO_BUCKET, object_key, audio_bytes)

    async with AsyncSessionLocal() as db:
        msg = CommunicationMessage(
            id=msg_id,
            company_id=company_id,
            source_channel="WHATSAPP",
            external_message_id=f"ext_{msg_id}",
            sender_identity="+111",
            status="RECEIVED",
        )
        db.add(msg)
        att = CommunicationAttachment(
            id=str(uuid.uuid4()),
            message_id=msg_id,
            media_type="audio/ogg; codecs=opus",  # Exact WhatsApp MIME
            object_storage_key=object_key,
            file_size=len(audio_bytes),
            status="MEDIA_PERSISTED",
        )
        db.add(att)
        await db.flush()

        transcript = CommunicationTranscript(
            id=str(uuid.uuid4()),
            company_id=company_id,
            attachment_id=att.id,
            provider="openai",
            model="whisper-1",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    # Mock STT provider
    from app.core.interfaces import TranscriptResult

    async def mock_transcribe(*args, **kwargs):
        return TranscriptResult(
            transcript="CNC 2 band ho gayi hai",
            language="hi",
            duration_seconds=3.0,
            provider_request_id="req-ogg-opus",
        )

    from unittest.mock import MagicMock

    import app.workers.stt_worker as sw

    mock_provider = MagicMock()
    mock_provider.transcribe = mock_transcribe
    monkeypatch.setattr(sw, "_provider", mock_provider)

    result = await sw.process_one_transcript("worker-mime-test")
    assert result is True

    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "COMPLETED", f"STT failed with MIME fix: {t.last_error}"
        assert t.provider_transcript == "CNC 2 band ho gayi hai"
