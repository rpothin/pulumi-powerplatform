"""Tests for the BillingPolicy resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from pulumi_powerplatform.resources.billing_policy import BillingPolicyResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def billing_policy_handler():
    """Create a BillingPolicyResource with no live client (for offline tests)."""
    return BillingPolicyResource(client=_mock_client())


class TestBillingPolicyCheck:
    """Tests for the BillingPolicy check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, billing_policy_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            old_inputs={},
            new_inputs={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
            },
            random_seed=b"",
        )
        response = await billing_policy_handler.check(request)
        assert response.failures is None
        assert "name" in response.inputs
        assert "location" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_name(self, billing_policy_handler):
        """Missing name should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            old_inputs={},
            new_inputs={
                "location": PropertyValue("unitedstates"),
            },
            random_seed=b"",
        )
        response = await billing_policy_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "name"

    @pytest.mark.asyncio
    async def test_check_missing_location(self, billing_policy_handler):
        """Missing location should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            old_inputs={},
            new_inputs={
                "name": PropertyValue("Test"),
            },
            random_seed=b"",
        )
        response = await billing_policy_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "location"


class TestBillingPolicyDiff:
    """Tests for the BillingPolicy diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, billing_policy_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
            },
            new_inputs={
                "name": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
            },
            ignore_changes=[],
        )
        response = await billing_policy_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_name_changed(self, billing_policy_handler):
        """Changed name should be detected as an in-place update."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "name": PropertyValue("Old Name"),
            },
            new_inputs={
                "name": PropertyValue("New Name"),
            },
            ignore_changes=[],
        )
        response = await billing_policy_handler.diff(request)
        assert response.changes is True
        assert "name" in response.diffs
        assert response.detailed_diff["name"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_status_changed(self, billing_policy_handler):
        """Changed status should be detected as an in-place update."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "status": PropertyValue("Enabled"),
            },
            new_inputs={
                "status": PropertyValue("Disabled"),
            },
            ignore_changes=[],
        )
        response = await billing_policy_handler.diff(request)
        assert response.changes is True
        assert "status" in response.diffs
        assert response.detailed_diff["status"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_location_changed_requires_replace(self, billing_policy_handler):
        """Changed location should require replacement."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:BillingPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "location": PropertyValue("unitedstates"),
            },
            new_inputs={
                "location": PropertyValue("europe"),
            },
            ignore_changes=[],
        )
        response = await billing_policy_handler.diff(request)
        assert response.changes is True
        assert "location" in response.diffs
        assert response.detailed_diff["location"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert "location" in response.replaces
