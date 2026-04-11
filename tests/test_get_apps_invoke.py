"""Tests for the getApps function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.functions.get_apps import GetAppsFunction


def _fake_app(*, app_id: str = "app-1", name: str = "MyApp", display_name: str = "My Application"):
    """Return a fake Power App SDK object."""
    app = MagicMock()
    app.id = app_id
    app.name = name
    app.display_name = display_name
    return app


def _mock_client(apps: list | None = None):
    """Build a MagicMock that mimics the SDK call chain for apps.get()."""
    client = MagicMock(spec=PowerPlatformClient)
    result = MagicMock()
    result.value = apps
    by_env = client.sdk.powerapps.environments.by_environment_id.return_value
    by_env.apps.get = AsyncMock(return_value=result)
    return client


@pytest.fixture
def handler_with_apps():
    """Handler whose SDK returns two apps."""
    apps = [
        _fake_app(app_id="app-1", name="App1", display_name="First App"),
        _fake_app(app_id="app-2", name="App2", display_name="Second App"),
    ]
    client = _mock_client(apps)
    return GetAppsFunction(client=client), client


@pytest.fixture
def handler_empty():
    """Handler whose SDK returns no apps."""
    client = _mock_client([])
    return GetAppsFunction(client=client), client


class TestGetAppsInvoke:
    """Tests for the GetAppsFunction invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_returns_apps(self, handler_with_apps):
        handler, client = handler_with_apps
        request = InvokeRequest(
            tok="powerplatform:index:getApps",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        apps_pv = response.return_value["apps"]
        apps = apps_pv.value
        assert len(apps) == 2
        assert apps[0].value["id"].value == "app-1"
        assert apps[0].value["name"].value == "App1"
        assert apps[1].value["id"].value == "app-2"

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler_empty):
        handler, _ = handler_empty
        request = InvokeRequest(
            tok="powerplatform:index:getApps",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        apps_pv = response.return_value["apps"]
        assert len(apps_pv.value) == 0
