"""Phase 0 / Phase 2 proof-of-concept component — validates the Option A+ construct bridge.

This component has **no side-effects** and makes **no API calls**.  It is kept as
a scaffold through Phase 2 to exercise the schema-merge pipeline and construct
dispatch registry end-to-end.  It will be replaced by real AVM components
(``ResEnvironment``, etc.) starting in Phase 3.
"""

from dataclasses import dataclass
from typing import Optional

import pulumi

from ._base import COMPONENT_TOKEN_PREFIX, ComponentArgs, register_component, register_construct

#: Type token registered in the Pulumi engine for this component.
COMPONENT_TYPE = f"{COMPONENT_TOKEN_PREFIX}PocComponent"


@dataclass(kw_only=True)
class PocComponentArgs(ComponentArgs):
    """Input arguments for :class:`PocComponent`.

    ``label`` is optional so that the bridge can be tested with a ``None``
    input (mirrors how an unknown/missing input arrives during ``preview``).
    """

    label: Optional[str] = None
    """String echoed back as ``labelOut``.  Intentionally optional for POC purposes."""


@register_component
class PocComponent(pulumi.ComponentResource):
    """Phase 0 / Phase 2 POC component — validates the bidirectional construct bridge.

    Accepts a ``label`` input and echoes it as ``labelOut``.
    Also exposes a placeholder ``resourceId`` output following AVM conventions.
    """

    label_out: pulumi.Output[str]
    """Echo of the ``label`` input — proves round-trip bridge correctness."""

    resource_id: pulumi.Output[str]
    """Placeholder resource ID following AVM output conventions."""

    def __init__(
        self,
        name: str,
        args: PocComponentArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(COMPONENT_TYPE, name, {}, opts)
        self.label_out = pulumi.Output.from_input(args.label)
        self.resource_id = pulumi.Output.from_input(f"poc/{name}")
        self.register_outputs({"labelOut": self.label_out, "resourceId": self.resource_id})


@register_construct(COMPONENT_TYPE)
async def _construct_poc(
    name: str,
    inputs: dict,
    opts: Optional[pulumi.ResourceOptions],
) -> object:
    """Async factory for :class:`PocComponent` — called by the provider's ``construct`` dispatch."""
    # Lazy imports so this module can be loaded in isolation (e.g. by merge-schema.py)
    # without pulling in provider side-effects.
    from pulumi.provider.experimental.property_value import PropertyValue  # noqa: PLC0415
    from pulumi.provider.experimental.provider import ConstructResponse  # noqa: PLC0415

    from ..construct_bridge import pv_to_input, resolve_outputs  # noqa: PLC0415

    label = pv_to_input(inputs.get("label", PropertyValue(None)))
    enable_telemetry = pv_to_input(inputs.get("enableTelemetry", PropertyValue(None)))
    args = PocComponentArgs(label=label, enable_telemetry=enable_telemetry)

    comp = PocComponent(name, args=args, opts=opts)
    urn = await comp.urn.future()
    state = await resolve_outputs({"labelOut": comp.label_out, "resourceId": comp.resource_id})
    return ConstructResponse(urn=urn, state=state, state_dependencies={})
