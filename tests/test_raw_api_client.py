"""Tests for RawApiClient — request dispatching, token handling, and error mapping."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from rpothin_powerplatform.raw_api.client import RawApiClient
from rpothin_powerplatform.utils import HttpError


class _FakeToken:
    """Minimal stand-in for an ``azure.core.credentials.AccessToken``."""

    def __init__(self, token: str = "fake-token") -> None:
        self.token = token


def _fake_credential(token: str = "fake-token") -> MagicMock:
    """Return a mock credential whose ``get_token`` returns a fixed token."""
    cred = MagicMock()
    cred.get_token.return_value = _FakeToken(token)
    return cred


class TestRawApiClientInit:
    """Tests for initialisation and configuration."""

    def test_default_base_url(self):
        client = RawApiClient(token_provider=_fake_credential())
        assert client._base_url == "https://api.bap.microsoft.com"

    def test_custom_base_url_strips_trailing_slash(self):
        client = RawApiClient(token_provider=_fake_credential(), base_url="https://custom.example.com/")
        assert client._base_url == "https://custom.example.com"

    def test_default_scope(self):
        client = RawApiClient(token_provider=_fake_credential())
        assert client._scope == "https://api.bap.microsoft.com/.default"

    def test_custom_scope(self):
        client = RawApiClient(
            token_provider=_fake_credential(),
            scope="https://api.powerplatform.com/.default",
        )
        assert client._scope == "https://api.powerplatform.com/.default"


class TestRawApiClientRequest:
    """Tests for the ``request`` method."""

    @pytest.mark.asyncio
    async def test_get_returns_json(self):
        """A successful GET should return parsed JSON."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            json={"value": [1, 2, 3]},
            request=httpx.Request("GET", "https://test.local/some/path"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("GET", "/some/path")

        assert result == {"value": [1, 2, 3]}
        mock_http.request.assert_awaited_once()
        call_kwargs = mock_http.request.call_args
        assert call_kwargs[1]["headers"]["Authorization"] == "Bearer fake-token"

    @pytest.mark.asyncio
    async def test_post_sends_json_body(self):
        """A POST with a body should send JSON."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            201,
            json={"id": "new-resource"},
            request=httpx.Request("POST", "https://test.local/resources"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("POST", "/resources", body={"name": "test"})

        assert result == {"id": "new-resource"}
        call_kwargs = mock_http.request.call_args
        assert call_kwargs[1]["json"] == {"name": "test"}

    @pytest.mark.asyncio
    async def test_204_returns_none(self):
        """A 204 No Content response should return None."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            204,
            request=httpx.Request("DELETE", "https://test.local/resources/1"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("DELETE", "/resources/1")

        assert result is None

    @pytest.mark.asyncio
    async def test_4xx_raises_http_error(self):
        """A 4xx response should raise HttpError."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            404,
            text="Not Found",
            request=httpx.Request("GET", "https://test.local/missing"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            with pytest.raises(HttpError) as exc_info:
                await client.request("GET", "/missing")

            assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_api_version_query_param(self):
        """The api-version query parameter should be sent."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://test.local/path"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            await client.request("GET", "/path", api_version="2021-04-01")

        call_kwargs = mock_http.request.call_args
        assert call_kwargs[1]["params"]["api-version"] == "2021-04-01"

    @pytest.mark.asyncio
    async def test_empty_body_returns_none(self):
        """A 200 response with empty content should return None."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            content=b"",
            request=httpx.Request("PATCH", "https://test.local/resources/1"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("PATCH", "/resources/1", body={"name": "updated"})

        assert result is None


class TestRawApiClientClose:
    """Tests for the close method."""

    @pytest.mark.asyncio
    async def test_close_when_no_client(self):
        """Closing without ever making a request should be a no-op."""
        client = RawApiClient(token_provider=_fake_credential())
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_closes_http_client(self):
        """Closing should close the underlying httpx client."""
        client = RawApiClient(token_provider=_fake_credential())
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.is_closed = False
        client._http = mock_http

        await client.close()

        mock_http.aclose.assert_awaited_once()
        assert client._http is None
