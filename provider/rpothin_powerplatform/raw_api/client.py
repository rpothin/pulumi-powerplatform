"""Low-level HTTP client for Power Platform REST API calls not covered by the SDK."""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from rpothin_powerplatform.utils import HttpError, retry_with_backoff

logger = logging.getLogger(__name__)


class RawApiClient:
    """HTTP client for direct REST calls to the Power Platform BAP admin API.

    This client manages its own ``httpx.AsyncClient`` and uses an externally
    provided async token-provider callback for authentication. All requests are
    automatically wrapped with :func:`retry_with_backoff` for resilience against
    transient errors and rate limiting.

    Usage example (inside a resource handler)::

        raw = RawApiClient(token_provider=my_token_fn)
        result = await raw.request("GET", "/providers/Microsoft.BusinessAppPlatform/environments")
    """

    BASE_URL = "https://api.bap.microsoft.com"

    def __init__(
        self,
        token_provider: Any,
        *,
        base_url: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> None:
        """Initialise the client.

        Parameters
        ----------
        token_provider:
            An Azure ``TokenCredential`` that supports ``get_token(scope)``.
        base_url:
            Override the default BAP admin API base URL (useful for testing).
        scope:
            Override the default OAuth scope (defaults to BAP scope).
        """
        self._token_provider = token_provider
        self._base_url = (base_url or self.BASE_URL).rstrip("/")
        self._scope = scope or "https://api.bap.microsoft.com/.default"
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        """Lazily create the httpx client."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self._http

    async def _get_token(self) -> str:
        """Obtain a bearer token from the credential."""
        token = self._token_provider.get_token(self._scope)
        return token.token

    async def request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict[str, Any]] = None,
        api_version: Optional[str] = "2023-06-01",
        extra_headers: Optional[dict[str, str]] = None,
        return_headers: bool = False,
    ) -> Any:
        """Send an HTTP request to the Power Platform BAP admin API.

        Parameters
        ----------
        method:
            HTTP method (GET, POST, PUT, PATCH, DELETE).
        path:
            API path relative to ``BASE_URL``, or a full URL (must share the
            same host as ``base_url`` — never pass user-controlled values here).
        body:
            Optional JSON body for POST/PUT/PATCH requests.
        api_version:
            ``api-version`` query parameter. Pass ``None`` to omit it.
        extra_headers:
            Additional request headers to merge with the default headers.
        return_headers:
            When ``True``, returns a ``(body, response_headers)`` tuple instead
            of just the body. Useful for inspecting response headers such as
            ``OData-EntityId`` on Dataverse POST responses.

        Returns
        -------
        The parsed JSON response, or ``None`` for 204/empty responses.
        When ``return_headers=True``, returns a tuple ``(body, dict[str, str])``.

        Raises
        ------
        HttpError
            On non-2xx responses (retryable errors are retried automatically).
        """

        async def _do_request() -> Any:
            client = await self._get_http()
            token = await self._get_token()
            # Support absolute URLs (e.g. Location/OData-EntityId headers) — only
            # call this with paths sourced from our own API responses, not user input.
            url = path if path.startswith("http") else f"{self._base_url}{path}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            if extra_headers:
                headers.update(extra_headers)
            params = {"api-version": api_version} if api_version else {}

            response = await client.request(
                method,
                url,
                headers=headers,
                params=params,
                json=body if body is not None else None,
            )

            if response.status_code >= 400:
                resp_headers = {k: v for k, v in response.headers.items()}
                raise HttpError(
                    response.status_code,
                    f"{method} {path} returned {response.status_code}: {response.text[:500]}",
                    headers=resp_headers,
                )

            resp_headers_dict = {k: v for k, v in response.headers.items()}

            if response.status_code == 204 or not response.content:
                parsed = None
            else:
                parsed = response.json()

            if return_headers:
                return (parsed, resp_headers_dict)
            return parsed

        return await retry_with_backoff(_do_request)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http is not None and not self._http.is_closed:
            await self._http.aclose()
            self._http = None
