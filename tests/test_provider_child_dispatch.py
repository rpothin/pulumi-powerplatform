"""Regression tests for dispatching CRUD calls to child resources created
inside a ``remote=True`` ComponentResource's server-side ``construct()`` call.

Background
----------
The four AVM components (``ResEnvironment``, ``ResDlpPolicy``,
``ResTenantSettings``, ``ResDeploymentPipeline``) run their entire
``construct()`` logic server-side, instantiating plain child custom
resources (e.g. ``Environment``, ``DlpPolicy``) via the normal Python
resource classes. When the engine round-trips those child resources back
into this same provider process for Check/Diff/Create/Read/Update/Delete,
``request.type`` (a property derived from the request URN via
``pulumi.provider.experimental.provider._extract_type``, which — unlike
``pulumi.urn._parse_urn`` — does NOT strip the qualified-type prefix) is a
composite, ``$``-joined chain: ``ParentComponentToken$ChildResourceToken``
(e.g. ``powerplatform:components:ResEnvironment$powerplatform:index:Environment``).

``PowerPlatformProvider._handler_for_type`` previously did an exact dict
lookup against plain tokens only, so this composite string always missed,
causing ``NotImplementedError`` on every Create/Update/Delete for these
components' children. These tests pin the fix: ``_handler_for_type`` must
normalize by taking the last ``$``-delimited segment before looking up the
handler, and every RPC method that routes through it (check/diff/create/
read/update/delete) must dispatch correctly for composite tokens.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pulumi.provider.experimental.provider import (
    CheckRequest,
    CheckResponse,
    CreateRequest,
    CreateResponse,
    DeleteRequest,
    DiffRequest,
    DiffResponse,
    ReadRequest,
    ReadResponse,
    UpdateRequest,
    UpdateResponse,
)
from rpothin_powerplatform.provider import PowerPlatformProvider

# The exact composite tokens observed live in CI (pulumi-powerplatform-test,
# workflow run 30140749814) for ResEnvironment and ResDlpPolicy children.
_RES_ENVIRONMENT_CHILD_TYPE = (
    "powerplatform:components:ResEnvironment$powerplatform:index:Environment"
)
_RES_DLP_POLICY_CHILD_TYPE = (
    "powerplatform:components:ResDlpPolicy$powerplatform:index:DlpPolicy"
)
_RES_TENANT_SETTINGS_CHILD_TYPE = (
    "powerplatform:components:ResTenantSettings$powerplatform:index:TenantSettings"
)
_RES_DEPLOYMENT_PIPELINE_CHILD_TYPE = (
    "powerplatform:components:ResDeploymentPipeline$powerplatform:index:PipelineSharing"
)

_URN_TEMPLATE = "urn:pulumi:test::test::{type}::my-child"


def _urn_for(resource_type: str) -> str:
    return _URN_TEMPLATE.format(type=resource_type)


@pytest.fixture
def provider() -> PowerPlatformProvider:
    """A provider instance with mocked-out resource handlers (no live client)."""
    p = PowerPlatformProvider()
    p._environment = AsyncMock()
    p._dlp_policy = AsyncMock()
    p._tenant_settings = AsyncMock()
    p._pipeline_sharing = AsyncMock()
    return p


class TestHandlerForTypeNormalization:
    """Unit tests for the composite-token normalization in _handler_for_type."""

    def test_plain_token_still_resolves(self, provider):
        """Plain, non-composite tokens continue to resolve as before."""
        assert provider._handler_for_type("powerplatform:index:Environment") is provider._environment
        assert provider._handler_for_type("powerplatform:index:DlpPolicy") is provider._dlp_policy

    def test_composite_res_environment_child_resolves(self, provider):
        """The exact composite token observed in CI resolves to the Environment handler."""
        handler = provider._handler_for_type(_RES_ENVIRONMENT_CHILD_TYPE)
        assert handler is provider._environment

    def test_composite_res_dlp_policy_child_resolves(self, provider):
        """The exact composite token observed in CI resolves to the DlpPolicy handler."""
        handler = provider._handler_for_type(_RES_DLP_POLICY_CHILD_TYPE)
        assert handler is provider._dlp_policy

    def test_composite_res_tenant_settings_child_resolves(self, provider):
        handler = provider._handler_for_type(_RES_TENANT_SETTINGS_CHILD_TYPE)
        assert handler is provider._tenant_settings

    def test_composite_res_deployment_pipeline_child_resolves(self, provider):
        handler = provider._handler_for_type(_RES_DEPLOYMENT_PIPELINE_CHILD_TYPE)
        assert handler is provider._pipeline_sharing

    def test_unknown_composite_child_still_returns_none(self, provider):
        """A composite token whose child segment is unknown still resolves to None."""
        unknown = "powerplatform:components:ResEnvironment$powerplatform:index:DoesNotExist"
        assert provider._handler_for_type(unknown) is None

    def test_deeply_nested_composite_uses_last_segment(self, provider):
        """If multiple '$' segments ever appear, only the last (actual child type) matters."""
        nested = "powerplatform:components:Outer$powerplatform:components:Inner$powerplatform:index:Environment"
        assert provider._handler_for_type(nested) is provider._environment


class TestCreateDispatchForCompositeTokens:
    """create() must not raise NotImplementedError for composite child tokens."""

    @pytest.mark.asyncio
    async def test_create_dispatches_res_environment_child(self, provider):
        provider._environment.create.return_value = CreateResponse(resource_id="env-1", properties={})
        request = CreateRequest(
            urn=_urn_for(_RES_ENVIRONMENT_CHILD_TYPE),
            properties={},
            timeout=300,
            preview=False,
        )
        response = await provider.create(request)
        provider._environment.create.assert_awaited_once_with(request)
        assert response.resource_id == "env-1"

    @pytest.mark.asyncio
    async def test_create_dispatches_res_dlp_policy_child(self, provider):
        provider._dlp_policy.create.return_value = CreateResponse(resource_id="dlp-1", properties={})
        request = CreateRequest(
            urn=_urn_for(_RES_DLP_POLICY_CHILD_TYPE),
            properties={},
            timeout=300,
            preview=False,
        )
        response = await provider.create(request)
        provider._dlp_policy.create.assert_awaited_once_with(request)
        assert response.resource_id == "dlp-1"

    @pytest.mark.asyncio
    async def test_create_still_raises_for_truly_unknown_type(self, provider):
        """Sanity check: unrelated/unknown types still raise as before (no over-matching)."""
        request = CreateRequest(
            urn=_urn_for("powerplatform:index:DoesNotExist"),
            properties={},
            timeout=300,
            preview=False,
        )
        with pytest.raises(NotImplementedError, match="DoesNotExist"):
            await provider.create(request)


class TestCheckDiffReadUpdateDeleteDispatchForCompositeTokens:
    """check/diff/read/update/delete must all resolve composite child tokens too."""

    @pytest.mark.asyncio
    async def test_check_dispatches_composite_child(self, provider):
        provider._environment.check.return_value = CheckResponse(inputs={})
        request = CheckRequest(
            urn=_urn_for(_RES_ENVIRONMENT_CHILD_TYPE),
            old_inputs={},
            new_inputs={},
            random_seed=b"",
        )
        await provider.check(request)
        provider._environment.check.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_diff_dispatches_composite_child(self, provider):
        provider._dlp_policy.diff.return_value = DiffResponse()
        request = DiffRequest(
            urn=_urn_for(_RES_DLP_POLICY_CHILD_TYPE),
            resource_id="dlp-1",
            old_state={},
            new_inputs={},
            ignore_changes=[],
        )
        await provider.diff(request)
        provider._dlp_policy.diff.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_read_dispatches_composite_child(self, provider):
        provider._environment.read.return_value = ReadResponse(
            resource_id="env-1", properties={}, inputs={}
        )
        request = ReadRequest(
            urn=_urn_for(_RES_ENVIRONMENT_CHILD_TYPE),
            resource_id="env-1",
            properties={},
            inputs={},
        )
        await provider.read(request)
        provider._environment.read.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_update_dispatches_composite_child(self, provider):
        provider._dlp_policy.update.return_value = UpdateResponse(properties={})
        request = UpdateRequest(
            urn=_urn_for(_RES_DLP_POLICY_CHILD_TYPE),
            resource_id="dlp-1",
            olds={},
            news={},
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        await provider.update(request)
        provider._dlp_policy.update.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_delete_dispatches_composite_child(self, provider):
        provider._environment.delete.return_value = None
        request = DeleteRequest(
            urn=_urn_for(_RES_ENVIRONMENT_CHILD_TYPE),
            resource_id="env-1",
            properties={},
            timeout=300,
        )
        await provider.delete(request)
        provider._environment.delete.assert_awaited_once_with(request)

    @pytest.mark.asyncio
    async def test_update_still_raises_for_truly_unknown_type(self, provider):
        request = UpdateRequest(
            urn=_urn_for("powerplatform:index:DoesNotExist"),
            resource_id="x",
            olds={},
            news={},
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        with pytest.raises(NotImplementedError, match="DoesNotExist"):
            await provider.update(request)

    @pytest.mark.asyncio
    async def test_delete_still_raises_for_truly_unknown_type(self, provider):
        request = DeleteRequest(
            urn=_urn_for("powerplatform:index:DoesNotExist"),
            resource_id="x",
            properties={},
            timeout=300,
        )
        with pytest.raises(NotImplementedError, match="DoesNotExist"):
            await provider.delete(request)
