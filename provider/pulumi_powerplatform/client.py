"""Power Platform SDK client factory with Azure Identity authentication."""

from __future__ import annotations

import os
from typing import Optional

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from mspp_management.service_client_base import ServiceClientBase

# The scope required for the Power Platform Management API.
POWER_PLATFORM_SCOPE = "https://api.powerplatform.com/.default"


class PowerPlatformClient:
    """Wraps the Power Platform Management SDK with configured authentication.

    Supports authentication via:
    - Explicit client secret credentials (tenant_id, client_id, client_secret)
    - DefaultAzureCredential (environment variables, managed identity, Azure CLI, etc.)
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        # Resolve credentials from explicit args or environment variables.
        resolved_tenant_id = tenant_id or os.environ.get("AZURE_TENANT_ID")
        resolved_client_id = client_id or os.environ.get("AZURE_CLIENT_ID")
        resolved_client_secret = client_secret or os.environ.get("AZURE_CLIENT_SECRET")

        if resolved_tenant_id and resolved_client_id and resolved_client_secret:
            credential = ClientSecretCredential(
                tenant_id=resolved_tenant_id,
                client_id=resolved_client_id,
                client_secret=resolved_client_secret,
            )
        else:
            credential = DefaultAzureCredential()

        auth_provider = AzureIdentityAuthenticationProvider(
            credential,
            scopes=[POWER_PLATFORM_SCOPE],
        )
        self._adapter = HttpxRequestAdapter(auth_provider)
        self._sdk = ServiceClientBase(self._adapter)

    @property
    def sdk(self) -> ServiceClientBase:
        """Return the Power Platform Management SDK client."""
        return self._sdk

    @property
    def adapter(self) -> HttpxRequestAdapter:
        """Return the underlying HTTP request adapter (for raw API calls)."""
        return self._adapter
