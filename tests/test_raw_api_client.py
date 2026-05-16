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
    async def test_api_version_none_omits_param(self):
        """Passing api_version=None should omit the api-version query parameter entirely."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            json={"value": []},
            request=httpx.Request("GET", "https://test.local/api/data/v9.2/entities"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            await client.request("GET", "/api/data/v9.2/entities", api_version=None)

        call_kwargs = mock_http.request.call_args
        assert "api-version" not in call_kwargs[1]["params"]

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


class TestRawApiClientReturnHeaders:
    """Tests for the ``return_headers=True`` option."""

    @pytest.mark.asyncio
    async def test_return_headers_returns_tuple(self):
        """When return_headers=True, request() should return (body, headers) tuple."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            201,
            json={"id": "new-record"},
            headers={"OData-EntityId": "https://test.local/api/data/v9.2/accounts(some-guid)"},
            request=httpx.Request("POST", "https://test.local/resources"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("POST", "/resources", body={}, return_headers=True)

        assert isinstance(result, tuple)
        body, headers = result
        assert body == {"id": "new-record"}
        assert "odata-entityid" in headers or "OData-EntityId" in headers

    @pytest.mark.asyncio
    async def test_return_headers_204_returns_none_body(self):
        """204 + return_headers=True should return (None, headers)."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        entity_id_url = "https://test.local/api/data/v9.2/accounts(guid-here)"
        fake_response = httpx.Response(
            204,
            headers={"OData-EntityId": entity_id_url},
            request=httpx.Request("POST", "https://test.local/api/data/v9.2/accounts"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("POST", "/api/data/v9.2/accounts", return_headers=True)

        body, headers = result
        assert body is None
        assert any("entityid" in k.lower() for k in headers)

    @pytest.mark.asyncio
    async def test_return_headers_false_returns_body_only(self):
        """When return_headers=False (default), only body is returned."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            json={"foo": "bar"},
            request=httpx.Request("GET", "https://test.local/path"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            result = await client.request("GET", "/path")

        assert result == {"foo": "bar"}
        assert not isinstance(result, tuple)


class TestRawApiClientAbsoluteUrl:
    """Tests for absolute URL support (path starting with 'http')."""

    @pytest.mark.asyncio
    async def test_absolute_url_used_verbatim(self):
        """An absolute URL should be sent directly without prepending base_url."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        abs_url = "https://org.crm.dynamics.com/api/data/v9.2/accounts"
        fake_response = httpx.Response(
            200,
            json={"value": []},
            request=httpx.Request("GET", abs_url),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            await client.request("GET", abs_url, api_version=None)

        call_kwargs = mock_http.request.call_args
        actual_url = call_kwargs[0][1]
        assert actual_url == abs_url

    @pytest.mark.asyncio
    async def test_relative_path_prepends_base_url(self):
        """A relative path should be joined with base_url."""
        cred = _fake_credential()
        client = RawApiClient(token_provider=cred, base_url="https://test.local")

        fake_response = httpx.Response(
            200,
            json={},
            request=httpx.Request("GET", "https://test.local/api/data"),
        )

        with patch.object(client, "_get_http") as mock_get_http:
            mock_http = AsyncMock()
            mock_http.request.return_value = fake_response
            mock_get_http.return_value = mock_http

            await client.request("GET", "/api/data", api_version=None)

        call_kwargs = mock_http.request.call_args
        actual_url = call_kwargs[0][1]
        assert actual_url == "https://test.local/api/data"


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
