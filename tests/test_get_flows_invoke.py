"""Tests for the getFlows function handler — invoke with mocked SDK."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from kiota_abstractions.api_error import APIError
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_flows import GetFlowsFunction


def _fake_flow(*, flow_id: str = "flow-1", name: str = "MyFlow", display_name: str = "My Cloud Flow"):
    """Return a fake Cloud Flow SDK object."""
    flow = MagicMock()
    flow.id = flow_id
    flow.name = name
    flow.display_name = display_name
    return flow


def _mock_client(flows: list | None = None):
    """Build a MagicMock that mimics the SDK call chain for cloud_flows.get()."""
    client = MagicMock(spec=PowerPlatformClient)
    result = MagicMock()
    result.value = flows
    by_env = client.sdk.powerautomate.environments.by_environment_id.return_value
    by_env.cloud_flows.get = AsyncMock(return_value=result)
    return client


@pytest.fixture
def handler_with_flows():
    """Handler whose SDK returns two flows."""
    flows = [
        _fake_flow(flow_id="flow-1", name="Flow1", display_name="First Flow"),
        _fake_flow(flow_id="flow-2", name="Flow2", display_name="Second Flow"),
    ]
    client = _mock_client(flows)
    return GetFlowsFunction(client=client), client


@pytest.fixture
def handler_empty():
    """Handler whose SDK returns no flows."""
    client = _mock_client([])
    return GetFlowsFunction(client=client), client


class TestGetFlowsInvoke:
    """Tests for the GetFlowsFunction invoke method."""

    @pytest.mark.asyncio
    async def test_invoke_returns_flows(self, handler_with_flows):
        handler, client = handler_with_flows
        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        flows_pv = response.return_value["flows"]
        flows = flows_pv.value
        assert len(flows) == 2
        assert flows[0].value["id"].value == "flow-1"
        assert flows[0].value["name"].value == "Flow1"
        assert flows[1].value["id"].value == "flow-2"

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler_empty):
        handler, _ = handler_empty
        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue("env-1")},
        )
        response = await handler.invoke(request)

        flows_pv = response.return_value["flows"]
        assert len(flows_pv.value) == 0

    @pytest.mark.asyncio
    async def test_invoke_passes_request_configuration(self, handler_with_flows):
        """get() must be called with a request_configuration kwarg (carries api-version)."""
        handler, client = handler_with_flows
        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue("env-1")},
        )
        await handler.invoke(request)

        by_env = client.sdk.powerautomate.environments.by_environment_id.return_value
        by_env.cloud_flows.get.assert_awaited_once()
        call_kwargs = by_env.cloud_flows.get.await_args.kwargs
        assert "request_configuration" in call_kwargs, "api-version must be passed via request_configuration"

    @pytest.mark.asyncio
    async def test_api_error_raises_runtime_error(self):
        """APIError from the SDK must be re-raised as RuntimeError with status and message."""
        client = MagicMock(spec=PowerPlatformClient)
        api_err = APIError(message="Bad Request", response_status_code=400)
        by_env = client.sdk.powerautomate.environments.by_environment_id.return_value
        by_env.cloud_flows.get = AsyncMock(side_effect=api_err)

        handler = GetFlowsFunction(client=client)
        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue("env-1")},
        )

        with pytest.raises(RuntimeError, match="400") as exc_info:
            await handler.invoke(request)
        assert exc_info.value.__cause__ is api_err
