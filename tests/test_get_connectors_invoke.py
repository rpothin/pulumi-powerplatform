"""Tests for the getConnectors function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.functions.get_connectors import GetConnectorsFunction


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
