"""Tests for the ManagedEnvironment resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from rpothin_powerplatform.resources.managed_environment import ManagedEnvironmentResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def managed_env_handler():
    """Create a ManagedEnvironmentResource with no live client (for offline tests)."""
    return ManagedEnvironmentResource(client=_mock_client())


class TestManagedEnvironmentCheck:
    """Tests for the ManagedEnvironment check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, managed_env_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:ManagedEnvironment::my-env",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("env-123"),
            },
            random_seed=b"",
        )
        response = await managed_env_handler.check(request)
        assert response.failures is None
        assert "environmentId" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_environment_id(self, managed_env_handler):
        """Missing environmentId should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:ManagedEnvironment::my-env",
            old_inputs={},
            new_inputs={},
            random_seed=b"",
        )
        response = await managed_env_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "environmentId"

    @pytest.mark.asyncio
    async def test_check_empty_environment_id(self, managed_env_handler):
        """An empty environmentId should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:ManagedEnvironment::my-env",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(""),
            },
            random_seed=b"",
        )
        response = await managed_env_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1


class TestManagedEnvironmentDiff:
    """Tests for the ManagedEnvironment diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, managed_env_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:ManagedEnvironment::my-env",
            resource_id="env-123",
            old_state={
                "environmentId": PropertyValue("env-123"),
            },
            new_inputs={
                "environmentId": PropertyValue("env-123"),
            },
            ignore_changes=[],
        )
        response = await managed_env_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_environment_id_changed(self, managed_env_handler):
        """Changed environmentId should require replacement."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:ManagedEnvironment::my-env",
            resource_id="env-123",
            old_state={
                "environmentId": PropertyValue("env-123"),
            },
            new_inputs={
                "environmentId": PropertyValue("env-456"),
            },
            ignore_changes=[],
        )
        response = await managed_env_handler.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "environmentId" in response.replaces
