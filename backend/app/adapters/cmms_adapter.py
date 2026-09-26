from typing import Dict, Any
from app.interfaces.adapters import BaseActionAdapter, AdapterCapabilities, AdapterResult, AdapterExecutionContext
from app.services.credential_service import CredentialService
from app.services.endpoint_registry import EndpointRegistryService

class GenericRestCmmsAdapter(BaseActionAdapter):
    
    def get_capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_idempotency=True,
            supports_safe_reconciliation=True,
            supports_async_confirmation=True,
            supports_delivery_status=False,
            retry_behavior="EXPONENTIAL_BACKOFF"
        )

    def execute(self, context: AdapterExecutionContext) -> AdapterResult:
        if context.allowlisted_operation != "UPDATE_WORK_ORDER_STATUS":
            return AdapterResult(success=False, error_payload={"error": "Unsupported operation"}, is_retryable_error=False)
            
        if context.action_type != "MARK_WORK_ORDER_COMPLETED":
            return AdapterResult(success=False, error_payload={"error": "Unsupported action type"}, is_retryable_error=False)

        try:
            endpoint_config = EndpointRegistryService.get_endpoint("Generic REST CMMS", context.allowlisted_operation)
        except ValueError as e:
            return AdapterResult(success=False, error_payload={"error": str(e)}, is_retryable_error=False)

        secret_token = CredentialService.resolve_credential(
            company_id=context.company_id,
            plant_id=context.plant_id,
            provider="Generic REST CMMS",
            integration_id=context.integration_id,
            environment="PRODUCTION",
            credential_reference=context.credential_reference,
            credential_version=context.credential_version
        )
        
        endpoint_url = endpoint_config["url_template"].format(target_identity=context.target_identity)
        http_method = endpoint_config["http_method"]
        
        payload = {
            "status": "COMPLETED",
            "notes": "Updated via Xaiote"
        }
        
        headers = {
            "Authorization": f"Bearer {secret_token}",
            "Idempotency-Key": context.downstream_idempotency_key
        }

        simulated_response_code = context.validated_parameters.get("_mock_response_code", 202)
        simulated_target_state = context.validated_parameters.get("_mock_external_state", "IN_PROGRESS")
        
        if simulated_target_state in ["CANCELLED", "ON_HOLD", "NOT_FOUND", "CONFLICT", "PROVIDER_REJECTED"]:
            return AdapterResult(success=False, error_payload={"error": f"Invalid external target state: {simulated_target_state}"}, is_retryable_error=False)
            
        if simulated_target_state == "COMPLETED":
            return AdapterResult(success=True, external_correlation_id=context.downstream_idempotency_key)
            
        if simulated_response_code == 202:
            return AdapterResult(
                success=False, 
                is_accepted_pending_confirmation=True, 
                external_correlation_id=context.downstream_idempotency_key
            )
        elif simulated_response_code == 200:
            return AdapterResult(
                success=True,
                external_correlation_id=context.downstream_idempotency_key
            )
        elif simulated_response_code in [400, 422, 404, 403, 409]:
            return AdapterResult(success=False, error_payload={"error": "Permanent business error"}, is_retryable_error=False)
        elif simulated_response_code == 401:
            return AdapterResult(success=False, error_payload={"error": "Credential refresh required"}, is_retryable_error=False)
        elif simulated_response_code == 429:
            return AdapterResult(success=False, error_payload={"error": "Rate limited"}, is_retryable_error=True)
        elif simulated_response_code in [500, 502, 503, 504]:
            return AdapterResult(success=False, error_payload={"error": "Provider unavailable"}, is_retryable_error=True)
        elif simulated_response_code == 0:
            return AdapterResult(success=False, is_unknown_outcome=True)
            
        return AdapterResult(success=False, error_payload={"error": "Unknown status code"}, is_retryable_error=False)

