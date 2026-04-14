"""Tests for BillingPolicy resource handler — create, read, update, delete with mocked SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

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
from rpothin_powerplatform.resources.billing_policy import BillingPolicyResource

_URN = "urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy"
_FAKE_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_policy(*, name: str = "Test", location: str = "unitedstates"):
    """Return a fake BillingPolicyResponseModel-like SDK object."""
    policy = MagicMock()
    policy.id = _FAKE_ID
    policy.name = name
    policy.location = location
    policy.status = MagicMock(value="Enabled")
    bi = MagicMock()
    bi.id = "bi-1"
    bi.resource_group = "rg-1"
    bi.subscription_id = UUID("11111111-2222-3333-4444-555555555555")
    policy.billing_instrument = bi
    policy.created_on = _FAKE_TIME
    policy.last_modified_on = _FAKE_TIME
    return policy


def _mock_client():
    """Build a MagicMock that mimics the SDK call chain for billing policies."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.licensing.billing_policies = MagicMock()
    client.sdk.licensing.billing_policies.post = AsyncMock()
    client.sdk.licensing.billing_policies.by_billing_policy_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return BillingPolicyResource(client=mock_client)


class TestBillingPolicyCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        mock_client.sdk.licensing.billing_policies.post.return_value = _fake_policy()

        request = CreateRequest(
            urn=_URN,
            properties={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["name"].value == "Test"
        assert response.properties["location"].value == "unitedstates"
        mock_client.sdk.licensing.billing_policies.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.sdk.licensing.billing_policies.post.assert_not_awaited()


class TestBillingPolicyRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.billing_policies.by_billing_policy_id.return_value
        by_id.get = AsyncMock(return_value=_fake_policy())

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["name"].value == "Test"
        assert response.properties["location"].value == "unitedstates"
        assert "name" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.billing_policies.by_billing_policy_id.return_value
        by_id.get = AsyncMock(return_value=None)

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestBillingPolicyUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_returns_updated_properties(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.billing_policies.by_billing_policy_id.return_value
        by_id.put = AsyncMock(return_value=_fake_policy(name="Updated"))

        request = UpdateRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            olds={"name": PropertyValue("Test")},
            news={"name": PropertyValue("Updated")},
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)

        assert response.properties["name"].value == "Updated"
        by_id.put.assert_awaited_once()


class TestBillingPolicyDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.billing_policies.by_billing_policy_id.return_value
        by_id.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_id.delete.assert_awaited_once()


class TestBillingPolicyDiffDeepEquality:
    """Tests for deep PropertyValue equality in diff (billing instrument sub-fields)."""

    @pytest.mark.asyncio
    async def test_diff_billing_instrument_subfield_change_detected(self):
        """A changed billingInstrument.resourceGroup should trigger a diff/replace."""
        handler = BillingPolicyResource(client=None)

        old_bi = PropertyValue({
            "id": PropertyValue("bi-1"),
            "resourceGroup": PropertyValue("rg-old"),
            "subscriptionId": PropertyValue("11111111-2222-3333-4444-555555555555"),
        })
        new_bi = PropertyValue({
            "id": PropertyValue("bi-1"),
            "resourceGroup": PropertyValue("rg-new"),
            "subscriptionId": PropertyValue("11111111-2222-3333-4444-555555555555"),
        })

        request = DiffRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            old_state={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "billingInstrument": old_bi,
            },
            new_inputs={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "billingInstrument": new_bi,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert response.changes is True
        assert "billingInstrument" in response.diffs
        assert response.detailed_diff["billingInstrument"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "billingInstrument" in response.replaces
