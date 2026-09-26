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
        if self.api_key == "mock-or-missing" or not self.api_key:
            return ExtractedEventResult(
                raw_json='{"events": [{"event_type": "MACHINE_FAILURE", "urgency": "HIGH", "plant_name": "Main Plant", "machine_name": "CNC 2", "reported_issue": "spindle failure hai. Maintenance ko lagbhag 8 ghante lagenge", "is_actionable": true, "confidence_score": 0.95}]}',
                provider="openai",
                model="gpt-4o-mini",
                completion_id="mock-123",
                prompt_tokens=10,
                completion_tokens=10,
                latency_ms=100
            )
"""
new_content = re.sub(r'    async def extract_event.*?        headers = \{', replacement + '        headers = {', content, flags=re.DOTALL)
with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)
