"""Tests for DlpPolicy resource handler — create, read, update, delete with mocked SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    DiffRequest,
    PropertyDiffKind,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.dlp_policy import DlpPolicyResource

_URN = "urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy"
_FAKE_ID = "policy-abc-123"
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_policy(*, name: str = "Test Policy"):
    """Return a fake Policy-like SDK object."""
    policy = MagicMock()
    policy.id = _FAKE_ID
    policy.name = name
    policy.tenant_id = "tenant-1"
    policy.last_modified = _FAKE_TIME
    policy.rule_set_count = 1

    rs = MagicMock()
    rs.id = "rs-1"
    rs.version = "1.0"
    rs.inputs = None
    policy.rule_sets = [rs]
    return policy


def _mock_client():
    """Build a MagicMock that mimics the SDK call chain for DLP policies."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies = MagicMock()
    client.sdk.governance.rule_based_policies.post = AsyncMock()
    client.sdk.governance.rule_based_policies.by_policy_id = MagicMock()
    client.sdk.governance.rule_sets = MagicMock()
    client.sdk.governance.rule_sets.by_rule_set_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return DlpPolicyResource(client=mock_client)


class TestDlpPolicyCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        mock_client.sdk.governance.rule_based_policies.post.return_value = _fake_policy()

        request = CreateRequest(
            urn=_URN,
            properties={"name": PropertyValue("Test Policy")},
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["name"].value == "Test Policy"
        mock_client.sdk.governance.rule_based_policies.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={"name": PropertyValue("Test Policy")},
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.sdk.governance.rule_based_policies.post.assert_not_awaited()


class TestDlpPolicyRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_id = mock_client.sdk.governance.rule_based_policies.by_policy_id.return_value
        by_id.get = AsyncMock(return_value=_fake_policy())

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["name"].value == "Test Policy"
        assert "name" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_id = mock_client.sdk.governance.rule_based_policies.by_policy_id.return_value
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


class TestDlpPolicyUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_returns_updated_properties(self, handler, mock_client):
        by_id = mock_client.sdk.governance.rule_based_policies.by_policy_id.return_value
        by_id.put = AsyncMock(return_value=None)
        by_id.get = AsyncMock(return_value=_fake_policy(name="Updated Policy"))

        request = UpdateRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            olds={"name": PropertyValue("Test Policy")},
            news={"name": PropertyValue("Updated Policy")},
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)

        assert response.properties["name"].value == "Updated Policy"
        by_id.put.assert_awaited_once()


class TestDlpPolicyDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        policy = _fake_policy()
        by_policy = mock_client.sdk.governance.rule_based_policies.by_policy_id.return_value
        by_policy.get = AsyncMock(return_value=policy)

        by_rs = mock_client.sdk.governance.rule_sets.by_rule_set_id.return_value
        by_rs.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_policy.get.assert_awaited_once()
        mock_client.sdk.governance.rule_sets.by_rule_set_id.assert_called_with("rs-1")


class TestDlpPolicyDiffDeepEquality:
    """Tests for deep PropertyValue equality in diff (rule sets sub-field change)."""

    @pytest.mark.asyncio
    async def test_diff_rule_set_element_change_detected(self):
        """A changed element inside ruleSets should trigger a diff."""
        handler = DlpPolicyResource(client=None)

        old_rs = PropertyValue([
            PropertyValue({"id": PropertyValue("rs-1"), "version": PropertyValue("1.0")}),
        ])
        new_rs = PropertyValue([
            PropertyValue({"id": PropertyValue("rs-1"), "version": PropertyValue("2.0")}),
        ])

        request = DiffRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            old_state={
                "name": PropertyValue("Test"),
                "ruleSets": old_rs,
            },
            new_inputs={
                "name": PropertyValue("Test"),
                "ruleSets": new_rs,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert response.changes is True
        assert "ruleSets" in response.diffs
        assert response.detailed_diff["ruleSets"].kind == PropertyDiffKind.UPDATE
