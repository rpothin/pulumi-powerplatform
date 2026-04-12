"""Power Platform SDK client factory with Azure Identity authentication."""

from __future__ import annotations

import os
from typing import Optional

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from mspp_management.service_client_base import ServiceClientBase

from pulumi_powerplatform.raw_api import RawApiClient

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

        self._credential = credential
        auth_provider = AzureIdentityAuthenticationProvider(
            credential,
            scopes=[POWER_PLATFORM_SCOPE],
        )
        self._adapter = HttpxRequestAdapter(auth_provider)
        self._sdk = ServiceClientBase(self._adapter)
        self._raw = RawApiClient(token_provider=credential)
        self._raw_pp = RawApiClient(
            token_provider=credential,
            base_url="https://api.powerplatform.com",
            scope="https://api.powerplatform.com/.default",
        )

    @property
    def sdk(self) -> ServiceClientBase:
        """Return the Power Platform Management SDK client."""
        return self._sdk

    @property
    def adapter(self) -> HttpxRequestAdapter:
        """Return the underlying HTTP request adapter (for raw API calls)."""
        return self._adapter

    @property
    def raw(self) -> RawApiClient:
        """Return the raw REST API client for BAP admin API calls."""
        return self._raw

    @property
    def raw_pp(self) -> RawApiClient:
        """Return the raw REST API client for Power Platform API calls (api.powerplatform.com)."""
        return self._raw_pp

    @property
    def credential(self):
        """Return the underlying Azure credential."""
        return self._credential
