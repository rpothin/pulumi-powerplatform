"""Tests for the bidirectional PropertyValue ↔ Output construct bridge."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pulumi
import pulumi.runtime.mocks as mocks_module
import pulumi.runtime.rpc
import pytest
from pulumi.provider.experimental.property_value import Computed, PropertyValue
from rpothin_powerplatform.construct_bridge import (
    _make_output,
    _python_to_pv,
    pv_to_input,
    resolve_outputs,
)


class _SimpleMocks(mocks_module.Mocks):
    def new_resource(self, args):
        return args.name + "_id", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture(autouse=True)
async def _pulumi_mocks():
    """Install Pulumi runtime mocks inside the test's event loop.

    Must be async so that any asyncio.Future objects created by set_mocks
    (e.g. for the root Stack resource URN) are bound to the same event loop as
    the test coroutine, avoiding "Future attached to a different loop" errors.
    """
    mocks_module.set_mocks(_SimpleMocks(), preview=False)


# ---------------------------------------------------------------------------
# Input direction: pv_to_input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pv_to_input_plain_string():
    """Plain string PV → bare Python string (no Output wrapper)."""
    result = pv_to_input(PropertyValue("hello"))
    assert result == "hello"
    assert not isinstance(result, pulumi.Output)


@pytest.mark.asyncio
async def test_pv_to_input_none():
    """None PV → None (no Output wrapper)."""
    result = pv_to_input(PropertyValue(None))
    assert result is None
    assert not isinstance(result, pulumi.Output)


@pytest.mark.asyncio
async def test_pv_to_input_bool():
    """Bool PV → bare Python bool."""
    assert pv_to_input(PropertyValue(True)) is True
    assert pv_to_input(PropertyValue(False)) is False


@pytest.mark.asyncio
async def test_pv_to_input_secret_string():
    """Secret PV → Output marked secret."""
    result = pv_to_input(PropertyValue("s3cr3t", is_secret=True))
    assert isinstance(result, pulumi.Output)
    value = await result.future(with_unknowns=True)
    is_secret = await result._is_secret
    assert value == "s3cr3t"
    assert is_secret is True


@pytest.mark.asyncio
async def test_pv_to_input_computed():
    """Computed PV (unknown/preview) → Output with is_known=False."""
    result = pv_to_input(PropertyValue(Computed()))
    assert isinstance(result, pulumi.Output)
    is_known = await result._is_known
    assert is_known is False


@pytest.mark.asyncio
async def test_pv_to_input_secret_computed():
    """Secret Computed PV → Output that is both unknown and secret."""
    result = pv_to_input(PropertyValue(Computed(), is_secret=True))
    assert isinstance(result, pulumi.Output)
    is_known = await result._is_known
    is_secret = await result._is_secret
    assert is_known is False
    assert is_secret is True


@pytest.mark.asyncio
async def test_pv_to_input_with_dependencies():
    """PV with resource dependencies → Output carrying those deps."""
    dep_urn = "urn:pulumi:stack::proj::powerplatform:index:Environment::my-env"
    result = pv_to_input(
        PropertyValue("val", dependencies=frozenset({dep_urn}))
    )
    assert isinstance(result, pulumi.Output)
    value = await result.future(with_unknowns=True)
    assert value == "val"
    resources = await result._resources
    urns = {await r.urn.future() for r in resources}
    assert dep_urn in urns


@pytest.mark.asyncio
async def test_pv_to_input_plain_map():
    """Plain nested map PV → dict (no Output wrapper)."""
    pv = PropertyValue({"a": PropertyValue("alpha"), "b": PropertyValue("beta")})
    result = pv_to_input(pv)
    assert isinstance(result, dict)
    assert result == {"a": "alpha", "b": "beta"}


@pytest.mark.asyncio
async def test_pv_to_input_secret_map_preserves_top_level_deps():
    """Secret map PV → Output wrapping the dict (top-level deps preserved)."""
    pv = PropertyValue(
        {"x": PropertyValue("value")},
        is_secret=True,
    )
    result = pv_to_input(pv)
    assert isinstance(result, pulumi.Output)
    is_secret = await result._is_secret
    assert is_secret is True
    inner = await result.future(with_unknowns=True)
    # Inner dict has already-resolved values
    assert isinstance(inner, dict)


@pytest.mark.asyncio
async def test_pv_to_input_map_with_dep_gets_output_wrapper():
    """Map PV with top-level URN dependencies → Output wrapper (dep preserved)."""
    dep_urn = "urn:pulumi:stack::proj::powerplatform:index:Environment::e"
    pv = PropertyValue(
        {"k": PropertyValue("v")},
        dependencies=frozenset({dep_urn}),
    )
    result = pv_to_input(pv)
    assert isinstance(result, pulumi.Output)
    resources = await result._resources
    urns = {await r.urn.future() for r in resources}
    assert dep_urn in urns


@pytest.mark.asyncio
async def test_pv_to_input_plain_list():
    """Plain list PV → list (no Output wrapper)."""
    pv = PropertyValue([PropertyValue("a"), PropertyValue("b")])
    result = pv_to_input(pv)
    assert isinstance(result, list)
    assert result == ["a", "b"]


@pytest.mark.asyncio
async def test_pv_to_input_secret_list_gets_output_wrapper():
    """Secret list PV → Output wrapping the list."""
    pv = PropertyValue([PropertyValue("item")], is_secret=True)
    result = pv_to_input(pv)
    assert isinstance(result, pulumi.Output)
    is_secret = await result._is_secret
    assert is_secret is True


# ---------------------------------------------------------------------------
# Output direction: resolve_outputs / _python_to_pv
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_outputs_plain_output():
    """Plain Output[str] → PropertyValue with same string value."""
    state = await resolve_outputs({"out": pulumi.Output.from_input("world")})
    pv = state["out"]
    assert pv.value == "world"
    assert pv.is_secret is False


@pytest.mark.asyncio
async def test_resolve_outputs_secret_output():
    """Secret Output → PropertyValue with is_secret=True."""
    secret = pulumi.Output.secret("top_secret")
    state = await resolve_outputs({"out": secret})
    pv = state["out"]
    assert pv.value == "top_secret"
    assert pv.is_secret is True


@pytest.mark.asyncio
async def test_resolve_outputs_unknown_output():
    """Unknown Output (preview) → PropertyValue wrapping the wire UNKNOWN sentinel.

    Regression test for a bug where `_output_to_pv` returned
    `PropertyValue(Computed(), ...)`. `PropertyValue(Computed()).marshal()`
    unconditionally raises `ValueError: Unsupported value type: ... Computed`
    in the installed (and current upstream) Pulumi SDK, so *every*
    `pulumi preview`/dry-run pass crashed for a component with an unknown
    output. The fix uses the classic `pulumi.runtime.rpc.UNKNOWN` sentinel
    string instead, which marshals successfully — asserted below by actually
    calling `.marshal()`, not just inspecting `.value`.
    """
    unknown_out = _make_output(
        pulumi.UNKNOWN,
        is_known=False,
        is_secret=False,
        dep_urns=frozenset(),
    )
    state = await resolve_outputs({"out": unknown_out})
    pv = state["out"]
    assert not isinstance(pv.value, Computed)
    assert pv.value == pulumi.runtime.rpc.UNKNOWN

    # The actual regression: this must not raise.
    marshaled = pv.marshal()
    assert marshaled.string_value == pulumi.runtime.rpc.UNKNOWN


@pytest.mark.asyncio
async def test_resolve_outputs_unknown_output_secret_and_deps_marshal():
    """Unknown + secret + dependency-carrying output marshals successfully too."""
    dep_urn = "urn:pulumi:stack::proj::powerplatform:index:Environment::dep-env"
    unknown_out = _make_output(
        pulumi.UNKNOWN,
        is_known=False,
        is_secret=True,
        dep_urns=frozenset({dep_urn}),
    )
    state = await resolve_outputs({"out": unknown_out})
    pv = state["out"]
    assert pv.is_secret is True
    assert dep_urn in pv.dependencies

    # Must not raise despite carrying secret + dependency metadata alongside
    # the unknown sentinel.
    marshaled = pv.marshal()
    assert marshaled.HasField("struct_value")


@pytest.mark.asyncio
async def test_resolve_outputs_plain_value():
    """Plain Python value → PropertyValue wrapping that value."""
    state = await resolve_outputs({"out": "just_a_string"})
    pv = state["out"]
    assert pv.value == "just_a_string"
    assert pv.is_secret is False


@pytest.mark.asyncio
async def test_resolve_outputs_integer_becomes_float():
    """Integer plain value → float in PropertyValue (Pulumi number representation)."""
    state = await resolve_outputs({"out": 42})
    pv = state["out"]
    assert pv.value == 42.0
    assert isinstance(pv.value, float)


@pytest.mark.asyncio
async def test_resolve_outputs_dict_value():
    """Plain dict value → PropertyValue wrapping Mapping[str, PropertyValue]."""
    state = await resolve_outputs({"out": {"nested": "value"}})
    pv = state["out"]
    # PropertyValue stores Mapping as MappingProxyType, so check for Mapping ABC
    assert isinstance(pv.value, Mapping)
    inner = pv.value["nested"]
    assert isinstance(inner, PropertyValue)
    assert inner.value == "value"


@pytest.mark.asyncio
async def test_resolve_outputs_output_with_dependency():
    """Output carrying a resource dep → PropertyValue with URN dependencies."""
    dep_urn = "urn:pulumi:stack::proj::powerplatform:index:Environment::dep-env"
    out = _make_output("v", is_known=True, is_secret=False, dep_urns=frozenset({dep_urn}))
    state = await resolve_outputs({"out": out})
    pv = state["out"]
    assert dep_urn in pv.dependencies


# ---------------------------------------------------------------------------
# Round-trip tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_round_trip_plain():
    """Plain string survives pv_to_input → resolve_outputs → same value."""
    pv_in = PropertyValue("unchanged")
    result = pv_to_input(pv_in)
    state = await resolve_outputs({"v": result})
    assert state["v"].value == "unchanged"


@pytest.mark.asyncio
async def test_round_trip_secret():
    """Secret PV → Output → PV preserves is_secret=True."""
    pv_in = PropertyValue("shh", is_secret=True)
    out = pv_to_input(pv_in)
    state = await resolve_outputs({"v": out})
    assert state["v"].is_secret is True
    assert state["v"].value == "shh"


@pytest.mark.asyncio
async def test_round_trip_unknown():
    """Computed PV (input) → unknown Output → resolved output PV marshals fine.

    The *input* direction still legitimately produces `Computed()` PVs (that
    part of the SDK's type system works fine — only `.marshal()` is broken).
    What matters for this regression is that once such a value round-trips
    through an Output and back out via `resolve_outputs` (the *output*
    direction), the result no longer carries a bare `Computed()` and marshals
    successfully.
    """
    pv_in = PropertyValue(Computed())
    out = pv_to_input(pv_in)
    state = await resolve_outputs({"v": out})
    pv_out = state["v"]
    assert not isinstance(pv_out.value, Computed)
    marshaled = pv_out.marshal()
    assert marshaled.string_value == pulumi.runtime.rpc.UNKNOWN


@pytest.mark.asyncio
async def test_python_to_pv_none():
    pv = _python_to_pv(None)
    assert pv.value is None


@pytest.mark.asyncio
async def test_python_to_pv_list():
    pv = _python_to_pv(["a", "b"])
    # PropertyValue stores sequences as tuples; check for Sequence ABC
    assert isinstance(pv.value, Sequence) and not isinstance(pv.value, str)
    assert all(isinstance(x, PropertyValue) for x in pv.value)
