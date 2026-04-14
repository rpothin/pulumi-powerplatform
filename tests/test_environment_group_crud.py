"""Tests for EnvironmentGroup resource handler — create, read, update, delete with mocked SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from mspp_management.models.environment_group import EnvironmentGroup
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.environment_group import EnvironmentGroupResource

_URN = "urn:pulumi:test::test::powerplatform:index:EnvironmentGroup::my-group"
_FAKE_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_group(
    *,
    display_name: str = "Test",
    description: str = "Desc",
) -> EnvironmentGroup:
    """Return a fake EnvironmentGroup SDK model."""
    group = EnvironmentGroup()
    group.id = _FAKE_ID
    group.display_name = display_name
    group.description = description
    group.parent_group_id = None
    group.created_time = _FAKE_TIME
    group.last_modified_time = _FAKE_TIME
    return group


def _mock_client() -> MagicMock:
    """Build a MagicMock that mimics the SDK call chains used by the handler."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.environmentmanagement.environment_groups = MagicMock()
    client.sdk.environmentmanagement.environment_groups.post = AsyncMock()
    client.sdk.environmentmanagement.environment_groups.by_group_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return EnvironmentGroupResource(client=mock_client)


class TestEnvironmentGroupCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        mock_client.sdk.environmentmanagement.environment_groups.post.return_value = _fake_group()

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test"),
                "description": PropertyValue("Desc"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["displayName"].value == "Test"
        assert response.properties["description"].value == "Desc"
        mock_client.sdk.environmentmanagement.environment_groups.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test"),
                "description": PropertyValue("Desc"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.sdk.environmentmanagement.environment_groups.post.assert_not_awaited()


class TestEnvironmentGroupRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_group = mock_client.sdk.environmentmanagement.environment_groups.by_group_id.return_value
        by_group.get = AsyncMock(return_value=_fake_group())

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["displayName"].value == "Test"
        assert response.properties["description"].value == "Desc"
        assert "displayName" in response.inputs
        assert "description" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_group = mock_client.sdk.environmentmanagement.environment_groups.by_group_id.return_value
        by_group.get = AsyncMock(return_value=None)

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestEnvironmentGroupUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_returns_updated_properties(self, handler, mock_client):
        by_group = mock_client.sdk.environmentmanagement.environment_groups.by_group_id.return_value
        by_group.put = AsyncMock(return_value=_fake_group(display_name="Updated"))

        request = UpdateRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            olds={
                "displayName": PropertyValue("Test"),
                "description": PropertyValue("Desc"),
            },
            news={
                "displayName": PropertyValue("Updated"),
                "description": PropertyValue("Desc"),
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)

        assert response.properties["displayName"].value == "Updated"
        by_group.put.assert_awaited_once()


class TestEnvironmentGroupDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        by_group = mock_client.sdk.environmentmanagement.environment_groups.by_group_id.return_value
        by_group.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_group.delete.assert_awaited_once()
