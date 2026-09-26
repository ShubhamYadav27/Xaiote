from typing import Dict, Any, Optional
from pydantic import BaseModel

class AdapterCapabilities(BaseModel):
    supports_idempotency: bool
    supports_safe_reconciliation: bool
    supports_async_confirmation: bool
    supports_delivery_status: bool
    retry_behavior: str

class AdapterResult(BaseModel):
    success: bool
    external_correlation_id: Optional[str] = None
    error_payload: Optional[Dict[str, Any]] = None
    is_retryable_error: bool = False
    is_unknown_outcome: bool = False
    is_accepted_pending_confirmation: bool = False

class AdapterExecutionContext(BaseModel):
    company_id: str
    plant_id: Optional[str]
    action_instance_id: str
    execution_attempt_id: str
    action_type: str
    allowlisted_operation: str
    validated_parameters: Dict[str, Any]
    target_identity: str
    correlation_id: Optional[str]
    downstream_idempotency_key: str
    integration_id: str
    credential_reference: str
    credential_version: int

class BaseActionAdapter:
    def get_capabilities(self) -> AdapterCapabilities:
        raise NotImplementedError

    def execute(self, context: AdapterExecutionContext) -> AdapterResult:
        raise NotImplementedError
