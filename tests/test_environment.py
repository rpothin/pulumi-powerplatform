"""Tests for Environment resource handler — check and diff."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from pulumi_powerplatform.resources.environment import EnvironmentResource

_URN = "urn:pulumi:test::test::powerplatform:index:Environment::my-env"


def _make_handler():
    """Create a handler with a None client (only check/diff need no client)."""
    return EnvironmentResource(client=None)  # type: ignore[arg-type]


class TestEnvironmentCheck:
    """Tests for the check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_missing_display_name(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "displayName" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_missing_location(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "location" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_missing_environment_type(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_invalid_environment_type(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("InvalidType"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_all_valid_environment_types(self):
        handler = _make_handler()
        for env_type in ("Sandbox", "Production", "Trial", "Developer", "Default"):
            request = CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={
                    "displayName": PropertyValue("My Env"),
                    "location": PropertyValue("unitedstates"),
                    "environmentType": PropertyValue(env_type),
                },
            )
            response = await handler.check(request)
            assert response.failures is None, f"Expected no failures for type {env_type}"


class TestEnvironmentDiff:
    """Tests for the diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self):
        handler = _make_handler()
        state = {
            "displayName": PropertyValue("My Env"),
            "location": PropertyValue("unitedstates"),
            "environmentType": PropertyValue("Sandbox"),
        }
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state=state,
            new_inputs=dict(state),
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert not response.diffs

    @pytest.mark.asyncio
    async def test_diff_display_name_is_update(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("Old Name"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("New Name"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "displayName" in response.diffs
        assert response.detailed_diff["displayName"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_location_triggers_replace(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("europe"),
                "environmentType": PropertyValue("Sandbox"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "location" in response.diffs
        assert response.detailed_diff["location"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_environment_type_triggers_replace(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Production"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "environmentType" in response.diffs
        assert response.detailed_diff["environmentType"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_description_is_update(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "description": PropertyValue("old"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "description": PropertyValue("new"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "description" in response.diffs
        assert response.detailed_diff["description"].kind == PropertyDiffKind.UPDATE
