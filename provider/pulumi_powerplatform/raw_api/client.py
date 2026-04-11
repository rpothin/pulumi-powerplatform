"""Low-level HTTP client for Power Platform REST API calls not covered by the SDK."""

from __future__ import annotations

from typing import Any, Optional

from kiota_http.httpx_request_adapter import HttpxRequestAdapter


class RawApiClient:
    """Thin wrapper around the Kiota ``HttpxRequestAdapter`` for direct REST calls.

    This client reuses the same authentication and transport layer as the
    ``powerplatform-management`` SDK so that credentials, base URL, and retry
    behaviour are consistent.

    Usage example (inside a resource handler)::

        raw = RawApiClient(self._client.adapter)
        result = await raw.request("GET", "/providers/Microsoft.BusinessAppPlatform/environments")
    """

    BASE_URL = "https://api.powerplatform.com"

    def __init__(self, adapter: HttpxRequestAdapter) -> None:
        self._adapter = adapter

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict[str, Any]] = None,
        api_version: str = "2022-03-01-preview",
    ) -> Any:
        """Send an HTTP request to the Power Platform REST API.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, PUT, PATCH, DELETE).
        path:
            API path relative to ``BASE_URL`` (e.g.
            ``/providers/Microsoft.BusinessAppPlatform/environments``).
        body:
            Optional JSON body for POST/PUT/PATCH requests.
        api_version:
            ``api-version`` query parameter.

        Returns
        -------
        The parsed JSON response, or ``None`` for 204/empty responses.

        Raises
        ------
        NotImplementedError
            This is a scaffold — the actual HTTP execution is not yet wired up.
            It will be implemented when the first resource requires raw REST access
            (e.g. Environment creation).
        """
        raise NotImplementedError(
            f"RawApiClient.request() is not yet implemented. "
            f"Called with {method} {path}. "
            f"Wire up httpx via the Kiota adapter when the first raw API consumer is added."
        )
