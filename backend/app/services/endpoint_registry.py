class EndpointRegistryService:
    _registry = {
        ("Generic REST CMMS", "UPDATE_WORK_ORDER_STATUS"): {
            "url_template": "https://internal-cmms-registry.local/api/v1/work-orders/{target_identity}/status",
            "http_method": "POST"
        }
    }

    @staticmethod
    def get_endpoint(provider: str, operation: str) -> dict:
        # Prevents client/LLM override of URLs and methods.
        # Strict mapping enforced by server configuration.
        endpoint = EndpointRegistryService._registry.get((provider, operation))
        if not endpoint:
            raise ValueError(f"No endpoint registered for provider '{provider}' and operation '{operation}'")
        return endpoint
