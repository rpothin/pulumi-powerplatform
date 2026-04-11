"""Tests for EnvironmentBackup resource handler — create, read, delete with mocked SDK."""

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
from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.resources.environment_backup import EnvironmentBackupResource

_URN = "urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup"
_FAKE_BACKUP_ID = "backup-abc-123"
_FAKE_ENV_ID = "env-abc-123"
_FAKE_RESOURCE_ID = f"{_FAKE_ENV_ID}/{_FAKE_BACKUP_ID}"
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_backup(*, label: str = "daily-backup"):
    """Return a fake EnvironmentBackup-like SDK object."""
    backup = MagicMock()
    backup.id = _FAKE_BACKUP_ID
    backup.label = label
    backup.backup_point_date_time = _FAKE_TIME
    backup.backup_expiry_date_time = _FAKE_TIME
    return backup


def _mock_client():
    """Build a MagicMock that mimics the SDK call chain for environment backups."""
    client = MagicMock(spec=PowerPlatformClient)
    by_env = client.sdk.environmentmanagement.environments.by_environment_id.return_value
    by_env.backups = MagicMock()
    by_env.backups.post = AsyncMock()
    by_env.backups.by_backup_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return EnvironmentBackupResource(client=mock_client)


class TestEnvironmentBackupCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        by_env = mock_client.sdk.environmentmanagement.environments.by_environment_id.return_value
        by_env.backups.post.return_value = _fake_backup()

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_FAKE_ENV_ID),
                "label": PropertyValue("daily-backup"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert _FAKE_BACKUP_ID in response.resource_id
        assert response.properties["environmentId"].value == _FAKE_ENV_ID
        assert response.properties["label"].value == "daily-backup"
        by_env.backups.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_FAKE_ENV_ID),
                "label": PropertyValue("daily-backup"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"


class TestEnvironmentBackupRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_env = mock_client.sdk.environmentmanagement.environments.by_environment_id.return_value
        by_backup = by_env.backups.by_backup_id.return_value
        by_backup.get = AsyncMock(return_value=_fake_backup())

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _FAKE_RESOURCE_ID
        assert response.properties["environmentId"].value == _FAKE_ENV_ID
        assert response.properties["label"].value == "daily-backup"
        assert "environmentId" in response.inputs
        assert "label" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_env = mock_client.sdk.environmentmanagement.environments.by_environment_id.return_value
        by_backup = by_env.backups.by_backup_id.return_value
        by_backup.get = AsyncMock(return_value=None)

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestEnvironmentBackupDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        by_env = mock_client.sdk.environmentmanagement.environments.by_environment_id.return_value
        by_backup = by_env.backups.by_backup_id.return_value
        by_backup.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=_FAKE_RESOURCE_ID,
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_backup.delete.assert_awaited_once()
