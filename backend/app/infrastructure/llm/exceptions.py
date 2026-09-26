class LLMProviderException(Exception):
    pass


class LLMRetryableException(LLMProviderException):
    """HTTP 429, 5xx, timeout, network failure."""


class LLMPermanentException(LLMProviderException):
    """HTTP 400, 401, 403, unsupported model."""


class LLMRequiresReviewException(LLMProviderException):
    """Provider refusal, malformed structured output, incomplete structured output."""
