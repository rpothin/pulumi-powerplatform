"""Tests for the EnvironmentBackup resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from rpothin_powerplatform.resources.environment_backup import EnvironmentBackupResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def env_backup_handler():
    """Create an EnvironmentBackupResource with no live client (for offline tests)."""
    return EnvironmentBackupResource(client=_mock_client())


class TestEnvironmentBackupCheck:
    """Tests for the EnvironmentBackup check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, env_backup_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("my-backup"),
            },
            random_seed=b"",
        )
        response = await env_backup_handler.check(request)
        assert response.failures is None
        assert "environmentId" in response.inputs
        assert "label" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_environment_id(self, env_backup_handler):
        """Missing environmentId should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            old_inputs={},
            new_inputs={
                "label": PropertyValue("my-backup"),
            },
            random_seed=b"",
        )
        response = await env_backup_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "environmentId"

    @pytest.mark.asyncio
    async def test_check_missing_label(self, env_backup_handler):
        """Missing label should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("env-1"),
            },
            random_seed=b"",
        )
        response = await env_backup_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "label"


class TestEnvironmentBackupDiff:
    """Tests for the EnvironmentBackup diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, env_backup_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            resource_id="env-1/backup-1",
            old_state={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("my-backup"),
            },
            new_inputs={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("my-backup"),
            },
            ignore_changes=[],
        )
        response = await env_backup_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_label_changed(self, env_backup_handler):
        """Changed label should require replacement (backups are immutable)."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            resource_id="env-1/backup-1",
            old_state={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("old-label"),
            },
            new_inputs={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("new-label"),
            },
            ignore_changes=[],
        )
        response = await env_backup_handler.diff(request)
        assert response.changes is True
        assert "label" in response.diffs
        assert response.detailed_diff["label"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "label" in response.replaces

    @pytest.mark.asyncio
    async def test_diff_environment_id_changed(self, env_backup_handler):
        """Changed environmentId should require replacement."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:EnvironmentBackup::my-backup",
            resource_id="env-1/backup-1",
            old_state={
                "environmentId": PropertyValue("env-1"),
                "label": PropertyValue("my-backup"),
            },
            new_inputs={
                "environmentId": PropertyValue("env-2"),
                "label": PropertyValue("my-backup"),
            },
            ignore_changes=[],
        )
        response = await env_backup_handler.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "environmentId" in response.replaces
