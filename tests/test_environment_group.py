"""Tests for the EnvironmentGroup resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from pulumi_powerplatform.resources.environment_group import EnvironmentGroupResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def env_group_handler():
    """Create an EnvironmentGroupResource with no live client (for offline tests)."""
    return EnvironmentGroupResource(client=_mock_client())


class TestEnvironmentGroupCheck:
    """Tests for the EnvironmentGroup check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, env_group_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test Group"),
                "description": PropertyValue("A test group"),
            },
            random_seed=b"",
        )
        response = await env_group_handler.check(request)
        assert response.failures is None
        assert "displayName" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_display_name(self, env_group_handler):
        """Missing displayName should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            old_inputs={},
            new_inputs={
                "description": PropertyValue("A test group"),
            },
            random_seed=b"",
        )
        response = await env_group_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "displayName"

    @pytest.mark.asyncio
    async def test_check_empty_display_name(self, env_group_handler):
        """An empty displayName should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue(""),
            },
            random_seed=b"",
        )
        response = await env_group_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1


class TestEnvironmentGroupDiff:
    """Tests for the EnvironmentGroup diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, env_group_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            resource_id="123",
            old_state={
                "displayName": PropertyValue("Test Group"),
                "description": PropertyValue("A test"),
            },
            new_inputs={
                "displayName": PropertyValue("Test Group"),
                "description": PropertyValue("A test"),
            },
            ignore_changes=[],
        )
        response = await env_group_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_display_name_changed(self, env_group_handler):
        """Changed displayName should be detected."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            resource_id="123",
            old_state={
                "displayName": PropertyValue("Old Name"),
            },
            new_inputs={
                "displayName": PropertyValue("New Name"),
            },
            ignore_changes=[],
        )
        response = await env_group_handler.diff(request)
        assert response.changes is True
        assert "displayName" in response.diffs
        assert "displayName" in response.detailed_diff
        assert response.detailed_diff["displayName"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_description_added(self, env_group_handler):
        """Adding a description should be detected as an update."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group",
            resource_id="123",
            old_state={
                "displayName": PropertyValue("Test"),
            },
            new_inputs={
                "displayName": PropertyValue("Test"),
                "description": PropertyValue("New description"),
            },
            ignore_changes=[],
        )
        response = await env_group_handler.diff(request)
        assert response.changes is True
        assert "description" in response.diffs
