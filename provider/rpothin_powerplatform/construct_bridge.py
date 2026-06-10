"""Bidirectional bridge between PropertyValue and pulumi.Output/Python values.

Input direction (pv_to_input):
    PropertyValue → Python value or pulumi.Output
    Used to pass ConstructRequest.inputs to ComponentResource constructors.
    Preserves secret, unknown (Computed), and dependency metadata.

Output direction (resolve_outputs):
    dict[str, Output | Any] → dict[str, PropertyValue]
    Used to build ConstructResponse.state from component outputs.

NOTE — Phase 0 scope: nested Output structures (e.g. Output[dict]) are not
traversed recursively during output resolution.  Fully-resolved composite values
and scalar Outputs are handled correctly.  Full nested-Output support is deferred
to Phase 3+.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import pulumi
import pulumi.resource
from pulumi.provider.experimental.property_value import Computed, PropertyValue

# ---------------------------------------------------------------------------
# Input direction: PropertyValue → Python / pulumi.Output
# ---------------------------------------------------------------------------


def pv_to_input(pv: PropertyValue) -> Any:
    """Convert a PropertyValue to a Python value suitable for ComponentResource inputs.

    Creates a ``pulumi.Output`` when the value is secret, unknown, or carries
    resource dependencies, preserving that metadata for the engine.
    """
    v = pv.value
    deps = pv.dependencies  # frozenset[str] of resource URN strings
    needs_output = pv.is_secret or bool(deps)

    if isinstance(v, Computed):
        # Unknown/computed value during preview
        return _make_output(
            pulumi.UNKNOWN,
            is_known=False,
            is_secret=pv.is_secret,
            dep_urns=deps,
        )

    if isinstance(v, Mapping):
        # Recursively convert nested PropertyValues; preserve top-level deps
        converted: Any = {k: pv_to_input(inner) for k, inner in v.items()}
        if needs_output:
            return _make_output(converted, is_known=True, is_secret=pv.is_secret, dep_urns=deps)
        return converted

    if isinstance(v, Sequence) and not isinstance(v, str):
        converted = [pv_to_input(item) for item in v]
        if needs_output:
            return _make_output(converted, is_known=True, is_secret=pv.is_secret, dep_urns=deps)
        return converted

    # Scalar: None, bool, float, str, Asset, Archive, ResourceReference
    if needs_output:
        return _make_output(v, is_known=True, is_secret=pv.is_secret, dep_urns=deps)
    return v


def _make_output(
    value: Any,
    *,
    is_known: bool,
    is_secret: bool,
    dep_urns: frozenset[str],
) -> pulumi.Output:
    """Build a ``pulumi.Output`` from already-resolved components.

    Must be called from within an async context (the ``construct`` method is
    always async, so there is always a running event loop).
    """
    resources: set[pulumi.resource.Resource] = {
        pulumi.resource.DependencyResource(urn) for urn in dep_urns
    }
    fut: asyncio.Future = asyncio.Future()
    fut.set_result(value)
    return pulumi.Output(
        resources=resources,
        future=fut,
        is_known=_done_future(is_known),
        is_secret=_done_future(is_secret),
    )


def _done_future(value: Any) -> asyncio.Future:
    f: asyncio.Future = asyncio.Future()
    f.set_result(value)
    return f


# ---------------------------------------------------------------------------
# Output direction: pulumi.Output / Python → PropertyValue
# ---------------------------------------------------------------------------


async def resolve_outputs(outputs: dict[str, Any]) -> dict[str, PropertyValue]:
    """Resolve component outputs to a ``dict[str, PropertyValue]``.

    Each value may be a ``pulumi.Output`` (awaited) or a plain Python value.
    Called inside the ``construct`` method after the ComponentResource is created.
    """
    result: dict[str, PropertyValue] = {}
    for key, val in outputs.items():
        if isinstance(val, pulumi.Output):
            result[key] = await _output_to_pv(val)
        else:
            result[key] = _python_to_pv(val)
    return result


async def _output_to_pv(output: pulumi.Output) -> PropertyValue:
    """Await a ``pulumi.Output`` and represent it as a ``PropertyValue``.

    .. note::
        ``output._is_known``, ``output._is_secret``, and ``output._resources``
        are **private** Pulumi internals with no public equivalents as of Pulumi
        ≤ 3.x.  ``output.future(with_unknowns=True)`` is the only public path
        to the raw value including the ``UNKNOWN`` sentinel.  These attributes
        could change in any minor release without notice — re-evaluate whenever
        the Pulumi SDK dependency is upgraded (see ``pyproject.toml`` pin comment).
    """
    value = await output.future(with_unknowns=True)
    is_known: bool = await output._is_known
    is_secret: bool = await output._is_secret
    resources: set[pulumi.resource.Resource] = await output._resources

    urn_futures = [r.urn.future() for r in resources]
    if urn_futures:
        resolved = await asyncio.gather(*urn_futures)
        urns: frozenset[str] = frozenset(u for u in resolved if u is not None)
    else:
        urns = frozenset()

    if not is_known:
        return PropertyValue(Computed(), is_secret=is_secret, dependencies=urns)

    return PropertyValue(
        _python_value_to_pv_value(value),
        is_secret=is_secret,
        dependencies=urns,
    )


def _python_to_pv(value: Any) -> PropertyValue:
    """Wrap a plain Python value (not an Output) in a ``PropertyValue``."""
    return PropertyValue(_python_value_to_pv_value(value))


def _python_value_to_pv_value(value: Any) -> Any:
    """Recursively convert a plain Python value to ``PythonValue`` (PropertyValue's inner type).

    - ``dict``  → ``Mapping[str, PropertyValue]``
    - ``list``  → ``Sequence[PropertyValue]``
    - ``int``   → ``float``  (Pulumi represents all numbers as float)
    - Others    → unchanged (None, bool, float, str, Asset, Archive …)
    """
    if value is None or isinstance(value, (bool, str, float)):
        return value
    if isinstance(value, int):
        return float(value)
    if isinstance(value, Mapping):
        return {k: PropertyValue(_python_value_to_pv_value(v)) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [PropertyValue(_python_value_to_pv_value(item)) for item in value]
    # Asset, Archive, ResourceReference, etc.
    return value
