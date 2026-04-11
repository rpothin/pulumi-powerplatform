"""Tests for the getEnvironments function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.provider import InvokeRequest
from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.functions.get_environments import GetEnvironmentsFunction


def _fake_env(*, env_id: str = "env-1", display_name: str = "Dev") -> MagicMock:
    """Return a fake environment SDK object."""
    env = MagicMock()
    env.id = env_id
    env.display_name = display_name
    env.domain_name = "org123"
    env.state = "Ready"
    env.type = "Sandbox"
    env.url = "https://org123.crm.dynamics.com"
    env.geo = "unitedstates"
    env.azure_region = "westus"
    env.security_group_id = None
    env.tenant_id = "tenant-1"
    env.environment_group_id = None
    env.dataverse_id = "dv-1"
    env.version = "9.2"
    return env


def _mock_client(envs: list | None = None) -> MagicMock:
    """Build a MagicMock that mimics the SDK call chain for environments.get()."""
    client = MagicMock(spec=PowerPlatformClient)
    result = MagicMock()
    result.value = envs
    client.sdk.environmentmanagement.environments.get = AsyncMock(return_value=result)
    return client


@pytest.fixture
def handler_with_envs():
    """Handler whose SDK returns two environments."""
    envs = [_fake_env(env_id="env-1", display_name="Dev"), _fake_env(env_id="env-2", display_name="Prod")]
    client = _mock_client(envs)
    return GetEnvironmentsFunction(client=client), client


@pytest.fixture
def handler_empty():
    """Handler whose SDK returns no environments."""
    client = _mock_client([])
    return GetEnvironmentsFunction(client=client), client


class TestGetEnvironmentsInvoke:
    """Tests for the GetEnvironmentsFunction invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_returns_environments(self, handler_with_envs):
        handler, client = handler_with_envs
        request = InvokeRequest(tok="powerplatform:index:getEnvironments", args={})
        response = await handler.invoke(request)

        envs_pv = response.return_value["environments"]
        envs = envs_pv.value
        assert len(envs) == 2
        assert envs[0].value["id"].value == "env-1"
        assert envs[0].value["displayName"].value == "Dev"
        assert envs[1].value["id"].value == "env-2"
        assert envs[1].value["displayName"].value == "Prod"
        client.sdk.environmentmanagement.environments.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler_empty):
        handler, _ = handler_empty
        request = InvokeRequest(tok="powerplatform:index:getEnvironments", args={})
        response = await handler.invoke(request)

        envs_pv = response.return_value["environments"]
        assert len(envs_pv.value) == 0
