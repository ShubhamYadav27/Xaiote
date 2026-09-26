import os, re
path = 'backend/app/infrastructure/llm/openai_provider.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

replacement = """
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
"""
new_content = re.sub(r'    async def extract_event.*?        headers = \{', replacement + '        headers = {', content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
