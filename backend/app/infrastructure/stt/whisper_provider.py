import logging
import os
import tempfile

import httpx

from app.core.config import settings
from app.core.interfaces import AudioInput, SpeechToTextProvider, TranscriptResult
from app.infrastructure.stt.exceptions import STTPermanentError, STTTransientError

logger = logging.getLogger(__name__)

WHISPER_MAX_BYTES = 25 * 1024 * 1024  # 25 MB


class WhisperProvider(SpeechToTextProvider):
    def __init__(self):
        self.api_key = settings.STT_API_KEY
        self.model = settings.STT_MODEL
        self.url = "https://api.openai.com/v1/audio/transcriptions"

    async def transcribe(
        self, audio_input: AudioInput, metadata: dict
    ) -> TranscriptResult:
        if audio_input.size_bytes > WHISPER_MAX_BYTES:
            raise STTPermanentError(
                f"Audio size {audio_input.size_bytes} exceeds Whisper limit of {WHISPER_MAX_BYTES} bytes."
            )

        # Stream to a temporary file to keep memory bounded
        temp_fd, temp_path = tempfile.mkstemp(suffix=".audio")
        try:
            with open(temp_fd, "wb") as f:  # noqa: ASYNC230
                async for chunk in audio_input.stream:
                    f.write(chunk)

            # Send to Whisper
            async with httpx.AsyncClient(timeout=120.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                with open(temp_path, "rb") as f:  # noqa: ASYNC230
                    files = {
                        "file": (audio_input.filename, f, audio_input.content_type)
                    }
                    data = {"model": self.model, "response_format": "verbose_json"}

                    response = await client.post(
                        self.url, headers=headers, data=data, files=files
                    )

                    if response.status_code in (400, 401, 403, 413, 415):
                        raise STTPermanentError(
                            f"OpenAI Permanent Error {response.status_code}: {response.text}"
                        )
                    elif response.status_code != 200:
                        raise STTTransientError(
                            f"OpenAI Transient Error {response.status_code}: {response.text}"
                        )

                    result = response.json()

                    text = result.get("text", "").strip()
                    language = result.get("language")
                    duration = result.get("duration")
                    request_id = response.headers.get("x-request-id")

                    return TranscriptResult(
                        transcript=text,
                        confidence=None,  # Whisper doesn't provide word-level confidence natively in this endpoint
                        language=language,
                        duration_seconds=duration,
                        provider_request_id=request_id,
                    )

        except httpx.RequestError as e:
            raise STTTransientError(f"HTTP Request failed: {e}")
        finally:
            os.remove(temp_path)
