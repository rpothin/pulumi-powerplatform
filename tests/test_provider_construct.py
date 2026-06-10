"""Tests for the provider's component construct dispatch."""

from __future__ import annotations

import pulumi
import pulumi.runtime.mocks as mocks_module
import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import ConstructRequest
from rpothin_powerplatform.components.res_environment import COMPONENT_TYPE
from rpothin_powerplatform.provider import PowerPlatformProvider


class _SimpleMocks(mocks_module.Mocks):
    def new_resource(self, args):
        return args.name + "_id", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture(autouse=True)
async def _pulumi_mocks():
    """Install Pulumi runtime mocks inside the test's event loop."""
    mocks_module.set_mocks(_SimpleMocks(), preview=False)


@pytest.fixture
def provider():
    return PowerPlatformProvider()


@pytest.mark.asyncio
async def test_construct_dispatches_res_environment(provider):
    """construct() returns a ConstructResponse for ResEnvironment."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="my-environment",
        inputs={
            "displayName": PropertyValue("Dispatch Environment"),
            "location": PropertyValue("unitedstates"),
        },
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)

    assert response.urn is not None
    assert isinstance(response.urn, str)
    assert len(response.urn) > 0
    assert "resourceId" in response.state
    assert response.state["environmentDisplayName"].value == "Dispatch Environment"


@pytest.mark.asyncio
async def test_construct_raises_for_unknown_type(provider):
    """construct() raises NotImplementedError for an unknown resource_type."""
    request = ConstructRequest(
        resource_type="powerplatform:components:DoesNotExist",
        name="x",
        inputs={},
        options=pulumi.ResourceOptions(),
    )
    with pytest.raises(NotImplementedError, match="DoesNotExist"):
        await provider.construct(request)


@pytest.mark.asyncio
async def test_construct_state_dependencies_empty(provider):
    """ConstructResponse.state_dependencies is always {}."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="deps-environment",
        inputs={
            "displayName": PropertyValue("Dependencies Environment"),
            "location": PropertyValue("unitedstates"),
        },
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)
    assert response.state_dependencies == {}
