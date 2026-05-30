"""Phase 0 proof-of-concept component — validates the bidirectional construct bridge.

This component has **no side-effects** and makes **no API calls**.  It accepts a
string ``label`` input and echoes it as a ``labelOut`` output, proving that the
``PropertyValue ↔ Output`` bridge works end-to-end through the Pulumi engine.

It will be removed once Phase 2 introduces the first real AVM component.
"""

from __future__ import annotations

from typing import Optional

import pulumi

#: Type token registered in the Pulumi engine for this component.
COMPONENT_TYPE = "powerplatform:components:PocComponent"


class PocComponent(pulumi.ComponentResource):
    """Skeletal POC component for validating the Option A+ construct bridge."""

    label_out: pulumi.Output[str]
    """Echo of the ``label`` input — proves round-trip bridge correctness."""

    def __init__(
        self,
        name: str,
        label: pulumi.Input[str],
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(COMPONENT_TYPE, name, {}, opts)
        self.label_out = pulumi.Output.from_input(label)
        self.register_outputs({"labelOut": self.label_out})
