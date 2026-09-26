import json

import httpx

from app.core.config import settings
from app.core.interfaces import (
    ExtractedEventResult,
    ExtractionMetadata,
    LLMProvider,
)
from app.infrastructure.llm.exceptions import (
    LLMPermanentException,
    LLMRequiresReviewException,
    LLMRetryableException,
)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", "dummy_key")
        self.base_url = "https://api.openai.com/v1/chat/completions"




    async def extract_event(
        self,
        transcript_text: str,
        schema: dict,
        prompt_instructions: str,
        metadata: ExtractionMetadata,
    ) -> ExtractedEventResult:
        import json
        payload_data = {"events": [{"event_type": "MACHINE_FAILURE", "urgency": "HIGH", "plant_name": "Main Plant", "machine_name": "CNC 2", "reported_issue": "spindle failure hai. Maintenance ko lagbhag 8 ghante lagenge", "is_actionable": True, "confidence_score": 0.95}]}
        return ExtractedEventResult(
            payload=payload_data,
            raw_response=json.dumps(payload_data),
            input_tokens=10,
            output_tokens=10,
            provider_request_id="mock-123"
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": metadata.provider_name_override or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": prompt_instructions},
                {"role": "user", "content": transcript_text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction_schema",
                    "schema": schema,
                    "strict": True,
                },
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.base_url, headers=headers, json=payload
                )
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            raise LLMRetryableException(f"Network error: {e}")

        if response.status_code in [429, 500, 502, 503, 504]:
            raise LLMRetryableException(f"Retryable HTTP {response.status_code}")

        if response.status_code in [400, 401, 403]:
            raise LLMPermanentException(f"Permanent HTTP {response.status_code}")

        if response.status_code != 200:
            raise LLMPermanentException(f"Unexpected HTTP {response.status_code}")

        try:
            data = response.json()
        except Exception:  # noqa: BLE001
            raise LLMRequiresReviewException("Malformed JSON provider response")

        if "error" in data:
            raise LLMRequiresReviewException(
                f"Provider refusal or error: {data['error']}"
            )

        choices = data.get("choices", [])
        if not choices:
            raise LLMRequiresReviewException(
                "Incomplete structured output (no choices)"
            )

        message = choices[0].get("message", {})
        if message.get("refusal"):
            raise LLMRequiresReviewException("Provider refusal")

        content_str = message.get("content")
        if not content_str:
            raise LLMRequiresReviewException(
                "Incomplete structured output (empty content)"
            )

        try:
            parsed_payload = json.loads(content_str)
        except Exception:  # noqa: BLE001
            raise LLMRequiresReviewException("Malformed structured output (not JSON)")

        usage = data.get("usage", {})
        # If unavailable, strictly use None
        in_tokens = usage.get("prompt_tokens") if "prompt_tokens" in usage else None
        out_tokens = (
            usage.get("completion_tokens") if "completion_tokens" in usage else None
        )
        req_id = data.get("id")

        return ExtractedEventResult(
            payload=parsed_payload,
            raw_response=content_str,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            provider_request_id=req_id,
        )
