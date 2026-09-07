"""Tests for the getEnvironments function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from kiota_abstractions.api_error import APIError
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_environments import GetEnvironmentsFunction
from rpothin_powerplatform.utils import HttpError


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
    client.raw.request = AsyncMock()
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

    @pytest.mark.asyncio
    async def test_invoke_passes_request_configuration(self, handler_with_envs):
        """get() must be called with a request_configuration kwarg (carries api-version)."""
        handler, client = handler_with_envs
        request = InvokeRequest(tok="powerplatform:index:getEnvironments", args={})
        await handler.invoke(request)

        get_mock = client.sdk.environmentmanagement.environments.get
        get_mock.assert_awaited_once()
        call_kwargs = get_mock.await_args.kwargs
        assert "request_configuration" in call_kwargs, "api-version must be passed via request_configuration"

    @pytest.mark.asyncio
    async def test_api_error_raises_runtime_error(self):
        """APIError from the SDK must be re-raised as RuntimeError with status and message."""
        client = MagicMock(spec=PowerPlatformClient)
        api_err = APIError(message="Bad Request", response_status_code=400)
        client.sdk.environmentmanagement.environments.get = AsyncMock(side_effect=api_err)

        handler = GetEnvironmentsFunction(client=client)
        request = InvokeRequest(tok="powerplatform:index:getEnvironments", args={})

        with pytest.raises(RuntimeError, match="400") as exc_info:
            await handler.invoke(request)
        assert exc_info.value.__cause__ is api_err

    @pytest.mark.asyncio
    async def test_unauthorized_app_falls_back_to_bap(self):
        client = _mock_client()
        api_err = APIError(message="Forbidden", response_status_code=403)
        api_err.response_body = {
            "code": "ForbiddenAccess",
            "message": "Caller is not an authorized app. Tenant 'tenant-1'.",
        }
        client.sdk.environmentmanagement.environments.get.side_effect = api_err
        client.raw.request.return_value = {
            "value": [
                {
                    "id": "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/env-1",
                    "location": "unitedstates",
                    "properties": {
                        "displayName": "Dev",
                        "environmentSku": "Sandbox",
                        "states": "Ready",
                        "linkedEnvironmentMetadata": {
                            "instanceUrl": "https://org123.crm.dynamics.com",
                            "tenantId": "tenant-1",
                        },
                    },
                }
            ]
        }

        response = await GetEnvironmentsFunction(client).invoke(
            InvokeRequest(
                tok="powerplatform:index:getEnvironments",
                args={"filter": PropertyValue("state eq 'Ready'"), "top": PropertyValue("1")},
            )
        )

        env = response.return_value["environments"].value[0].value
        assert env["id"].value.endswith("/env-1")
        assert env["displayName"].value == "Dev"
        assert env["type"].value == "Sandbox"
        assert env["url"].value == "https://org123.crm.dynamics.com"
        client.raw.request.assert_awaited_once_with(
            "GET",
            "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments",
            api_version="2021-04-01",
            query_params={"$filter": "state eq 'Ready'", "$top": 1},
        )

    @pytest.mark.asyncio
    async def test_other_api_error_does_not_fall_back(self):
        client = _mock_client()
        api_err = APIError(message="Forbidden", response_status_code=403)
        api_err.response_body = {"code": "ForbiddenAccess", "message": "Access denied"}
        client.sdk.environmentmanagement.environments.get.side_effect = api_err

        with pytest.raises(RuntimeError, match="403"):
            await GetEnvironmentsFunction(client).invoke(
                InvokeRequest(tok="powerplatform:index:getEnvironments", args={})
            )

        client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_bap_failure_includes_both_errors(self):
        client = _mock_client()
        api_err = APIError(message="Forbidden", response_status_code=403)
        api_err.response_body = {
            "code": "ForbiddenAccess",
            "message": "Caller is not an authorized app",
        }
        client.sdk.environmentmanagement.environments.get.side_effect = api_err
        client.raw.request.side_effect = HttpError(500, "BAP unavailable")

        with pytest.raises(RuntimeError, match="BAP fallback failed.*BAP unavailable"):
            await GetEnvironmentsFunction(client).invoke(
                InvokeRequest(tok="powerplatform:index:getEnvironments", args={})
            )
