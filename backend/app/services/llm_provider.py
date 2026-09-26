from typing import Dict, Any, List
from abc import ABC, abstractmethod

class LLMProviderException(Exception):
    pass

class ActionIntelligenceLLMProvider(ABC):
    @abstractmethod
    def generate_recommendation_candidates(
        self, 
        system_prompt: str,
        operational_context: str, 
        schema_version: str
    ) -> List[Dict[str, Any]]:
        '''
        Queries the LLM with the provided read-only operational context and expected schema.
        Returns a list of untrusted, parsed JSON candidate dictionaries.
        '''
        pass

class DummyLLMProvider(ActionIntelligenceLLMProvider):
    def generate_recommendation_candidates(
        self, 
        system_prompt: str,
        operational_context: str, 
        schema_version: str
    ) -> List[Dict[str, Any]]:
        return []
