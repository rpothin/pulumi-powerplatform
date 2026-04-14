"""Tests for the RoleAssignment resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from rpothin_powerplatform.resources.role_assignment import RoleAssignmentResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def role_assignment_handler():
    """Create a RoleAssignmentResource with no live client (for offline tests)."""
    return RoleAssignmentResource(client=_mock_client())


class TestRoleAssignmentCheck:
    """Tests for the RoleAssignment check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, role_assignment_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            old_inputs={},
            new_inputs={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            random_seed=b"",
        )
        response = await role_assignment_handler.check(request)
        assert response.failures is None
        assert "principalObjectId" in response.inputs
        assert "principalType" in response.inputs
        assert "roleDefinitionId" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_principal_object_id(self, role_assignment_handler):
        """Missing principalObjectId should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            old_inputs={},
            new_inputs={
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            random_seed=b"",
        )
        response = await role_assignment_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "principalObjectId"

    @pytest.mark.asyncio
    async def test_check_missing_principal_type(self, role_assignment_handler):
        """Missing principalType should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            old_inputs={},
            new_inputs={
                "principalObjectId": PropertyValue("obj-123"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            random_seed=b"",
        )
        response = await role_assignment_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "principalType"

    @pytest.mark.asyncio
    async def test_check_missing_role_definition_id(self, role_assignment_handler):
        """Missing roleDefinitionId should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            old_inputs={},
            new_inputs={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
            },
            random_seed=b"",
        )
        response = await role_assignment_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "roleDefinitionId"


class TestRoleAssignmentDiff:
    """Tests for the RoleAssignment diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, role_assignment_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            resource_id="assignment-123",
            old_state={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            new_inputs={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            ignore_changes=[],
        )
        response = await role_assignment_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_principal_changed(self, role_assignment_handler):
        """Changed principalObjectId should require replacement."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            resource_id="assignment-123",
            old_state={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            new_inputs={
                "principalObjectId": PropertyValue("obj-999"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            ignore_changes=[],
        )
        response = await role_assignment_handler.diff(request)
        assert response.changes is True
        assert "principalObjectId" in response.diffs
        assert response.detailed_diff["principalObjectId"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "principalObjectId" in response.replaces

    @pytest.mark.asyncio
    async def test_diff_role_definition_changed(self, role_assignment_handler):
        """Changed roleDefinitionId should require replacement."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-role",
            resource_id="assignment-123",
            old_state={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-456"),
            },
            new_inputs={
                "principalObjectId": PropertyValue("obj-123"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-789"),
            },
            ignore_changes=[],
        )
        response = await role_assignment_handler.diff(request)
        assert response.changes is True
        assert "roleDefinitionId" in response.diffs
        assert response.detailed_diff["roleDefinitionId"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "roleDefinitionId" in response.replaces
