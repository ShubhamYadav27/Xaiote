"""Shared STT exception classes.

Used by all STT providers (WhisperProvider, SarvamProvider, etc.)
and the stt_worker for error classification and retry decisions.
"""


class STTPermanentError(Exception):
    """Non-retryable STT error.

    Examples: unsupported format, invalid request, auth failure.
    The stt_worker will NOT retry and will mark status as FAILED.
    """


class STTTransientError(Exception):
    """Retryable STT error.

    Examples: rate limit, provider unavailable, network timeout.
    The stt_worker WILL retry up to MAX_RETRIES.
    """


class STTUnsupportedDurationError(STTPermanentError):
    """Audio exceeds provider's synchronous duration limit.

    Extension point: A future Batch STT worker can query transcripts
    with status='NEEDS_REVIEW' and last_error LIKE 'UNSUPPORTED_DURATION%'
    to process these via the Sarvam Batch API.

    The stt_worker handles this distinctly from generic STTPermanentError:
    - Sets status = 'NEEDS_REVIEW' (not 'FAILED')
    - Does NOT increment retry_count
    - Preserves original audio in MinIO
    """

    def __init__(self, duration: float, limit: float, provider: str):
        self.duration = duration
        self.limit = limit
        self.provider = provider
        super().__init__(
            f"UNSUPPORTED_DURATION: audio={duration:.1f}s exceeds "
            f"{provider} REST limit={limit}s. Requires batch processing."
        )
