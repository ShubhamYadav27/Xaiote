"""Sarvam AI Speech-to-Text provider for Xaiote.

Uses the official sarvamai SDK to transcribe audio via Sarvam Saaras v4.

Authentication: api-subscription-key header (managed by the SDK).
The SARVAM_API_KEY is loaded from the backend environment only.

Supported audio: WAV, MP3, AAC, OGG, OPUS, FLAC, MP4/M4A, AMR, WebM.
REST API limit: <= 30 seconds. Longer audio raises STTUnsupportedDurationError.
"""

import logging
import os
import tempfile
import time

from app.core.config import settings
from app.core.interfaces import AudioInput, SpeechToTextProvider, TranscriptResult
from app.infrastructure.stt.exceptions import (
    STTPermanentError,
    STTTransientError,
    STTUnsupportedDurationError,
)

logger = logging.getLogger(__name__)

# Sarvam REST STT duration limit (seconds)
SARVAM_REST_MAX_DURATION_SECONDS = 30.0

# Maximum keyterms per Sarvam API constraint
SARVAM_MAX_KEYTERMS = 50
SARVAM_MAX_KEYTERM_LENGTH = 64


class SarvamProvider(SpeechToTextProvider):
    """Sarvam AI STT provider using the official sarvamai SDK.

    Implements SpeechToTextProvider ABC for the Xaiote STT pipeline.
    Uses Saaras v4 model with 'transcribe' mode (preserves original language).
    """

    def __init__(self) -> None:
        self.api_key = settings.SARVAM_API_KEY
        self.model = settings.STT_MODEL or "saaras:v4"

        if not self.api_key:
            raise STTPermanentError(
                "SARVAM_API_KEY is not configured. "
                "Set the SARVAM_API_KEY environment variable."
            )

        try:
            from sarvamai import SarvamAI

            self.client = SarvamAI(api_subscription_key=self.api_key)
        except Exception as e:
            raise STTPermanentError(f"Failed to initialize SarvamAI client: {e}") from e

        logger.info(
            "SarvamProvider initialized",
            extra={"stt_provider": "sarvam", "stt_model": self.model},
        )

    async def transcribe(
        self, audio_input: AudioInput, metadata: dict
    ) -> TranscriptResult:
        """Transcribe audio using Sarvam Saaras v4.

        Args:
            audio_input: Audio data with stream, content_type, and duration.
            metadata: Optional dict. May contain 'keyterms' (list[str]) for
                      manufacturing vocabulary hints (max 50 terms, 64 chars each).

        Returns:
            TranscriptResult with transcript in original spoken language.

        Raises:
            STTUnsupportedDurationError: Audio exceeds 30s REST limit.
            STTPermanentError: Non-retryable error (auth, bad request, etc.).
            STTTransientError: Retryable error (rate limit, timeout, etc.).
        """
        # Duration guard — check BEFORE making any API call
        if audio_input.duration_seconds > SARVAM_REST_MAX_DURATION_SECONDS:
            raise STTUnsupportedDurationError(
                duration=audio_input.duration_seconds,
                limit=SARVAM_REST_MAX_DURATION_SECONDS,
                provider="sarvam",
            )

        # Stream audio to a temporary file (keeps memory bounded)
        temp_fd, temp_path = tempfile.mkstemp(suffix=".audio")
        try:
            with open(temp_fd, "wb") as f:  # noqa: ASYNC230
                async for chunk in audio_input.stream:
                    f.write(chunk)

            # Build transcription kwargs
            transcribe_kwargs: dict = {
                "model": self.model,
                "mode": "transcribe",  # Preserves original spoken language
            }

            # Optional keyterms for manufacturing vocabulary
            keyterms = metadata.get("keyterms") if metadata else None
            if keyterms and isinstance(keyterms, list):
                # Enforce Sarvam constraints: max 50 terms, max 64 chars each
                filtered = [
                    str(term)[:SARVAM_MAX_KEYTERM_LENGTH]
                    for term in keyterms[:SARVAM_MAX_KEYTERMS]
                    if term
                ]
                if filtered:
                    transcribe_kwargs["keyterms"] = filtered

            # Optional language_code hint
            language_code = metadata.get("language_code") if metadata else None
            if language_code:
                transcribe_kwargs["language_code"] = language_code

            # Call Sarvam API
            start_time = time.monotonic()

            with open(temp_path, "rb") as audio_file:  # noqa: ASYNC230
                response = self.client.speech_to_text.transcribe(
                    file=audio_file,
                    **transcribe_kwargs,
                )

            latency_ms = int((time.monotonic() - start_time) * 1000)

            # Extract result fields
            transcript_text = getattr(response, "transcript", "") or ""
            language = getattr(response, "language_code", None)
            request_id = getattr(response, "request_id", None)

            logger.info(
                "Sarvam STT completed",
                extra={
                    "stt_provider": "sarvam",
                    "stt_model": self.model,
                    "stt_latency_ms": latency_ms,
                    "stt_language": language,
                    "stt_has_transcript": bool(transcript_text.strip()),
                    "stt_request_id": request_id,
                },
            )

            return TranscriptResult(
                transcript=transcript_text.strip(),
                confidence=None,  # Sarvam does not provide confidence score
                language=language,
                duration_seconds=audio_input.duration_seconds,
                provider_request_id=request_id,
            )

        except STTUnsupportedDurationError:
            # Re-raise without wrapping
            raise
        except STTPermanentError:
            raise
        except STTTransientError:
            raise
        except Exception as e:
            # Map SDK/HTTP errors to STT error types
            return self._handle_provider_error(e)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def _handle_provider_error(self, error: Exception) -> TranscriptResult:
        """Map Sarvam SDK errors to STTPermanentError or STTTransientError.

        Never returns — always raises.
        """
        # Import here to avoid hard dependency at module level
        try:
            from sarvamai.core.api_error import ApiError

            if isinstance(error, ApiError):
                status_code = getattr(error, "status_code", None)
                error_body = str(getattr(error, "body", ""))[:500]

                logger.error(
                    "Sarvam API error",
                    extra={
                        "stt_provider": "sarvam",
                        "stt_error_status": status_code,
                        "stt_error_type": type(error).__name__,
                    },
                )

                if status_code in (400, 413, 415, 422):
                    raise STTPermanentError(
                        f"Sarvam request error {status_code}: {error_body}"
                    ) from error
                elif status_code in (401, 403):
                    raise STTPermanentError(
                        f"Sarvam authentication error {status_code}: {error_body}"
                    ) from error
                elif status_code == 429:
                    raise STTTransientError(
                        f"Sarvam rate limit {status_code}: {error_body}"
                    ) from error
                elif status_code and status_code >= 500:
                    raise STTTransientError(
                        f"Sarvam server error {status_code}: {error_body}"
                    ) from error
                else:
                    raise STTTransientError(
                        f"Sarvam error {status_code}: {error_body}"
                    ) from error
        except (ImportError, STTPermanentError, STTTransientError):
            # Re-raise STT errors; ImportError means SDK structure changed
            raise

        # Network / timeout / unknown errors are transient
        import httpx

        if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
            raise STTTransientError(f"Sarvam network error: {error}") from error

        # Unknown errors default to transient (will be retried)
        raise STTTransientError(
            f"Sarvam unexpected error: {type(error).__name__}: {str(error)[:500]}"
        ) from error
