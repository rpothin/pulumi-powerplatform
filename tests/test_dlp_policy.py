"""Tests for the DlpPolicy resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from pulumi_powerplatform.resources.dlp_policy import DlpPolicyResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def dlp_policy_handler():
    """Create a DlpPolicyResource with no live client (for offline tests)."""
    return DlpPolicyResource(client=_mock_client())


class TestDlpPolicyCheck:
    """Tests for the DlpPolicy check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, dlp_policy_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            old_inputs={},
            new_inputs={
                "name": PropertyValue("Test Policy"),
            },
            random_seed=b"",
        )
        response = await dlp_policy_handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_missing_name(self, dlp_policy_handler):
        """Missing name should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            old_inputs={},
            new_inputs={},
            random_seed=b"",
        )
        response = await dlp_policy_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "name"

    @pytest.mark.asyncio
    async def test_check_empty_name(self, dlp_policy_handler):
        """An empty name should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            old_inputs={},
            new_inputs={
                "name": PropertyValue(""),
            },
            random_seed=b"",
        )
        response = await dlp_policy_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1


class TestDlpPolicyDiff:
    """Tests for the DlpPolicy diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, dlp_policy_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "name": PropertyValue("Test Policy"),
            },
            new_inputs={
                "name": PropertyValue("Test Policy"),
            },
            ignore_changes=[],
        )
        response = await dlp_policy_handler.diff(request)
        assert response.changes is False

    @pytest.mark.asyncio
    async def test_diff_name_changed(self, dlp_policy_handler):
        """Changed name should be detected."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            resource_id="policy-123",
            old_state={
                "name": PropertyValue("Old Policy"),
            },
            new_inputs={
                "name": PropertyValue("New Policy"),
            },
            ignore_changes=[],
        )
        response = await dlp_policy_handler.diff(request)
        assert response.changes is True
        assert "name" in response.diffs
        assert response.detailed_diff["name"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_rule_sets_changed(self, dlp_policy_handler):
        """Changed ruleSets should be detected."""
        old_rs = PropertyValue(
            [PropertyValue({"id": PropertyValue("rs-1"), "version": PropertyValue("1.0")})]
        )
        new_rs = PropertyValue(
            [PropertyValue({"id": PropertyValue("rs-1"), "version": PropertyValue("2.0")})]
        )

        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:DlpPolicy::my-policy",
            resource_id="policy-123",
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
        response = await dlp_policy_handler.diff(request)
        assert response.changes is True
        assert "ruleSets" in response.diffs
