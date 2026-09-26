"""Optional Sarvam STT live integration test.

This test ONLY runs when SARVAM_API_KEY is configured in the environment.
It makes a REAL API call to Sarvam — do NOT include in the default test suite.

Usage:
    SARVAM_API_KEY=<key> python -m pytest tests/integration/test_sarvam_integration.py -v

Security:
    - NEVER logs or prints the API key
    - NEVER logs authorization headers
    - Only logs safe metadata: provider, model, status, latency, transcript length
"""

import logging
import os
import time
import wave

import pytest

logger = logging.getLogger(__name__)

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")

skip_reason = "SARVAM_API_KEY not configured — skipping live integration test"


def create_test_wav(path: str, duration_seconds: int = 3) -> int:
    """Create a short WAV file for testing. Returns file size."""
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(16000)  # 16kHz recommended by Sarvam
        f.writeframes(b"\x00" * 16000 * 2 * duration_seconds)
    return os.path.getsize(path)


# ============================================================
# 1. SDK Import + Version
# ============================================================
@pytest.mark.skipif(not SARVAM_API_KEY, reason=skip_reason)
def test_sarvam_sdk_import():
    """Verify sarvamai SDK imports and report version."""
    import sarvamai

    version = getattr(sarvamai, "__version__", "unknown")
    logger.info(f"sarvamai SDK version: {version}")
    assert sarvamai is not None


# ============================================================
# 2. Provider Initialization
# ============================================================
@pytest.mark.skipif(not SARVAM_API_KEY, reason=skip_reason)
def test_sarvam_provider_init():
    """Verify SarvamProvider initializes with the configured key."""
    os.environ.setdefault("STT_PROVIDER", "sarvam")
    os.environ.setdefault("STT_MODEL", "saaras:v4")

    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()
    assert provider.model == "saaras:v4"
    assert provider.client is not None
    logger.info("SarvamProvider initialized successfully")
    logger.info(f"SARVAM_API_KEY: PRESENT (length={len(SARVAM_API_KEY)})")


# ============================================================
# 3. Authentication Check
# ============================================================
@pytest.mark.skipif(not SARVAM_API_KEY, reason=skip_reason)
def test_sarvam_authentication():
    """Verify the configured API key is accepted by Sarvam."""
    wav_path = "integration_auth_test.wav"
    try:
        create_test_wav(wav_path, 1)

        from sarvamai import SarvamAI
        from sarvamai.core.api_error import ApiError

        client = SarvamAI(api_subscription_key=SARVAM_API_KEY)

        start = time.monotonic()
        try:
            with open(wav_path, "rb") as f:
                response = client.speech_to_text.transcribe(
                    file=f,
                    model="saaras:v4",
                    mode="transcribe",
                )
            latency_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "Sarvam authentication: ACCEPTED",
                extra={
                    "stt_provider": "sarvam",
                    "stt_model": "saaras:v4",
                    "stt_auth": "accepted",
                    "stt_latency_ms": latency_ms,
                },
            )
        except ApiError as e:
            latency_ms = int((time.monotonic() - start) * 1000)
            if e.status_code == 403:
                pytest.fail(
                    f"Sarvam authentication REJECTED (403): API key invalid/revoked. "
                    f"Latency: {latency_ms}ms"
                )
            elif e.status_code == 429:
                pytest.fail(
                    f"Sarvam rate limit (429): Account/credit issue. "
                    f"Latency: {latency_ms}ms"
                )
            else:
                pytest.fail(
                    f"Sarvam API error {e.status_code}: {e.body}. "
                    f"Latency: {latency_ms}ms"
                )
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


# ============================================================
# 4. Real STT Transcription (via SarvamProvider)
# ============================================================
@pytest.mark.skipif(not SARVAM_API_KEY, reason=skip_reason)
@pytest.mark.asyncio
async def test_sarvam_real_transcription():
    """Real transcription through SarvamProvider (not raw SDK)."""
    from collections.abc import AsyncIterator

    from app.core.interfaces import AudioInput, TranscriptResult
    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()

    wav_path = "integration_stt_test.wav"
    try:
        file_size = create_test_wav(wav_path, 3)

        async def stream_file() -> AsyncIterator[bytes]:
            with open(wav_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk

        audio_input = AudioInput(
            stream=stream_file(),
            content_type="audio/wav",
            filename="test.wav",
            size_bytes=file_size,
            duration_seconds=3.0,
        )

        start = time.monotonic()
        result = await provider.transcribe(audio_input, {})
        latency_ms = int((time.monotonic() - start) * 1000)

        assert isinstance(result, TranscriptResult)

        logger.info(
            "=== SARVAM REAL STT RESULT ===\n"
            f"  provider: sarvam\n"
            f"  model: saaras:v4\n"
            f"  status: SUCCESS\n"
            f"  transcript_received: {'yes' if result.transcript else 'no (empty/no_speech)'}\n"
            f"  transcript_length: {len(result.transcript)}\n"
            f"  language: {result.language}\n"
            f"  duration_seconds: {result.duration_seconds}\n"
            f"  request_id: {result.provider_request_id}\n"
            f"  latency_ms: {latency_ms}\n"
            f"  audio_duration: 3.0s"
        )

    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)


# ============================================================
# 5. Duration Guard (>30s)
# ============================================================
@pytest.mark.skipif(not SARVAM_API_KEY, reason=skip_reason)
@pytest.mark.asyncio
async def test_sarvam_duration_guard_live():
    """Verify >30s audio does NOT reach the API."""
    from collections.abc import AsyncIterator

    from app.core.interfaces import AudioInput
    from app.infrastructure.stt.exceptions import STTUnsupportedDurationError
    from app.infrastructure.stt.sarvam_provider import SarvamProvider

    provider = SarvamProvider()

    async def empty_stream() -> AsyncIterator[bytes]:
        yield b""

    audio_input = AudioInput(
        stream=empty_stream(),
        content_type="audio/wav",
        filename="long_audio.wav",
        size_bytes=1000,
        duration_seconds=45.0,
    )

    with pytest.raises(STTUnsupportedDurationError) as exc_info:
        await provider.transcribe(audio_input, {})

    assert exc_info.value.duration == 45.0
    assert exc_info.value.provider == "sarvam"
    logger.info("Duration guard: PASSED — >30s audio blocked before API call")
