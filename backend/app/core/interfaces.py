from abc import ABC, abstractmethod


class ObjectStorage(ABC):
    @abstractmethod
    async def upload(self, bucket_name: str, object_name: str, data: bytes):
        pass

    @abstractmethod
    async def download(self, bucket_name: str, object_name: str) -> bytes:
        pass

    @abstractmethod
    async def delete(self, bucket_name: str, object_name: str):
        pass

    @abstractmethod
    async def exists(self, bucket_name: str, object_name: str) -> bool:
        pass

    @abstractmethod
    async def get_presigned_url(self, bucket_name: str, object_name: str) -> str:
        pass


from collections.abc import AsyncIterator

from pydantic import BaseModel


class AudioInput(BaseModel):
    stream: AsyncIterator[bytes]
    content_type: str
    filename: str
    size_bytes: int
    duration_seconds: float

    class Config:
        arbitrary_types_allowed = True


class TranscriptResult(BaseModel):
    transcript: str
    confidence: float | None = None
    language: str | None = None
    duration_seconds: float | None = None
    provider_request_id: str | None = None


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(
        self, audio_input: AudioInput, metadata: dict
    ) -> TranscriptResult:
        pass


class ExtractionMetadata(BaseModel):
    transcript_id: str
    attempt_count: int
    provider_name_override: str | None = None


class ExtractedEventResult(BaseModel):
    payload: dict
    raw_response: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    provider_request_id: str | None = None


class LLMProvider(ABC):
    @abstractmethod
    async def extract_event(
        self,
        transcript_text: str,
        schema: dict,
        prompt_instructions: str,
        metadata: ExtractionMetadata,
    ) -> ExtractedEventResult:
        pass
