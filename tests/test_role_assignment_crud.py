"""Tests for RoleAssignment resource handler — create, read, delete with mocked SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.role_assignment import RoleAssignmentResource

_URN = "urn:pulumi:test::test::powerplatform:index:RoleAssignment::my-assignment"
_FAKE_ID = "assignment-abc-123"
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_response():
    """Return a fake RoleAssignmentResponse-like SDK object with one value."""
    value_item = MagicMock()
    value_item.role_assignment_id = _FAKE_ID
    value_item.principal_object_id = "principal-1"
    value_item.principal_type = "User"
    value_item.role_definition_id = "role-def-1"
    value_item.scope = "/providers/Microsoft.PowerPlatform"
    value_item.created_on = _FAKE_TIME

    response = MagicMock()
    response.value = [value_item]
    return response


def _mock_client():
    """Build a MagicMock that mimics the SDK call chain for role assignments."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.authorization.role_assignments = MagicMock()
    client.sdk.authorization.role_assignments.post = AsyncMock()
    client.sdk.authorization.role_assignments.by_role_assignment_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return RoleAssignmentResource(client=mock_client)


class TestRoleAssignmentCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        mock_client.sdk.authorization.role_assignments.post.return_value = _fake_response()

        request = CreateRequest(
            urn=_URN,
            properties={
                "principalObjectId": PropertyValue("principal-1"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-def-1"),
                "scope": PropertyValue("/providers/Microsoft.PowerPlatform"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["principalObjectId"].value == "principal-1"
        assert response.properties["principalType"].value == "User"
        mock_client.sdk.authorization.role_assignments.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "principalObjectId": PropertyValue("principal-1"),
                "principalType": PropertyValue("User"),
                "roleDefinitionId": PropertyValue("role-def-1"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.sdk.authorization.role_assignments.post.assert_not_awaited()


class TestRoleAssignmentRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_id = mock_client.sdk.authorization.role_assignments.by_role_assignment_id.return_value
        by_id.get = AsyncMock(return_value=_fake_response())

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["principalObjectId"].value == "principal-1"
        assert "principalObjectId" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_id = mock_client.sdk.authorization.role_assignments.by_role_assignment_id.return_value
        by_id.get = AsyncMock(return_value=None)

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestRoleAssignmentDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        by_id = mock_client.sdk.authorization.role_assignments.by_role_assignment_id.return_value
        by_id.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_id.delete.assert_awaited_once()
