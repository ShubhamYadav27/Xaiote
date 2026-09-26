"""STT Provider Factory.

Selects and instantiates the active STT provider based on settings.STT_PROVIDER.

Usage:
    from app.infrastructure.stt import get_stt_provider
    provider = get_stt_provider()
    result = await provider.transcribe(audio_input, metadata)
"""

import logging

from app.core.config import settings
from app.core.interfaces import SpeechToTextProvider

logger = logging.getLogger(__name__)


def get_stt_provider() -> SpeechToTextProvider:
    """Create and return the configured STT provider.

    Reads settings.STT_PROVIDER to determine which provider to instantiate:
    - "sarvam" -> SarvamProvider (Sarvam Saaras v4)
    - "openai" -> WhisperProvider (OpenAI Whisper)

    Returns:
        An initialized SpeechToTextProvider instance.

    Raises:
        ValueError: If STT_PROVIDER is not a recognized provider name.
    """
    provider_name = settings.STT_PROVIDER.lower().strip()

    if provider_name == "sarvam":
        from app.infrastructure.stt.sarvam_provider import SarvamProvider

        logger.info(
            "STT provider selected: sarvam",
            extra={"stt_provider": "sarvam", "stt_model": settings.STT_MODEL},
        )
        return SarvamProvider()

    elif provider_name == "openai":
        from app.infrastructure.stt.whisper_provider import WhisperProvider

        logger.info(
            "STT provider selected: openai",
            extra={"stt_provider": "openai", "stt_model": settings.STT_MODEL},
        )
        return WhisperProvider()

    else:
        raise ValueError(
            f"Unknown STT_PROVIDER: '{settings.STT_PROVIDER}'. "
            f"Supported providers: 'sarvam', 'openai'."
        )
