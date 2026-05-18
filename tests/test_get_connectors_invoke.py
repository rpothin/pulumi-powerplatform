"""Tests for the getConnectors function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from kiota_abstractions.api_error import APIError
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_connectors import GetConnectorsFunction


def _fake_connector(*, connector_id: str = "conn-1", name: str = "SQL", display_name: str = "SQL Server"):
    """Return a fake connector SDK object."""
    c = MagicMock()
    c.id = connector_id
    c.name = name
    c.display_name = display_name
    c.type = "Standard"
    return c


def _mock_client(connectors: list | None = None):
    """Build a MagicMock that mimics the SDK call chain for connectors.get()."""
    client = MagicMock(spec=PowerPlatformClient)
    result = MagicMock()
    result.value = connectors
    by_env = client.sdk.connectivity.environments.by_environment_id.return_value
    by_env.connectors.get = AsyncMock(return_value=result)
    return client


@pytest.fixture
def handler_with_connectors():
    """Handler whose SDK returns two connectors."""
    connectors = [
        _fake_connector(connector_id="conn-1", name="SQL", display_name="SQL Server"),
        _fake_connector(connector_id="conn-2", name="SharePoint", display_name="SharePoint Online"),
    ]
    client = _mock_client(connectors)
    return GetConnectorsFunction(client=client), client


@pytest.fixture
def handler_empty():
    """Handler whose SDK returns no connectors."""
    client = _mock_client([])
    return GetConnectorsFunction(client=client), client


class TestGetConnectorsInvoke:
    """Tests for the GetConnectorsFunction invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_returns_connectors(self, handler_with_connectors):
        handler, client = handler_with_connectors
        request = InvokeRequest(
            tok="powerplatform:index:getConnectors",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        connectors_pv = response.return_value["connectors"]
        connectors = connectors_pv.value
        assert len(connectors) == 2
        assert connectors[0].value["id"].value == "conn-1"
        assert connectors[0].value["name"].value == "SQL"
        assert connectors[1].value["id"].value == "conn-2"

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler_empty):
        handler, _ = handler_empty
        request = InvokeRequest(
            tok="powerplatform:index:getConnectors",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        connectors_pv = response.return_value["connectors"]
        assert len(connectors_pv.value) == 0

    @pytest.mark.asyncio
    async def test_invoke_passes_request_configuration(self, handler_with_connectors):
        """get() must be called with a request_configuration kwarg (carries api-version)."""
        handler, client = handler_with_connectors
        request = InvokeRequest(
            tok="powerplatform:index:getConnectors",
            args={"environmentId": PropertyValue("env-1")},
        )
        await handler.invoke(request)

        by_env = client.sdk.connectivity.environments.by_environment_id.return_value
        by_env.connectors.get.assert_awaited_once()
        call_kwargs = by_env.connectors.get.await_args.kwargs
        assert "request_configuration" in call_kwargs, "api-version must be passed via request_configuration"

    @pytest.mark.asyncio
    async def test_api_error_raises_runtime_error(self):
        """APIError from the SDK must be re-raised as RuntimeError with status and message."""
        client = MagicMock(spec=PowerPlatformClient)
        api_err = APIError(message="Bad Request", response_status_code=400)
        by_env = client.sdk.connectivity.environments.by_environment_id.return_value
        by_env.connectors.get = AsyncMock(side_effect=api_err)

        handler = GetConnectorsFunction(client=client)
        request = InvokeRequest(
            tok="powerplatform:index:getConnectors",
            args={"environmentId": PropertyValue("env-1")},
        )

        with pytest.raises(RuntimeError, match="400") as exc_info:
            await handler.invoke(request)
        assert exc_info.value.__cause__ is api_err
