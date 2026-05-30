"""Tests for the PocComponent and the provider's construct dispatch."""

from __future__ import annotations

import pulumi
import pulumi.runtime.mocks as mocks_module
import pytest
from pulumi.provider.experimental.property_value import Computed, PropertyValue
from pulumi.provider.experimental.provider import ConstructRequest
from rpothin_powerplatform.components.poc_component import COMPONENT_TYPE, PocComponent
from rpothin_powerplatform.construct_bridge import _make_output
from rpothin_powerplatform.provider import PowerPlatformProvider


class _SimpleMocks(mocks_module.Mocks):
    def new_resource(self, args):
        return args.name + "_id", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture(autouse=True)
async def _pulumi_mocks():
    """Install Pulumi runtime mocks inside the test's event loop.

    Must be async so that any asyncio.Future objects created by set_mocks
    are bound to the same event loop as the test, avoiding cross-loop errors.
    """
    mocks_module.set_mocks(_SimpleMocks(), preview=False)


@pytest.fixture
def provider():
    return PowerPlatformProvider()


# ---------------------------------------------------------------------------
# PocComponent unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_poc_component_echoes_label():
    """PocComponent.label_out resolves to the string passed as label."""
    comp = PocComponent("test-poc", label="echo-me")
    result = await comp.label_out.future(with_unknowns=True)
    assert result == "echo-me"


@pytest.mark.asyncio
async def test_poc_component_secret_label():
    """Secret Output input → label_out is also secret."""
    secret_input = pulumi.Output.secret("my-secret")
    comp = PocComponent("test-poc", label=secret_input)
    is_secret = await comp.label_out._is_secret
    assert is_secret is True


@pytest.mark.asyncio
async def test_poc_component_unknown_label():
    """Unknown input (preview) → label_out is unknown."""
    unknown_input = _make_output(
        pulumi.UNKNOWN,
        is_known=False,
        is_secret=False,
        dep_urns=frozenset(),
    )
    comp = PocComponent("test-poc", label=unknown_input)
    value = await comp.label_out.future(with_unknowns=True)
    # When is_known is False the value is the UNKNOWN sentinel
    assert value is pulumi.UNKNOWN or value is None or not await comp.label_out._is_known


@pytest.mark.asyncio
async def test_poc_component_type_token():
    """COMPONENT_TYPE constant matches the expected token."""
    assert COMPONENT_TYPE == "powerplatform:components:PocComponent"


# ---------------------------------------------------------------------------
# Provider.construct dispatch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_construct_dispatches_poc_component(provider):
    """construct() returns a ConstructResponse with URN and labelOut for PocComponent."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="my-poc",
        inputs={"label": PropertyValue("dispatch-test")},
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)

    assert response.urn is not None
    assert isinstance(response.urn, str)
    assert len(response.urn) > 0
    assert "labelOut" in response.state
    label_pv = response.state["labelOut"]
    assert isinstance(label_pv, PropertyValue)
    assert label_pv.value == "dispatch-test"


@pytest.mark.asyncio
async def test_construct_secret_input_propagates(provider):
    """Secret PV input → labelOut PropertyValue retains is_secret=True."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="poc-secret",
        inputs={"label": PropertyValue("secret-val", is_secret=True)},
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)
    label_pv = response.state["labelOut"]
    assert label_pv.is_secret is True
    assert label_pv.value == "secret-val"


@pytest.mark.asyncio
async def test_construct_unknown_input_propagates(provider):
    """Computed PV input → labelOut PropertyValue is Computed (unknown)."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="poc-unknown",
        inputs={"label": PropertyValue(Computed())},
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)
    label_pv = response.state["labelOut"]
    assert isinstance(label_pv.value, Computed)


@pytest.mark.asyncio
async def test_construct_missing_label_defaults_to_none(provider):
    """Missing label input → construct succeeds with None label_out."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="poc-no-label",
        inputs={},
        options=pulumi.ResourceOptions(),
    )
    # Should not raise; label defaults to None via PropertyValue(None)
    response = await provider.construct(request)
    assert response.urn is not None


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
    """ConstructResponse.state_dependencies is always {} (server recomputes)."""
    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="poc-deps",
        inputs={"label": PropertyValue("v")},
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)
    assert response.state_dependencies == {}
