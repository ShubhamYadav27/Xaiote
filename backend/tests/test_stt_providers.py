"""Comprehensive STT provider tests.

All tests use mocks — zero real Sarvam/OpenAI API calls, zero credit consumption.

Test matrix:
1.  Provider factory selects Sarvam when STT_PROVIDER=sarvam
2.  Provider factory selects OpenAI when STT_PROVIDER=openai
3.  Provider factory raises on unknown provider
4.  Sarvam provider init fails without API key
5.  Sarvam provider init succeeds with key
6.  Sarvam successful transcription
7.  Sarvam 400 error → STTPermanentError
8.  Sarvam 403 error → STTPermanentError
9.  Sarvam 429 error → STTTransientError
10. Sarvam 503 error → STTTransientError
11. Sarvam network timeout → STTTransientError
12. Sarvam malformed response → handled
13. Duration >30s → STTUnsupportedDurationError
14. Duration >30s → NEEDS_REVIEW in worker (no retry increment)
15. OpenAI provider still works
16. No API key in log output
17. Original audio preserved after failure
"""

import logging
import os
import uuid
import wave
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import delete
from sqlalchemy.future import select

from app.core.interfaces import AudioInput, TranscriptResult
from app.infrastructure.stt.exceptions import (
    STTPermanentError,
    STTTransientError,
    STTUnsupportedDurationError,
)

# ============================================================
# Helpers
# ============================================================


async def _make_audio_stream(data: bytes):
    """Create an async generator from bytes."""
    yield data


def _make_audio_input(duration: float = 5.0, size: int = 1000):
    """Create a mock AudioInput."""
    return AudioInput(
        stream=_make_audio_stream(b"\x00" * size),
        content_type="audio/wav",
        filename="test.wav",
        size_bytes=size,
        duration_seconds=duration,
    )


def create_dummy_wav(path: str, duration_seconds: int = 1):
    """Create a dummy WAV file for validation tests."""
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(44100)
        f.writeframes(b"\x00" * 44100 * 2 * duration_seconds)


# ============================================================
# 1. Provider factory: sarvam
# ============================================================
def test_factory_selects_sarvam(monkeypatch):
    """STT_PROVIDER=sarvam should instantiate SarvamProvider."""
    monkeypatch.setattr("app.core.config.settings.STT_PROVIDER", "sarvam")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")

    from app.infrastructure.stt import get_stt_provider
    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = get_stt_provider()
    assert isinstance(provider, SarvamProvider)


# ============================================================
# 2. Provider factory: openai
# ============================================================
def test_factory_selects_openai(monkeypatch):
    """STT_PROVIDER=openai should instantiate WhisperProvider."""
    monkeypatch.setattr("app.core.config.settings.STT_PROVIDER", "openai")

    from app.infrastructure.stt import get_stt_provider
    from app.infrastructure.stt.whisper_provider import WhisperProvider

    provider = get_stt_provider()
    assert isinstance(provider, WhisperProvider)


# ============================================================
# 3. Provider factory: unknown
# ============================================================
def test_factory_unknown_provider(monkeypatch):
    """Unknown STT_PROVIDER should raise ValueError."""
    monkeypatch.setattr("app.core.config.settings.STT_PROVIDER", "deepgram")

    from app.infrastructure.stt import get_stt_provider

    with pytest.raises(ValueError, match="Unknown STT_PROVIDER"):
        get_stt_provider()


# ============================================================
# 4. Sarvam init: missing key
# ============================================================
def test_sarvam_init_missing_key(monkeypatch):
    """SarvamProvider must fail clearly when SARVAM_API_KEY is empty."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    with pytest.raises(STTPermanentError, match="SARVAM_API_KEY is not configured"):
        SarvamProvider()


# ============================================================
# 5. Sarvam init: success
# ============================================================
def test_sarvam_init_success(monkeypatch):
    """SarvamProvider initializes with a valid key."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    assert provider.model == "saaras:v4"
    assert provider.client is not None


# ============================================================
# 6. Sarvam successful transcription
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_transcription_success(monkeypatch):
    """Successful Sarvam transcription returns TranscriptResult."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()

    # Mock the SDK response
    mock_response = MagicMock()
    mock_response.transcript = "CNC-02 spindle broken, work order WO-1045"
    mock_response.language_code = "en-IN"
    mock_response.request_id = "req-sarvam-123"

    provider.client.speech_to_text.transcribe = MagicMock(return_value=mock_response)

    audio_input = _make_audio_input(duration=10.0)
    result = await provider.transcribe(audio_input, {})

    assert isinstance(result, TranscriptResult)
    assert result.transcript == "CNC-02 spindle broken, work order WO-1045"
    assert result.language == "en-IN"
    assert result.provider_request_id == "req-sarvam-123"
    assert result.duration_seconds == 10.0


# ============================================================
# 7. Sarvam 400 error → STTPermanentError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_400_error(monkeypatch):
    """Sarvam 400 (bad request) maps to STTPermanentError."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from sarvamai.core.api_error import ApiError

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    provider.client.speech_to_text.transcribe = MagicMock(
        side_effect=ApiError(status_code=400, body={"error": "Invalid audio format"})
    )

    audio_input = _make_audio_input()
    with pytest.raises(STTPermanentError, match="Sarvam request error 400"):
        await provider.transcribe(audio_input, {})


# ============================================================
# 8. Sarvam 403 error → STTPermanentError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_403_error(monkeypatch):
    """Sarvam 403 (auth failure) maps to STTPermanentError."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from sarvamai.core.api_error import ApiError

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    provider.client.speech_to_text.transcribe = MagicMock(
        side_effect=ApiError(status_code=403, body={"error": "Invalid API key"})
    )

    audio_input = _make_audio_input()
    with pytest.raises(STTPermanentError, match="Sarvam authentication error 403"):
        await provider.transcribe(audio_input, {})


# ============================================================
# 9. Sarvam 429 error → STTTransientError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_429_error(monkeypatch):
    """Sarvam 429 (rate limit) maps to STTTransientError."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from sarvamai.core.api_error import ApiError

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    provider.client.speech_to_text.transcribe = MagicMock(
        side_effect=ApiError(status_code=429, body={"error": "Rate limit exceeded"})
    )

    audio_input = _make_audio_input()
    with pytest.raises(STTTransientError, match="Sarvam rate limit 429"):
        await provider.transcribe(audio_input, {})


# ============================================================
# 10. Sarvam 503 error → STTTransientError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_503_error(monkeypatch):
    """Sarvam 503 (unavailable) maps to STTTransientError."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from sarvamai.core.api_error import ApiError

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    provider.client.speech_to_text.transcribe = MagicMock(
        side_effect=ApiError(status_code=503, body={"error": "Service unavailable"})
    )

    audio_input = _make_audio_input()
    with pytest.raises(STTTransientError, match="Sarvam server error 503"):
        await provider.transcribe(audio_input, {})


# ============================================================
# 11. Sarvam network timeout → STTTransientError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_timeout(monkeypatch):
    """Network timeout maps to STTTransientError."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    import httpx

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    provider.client.speech_to_text.transcribe = MagicMock(
        side_effect=httpx.ReadTimeout("Connection timed out")
    )

    audio_input = _make_audio_input()
    with pytest.raises(STTTransientError, match="Sarvam network error"):
        await provider.transcribe(audio_input, {})


# ============================================================
# 12. Sarvam malformed response
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_malformed_response(monkeypatch):
    """Malformed response (missing transcript attr) is handled."""
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()

    # Response without expected fields — getattr returns defaults
    mock_response = MagicMock(spec=[])  # No attributes
    mock_response.transcript = None
    mock_response.language_code = None
    mock_response.request_id = None

    provider.client.speech_to_text.transcribe = MagicMock(return_value=mock_response)

    audio_input = _make_audio_input()
    result = await provider.transcribe(audio_input, {})

    # Should return empty transcript, not crash
    assert result.transcript == ""


# ============================================================
# 13. Duration >30s → STTUnsupportedDurationError
# ============================================================
@pytest.mark.asyncio
async def test_sarvam_duration_guard():
    """Audio >30s raises STTUnsupportedDurationError before API call."""
    from unittest.mock import MagicMock

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    with patch("app.core.config.settings.SARVAM_API_KEY", "test-key-not-real"), patch(
        "app.core.config.settings.STT_MODEL", "saaras:v4"
    ):
        provider = SarvamProvider()

    # Mock to ensure API is NOT called
    provider.client.speech_to_text.transcribe = MagicMock()

    audio_input = _make_audio_input(duration=45.0)

    with pytest.raises(STTUnsupportedDurationError) as exc_info:
        await provider.transcribe(audio_input, {})

    assert exc_info.value.duration == 45.0
    assert exc_info.value.limit == 30.0
    assert exc_info.value.provider == "sarvam"
    assert "UNSUPPORTED_DURATION" in str(exc_info.value)

    # Verify API was NOT called
    provider.client.speech_to_text.transcribe.assert_not_called()


# ============================================================
# 14. >30s in worker → NEEDS_REVIEW, no retry increment
# ============================================================
@pytest.mark.asyncio
async def test_stt_worker_unsupported_duration(monkeypatch):
    """Worker marks >30s audio as NEEDS_REVIEW without retry increment."""
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

    # Cleanup
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

    company_id = await setup_integration(
        company_name=f"Duration Test {uuid.uuid4()}",
        phone_number_id=f"dur_{uuid.uuid4()}",
    )

    # Create a dummy WAV file (will pass validation but duration will be overridden)
    wav_path = "dummy_long.wav"
    create_dummy_wav(wav_path, 2)
    with open(wav_path, "rb") as f:
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
            provider="sarvam",
            model="saaras:v4",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    # Mock the provider to raise STTUnsupportedDurationError
    import app.workers.stt_worker as sw

    mock_provider = MagicMock()

    async def mock_transcribe_duration_error(audio_input, metadata):
        raise STTUnsupportedDurationError(duration=45.0, limit=30.0, provider="sarvam")

    mock_provider.transcribe = mock_transcribe_duration_error
    monkeypatch.setattr(sw, "_provider", mock_provider)

    result = await sw.process_one_transcript("worker-dur-test")
    assert result is True

    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "NEEDS_REVIEW", f"Expected NEEDS_REVIEW, got: {t.status}"
        assert "UNSUPPORTED_DURATION" in t.last_error
        assert t.retry_count == 0, "retry_count should NOT increment for duration guard"
        assert t.provider_transcript is None, "No fabricated transcript"

    # Verify original audio still in storage
    stored = await storage_client.download(settings.MINIO_BUCKET, object_key)
    assert stored == audio_bytes


# ============================================================
# 15. OpenAI provider regression
# ============================================================
def test_openai_provider_still_works(monkeypatch):
    """WhisperProvider still initializes correctly."""
    monkeypatch.setattr("app.core.config.settings.STT_API_KEY", "test-key")
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "whisper-1")

    from app.infrastructure.stt.whisper_provider import WhisperProvider

    provider = WhisperProvider()
    assert provider.model == "whisper-1"
    assert provider.api_key == "test-key"
    assert "openai.com" in provider.url


# ============================================================
# 16. No API key in logs
# ============================================================
@pytest.mark.asyncio
async def test_no_api_key_in_logs(monkeypatch, caplog):
    """Verify the Sarvam API key never appears in log output."""
    test_key = "sk_SUPERSECRET_test_key_12345"
    monkeypatch.setattr("app.core.config.settings.SARVAM_API_KEY", test_key)
    monkeypatch.setattr("app.core.config.settings.STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    with caplog.at_level(logging.DEBUG):
        provider = SarvamProvider()

        mock_response = MagicMock()
        mock_response.transcript = "test"
        mock_response.language_code = "en"
        mock_response.request_id = "req-123"
        provider.client.speech_to_text.transcribe = MagicMock(
            return_value=mock_response
        )

        audio_input = _make_audio_input()
        await provider.transcribe(audio_input, {})

    # Check no log record contains the key
    for record in caplog.records:
        assert (
            test_key not in record.getMessage()
        ), f"API key found in log: {record.getMessage()}"


# ============================================================
# 17. Audio preserved after STT failure
# ============================================================
@pytest.mark.asyncio
async def test_audio_preserved_after_failure(monkeypatch):
    """Original audio must remain in storage after STT failure."""
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

    # Cleanup
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

    company_id = await setup_integration(
        company_name=f"Preserve Test {uuid.uuid4()}",
        phone_number_id=f"preserve_{uuid.uuid4()}",
    )

    wav_path = "dummy_preserve.wav"
    create_dummy_wav(wav_path, 2)
    with open(wav_path, "rb") as f:
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
            provider="sarvam",
            model="saaras:v4",
            status="PENDING",
        )
        db.add(transcript)
        await db.commit()
        t_id = transcript.id

    # Mock provider to fail
    import app.workers.stt_worker as sw

    mock_provider = MagicMock()

    async def mock_fail(*args, **kwargs):
        raise STTPermanentError("Simulated provider failure")

    mock_provider.transcribe = mock_fail
    monkeypatch.setattr(sw, "_provider", mock_provider)

    await sw.process_one_transcript("worker-preserve-test")

    # Verify transcript is FAILED
    async with AsyncSessionLocal() as db:
        t_result = await db.execute(
            select(CommunicationTranscript).where(CommunicationTranscript.id == t_id)
        )
        t = t_result.scalars().first()
        assert t.status == "FAILED"

    # Verify audio is still in storage
    stored = await storage_client.download(settings.MINIO_BUCKET, object_key)
    assert stored == audio_bytes, "Original audio must be preserved after STT failure"
