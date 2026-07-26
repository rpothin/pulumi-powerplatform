"""End-to-end preview-mode regression test for the `Computed` marshal bug.

Kept in its own module (rather than added to ``test_provider_construct.py``)
because it needs Pulumi runtime mocks installed with ``preview=True`` for the
*entire* module. Calling ``pulumi.runtime.mocks.set_mocks()`` a second time
within an already-mocked test (e.g. layering on top of an autouse
``preview=False`` fixture from another module) does not reliably flip
``pulumi.runtime.settings.is_dry_run()`` for resource registration purposes,
so a dedicated module with a single ``set_mocks(..., preview=True)`` call is
the reliable way to simulate a real `pulumi preview`/dry-run pass.
"""

from __future__ import annotations

import pulumi
import pulumi.runtime.mocks as mocks_module
import pulumi.runtime.rpc
import pulumi.runtime.settings
import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import ConstructRequest
from rpothin_powerplatform.components.res_environment import COMPONENT_TYPE
from rpothin_powerplatform.provider import PowerPlatformProvider


class _PreviewMocks(mocks_module.Mocks):
    def new_resource(self, args):
        # Real custom-resource providers return an empty ID during preview
        # (the resource doesn't exist yet). Pulumi's runtime treats an empty
        # ID string as "unknown" for the resource's `id` output — see
        # `resource.py`: `is_known = bool(resp.id)` — so this mirrors real
        # provider behavior instead of a mock always returning a concrete ID.
        return "", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture(autouse=True)
async def _pulumi_mocks():
    """Install Pulumi runtime mocks in preview (dry-run) mode."""
    mocks_module.set_mocks(_PreviewMocks(), preview=True)


@pytest.fixture
def provider():
    return PowerPlatformProvider()


@pytest.mark.asyncio
async def test_construct_preview_state_marshals_without_error(provider):
    """Full ``ConstructRequest`` → ``provider.construct()`` round trip in preview mode.

    During `pulumi preview`/the dry-run pass of `pulumi up`, the child
    resource's `id` (and outputs derived from it, e.g. `resourceId`) are
    always unknown. Before the fix, `resolve_outputs()`/`_output_to_pv()`
    represented that as `PropertyValue(Computed(), ...)`, which crashes when
    the real provider server marshals `ConstructResponse.state` via
    `PropertyValue.marshal_map()` (see the installed `pulumi` package's
    `provider/experimental/server.py`, `_construct_response`).

    `test_construct_dispatches_res_environment` in `test_provider_construct.py`
    does NOT exercise this: it never calls `.marshal()` on the response
    state, so it could not have caught this bug before it shipped. This test
    reproduces that exact marshal step end-to-end.
    """
    assert pulumi.runtime.settings.is_dry_run() is True

    request = ConstructRequest(
        resource_type=COMPONENT_TYPE,
        name="preview-environment",
        inputs={
            "displayName": PropertyValue("Preview Environment"),
            "location": PropertyValue("unitedstates"),
        },
        options=pulumi.ResourceOptions(),
    )
    response = await provider.construct(request)

    # The actual regression: marshaling the state must not raise.
    marshaled = PropertyValue.marshal_map(response.state)
    assert "resourceId" in marshaled.fields

    # `resourceId` is derived from the child `Environment` resource's `.id`,
    # which is unknown during preview *and* carries that resource as a
    # dependency. Because `dependencies` is non-empty, `PropertyValue.marshal()`
    # wraps the value in the protocol's "output value" struct (signature key +
    # `value`/`dependencies`/`secret` fields) rather than emitting a bare
    # `string_value` -- see `property_value.py`'s `marshal()`: `if
    # self.dependencies: ...`. The unknown sentinel lives at the nested
    # `value` field either way; unwrap it before comparing.
    resource_id_field = marshaled.fields["resourceId"]
    assert resource_id_field.WhichOneof("kind") == "struct_value"
    inner_value = resource_id_field.struct_value.fields["value"]
    assert inner_value.string_value == pulumi.runtime.rpc.UNKNOWN
