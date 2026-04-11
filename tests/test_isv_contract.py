"""Tests for the IsvContract resource handler — check and diff logic."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from pulumi_powerplatform.resources.isv_contract import IsvContractResource


def _mock_client():
    """Return None — check/diff don't use the SDK client."""
    return None


@pytest.fixture
def isv_contract_handler():
    """Create an IsvContractResource with no live client (for offline tests)."""
    return IsvContractResource(client=_mock_client())


class TestIsvContractCheck:
    """Tests for the IsvContract check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self, isv_contract_handler):
        """Valid inputs should pass check without failures."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            old_inputs={},
            new_inputs={
                "name": PropertyValue("Test Contract"),
                "geo": PropertyValue("unitedstates"),
            },
            random_seed=b"",
        )
        response = await isv_contract_handler.check(request)
        assert response.failures is None
        assert "name" in response.inputs
        assert "geo" in response.inputs

    @pytest.mark.asyncio
    async def test_check_missing_name(self, isv_contract_handler):
        """Missing name should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            old_inputs={},
            new_inputs={
                "geo": PropertyValue("unitedstates"),
            },
            random_seed=b"",
        )
        response = await isv_contract_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "name"

    @pytest.mark.asyncio
    async def test_check_missing_geo(self, isv_contract_handler):
        """Missing geo should produce a check failure."""
        request = CheckRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            old_inputs={},
            new_inputs={
                "name": PropertyValue("Test Contract"),
            },
            random_seed=b"",
        )
        response = await isv_contract_handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "geo"


class TestIsvContractDiff:
    """Tests for the IsvContract diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self, isv_contract_handler):
        """Identical old and new should produce no diff."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            resource_id="contract-123",
            old_state={
                "name": PropertyValue("Test"),
                "geo": PropertyValue("unitedstates"),
            },
            new_inputs={
                "name": PropertyValue("Test"),
                "geo": PropertyValue("unitedstates"),
            },
            ignore_changes=[],
        )
        response = await isv_contract_handler.diff(request)
        assert response.changes is False
        assert len(response.diffs) == 0

    @pytest.mark.asyncio
    async def test_diff_name_changed(self, isv_contract_handler):
        """Changed name should be detected as an in-place update."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            resource_id="contract-123",
            old_state={
                "name": PropertyValue("Old Name"),
            },
            new_inputs={
                "name": PropertyValue("New Name"),
            },
            ignore_changes=[],
        )
        response = await isv_contract_handler.diff(request)
        assert response.changes is True
        assert "name" in response.diffs
        assert response.detailed_diff["name"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_geo_changed(self, isv_contract_handler):
        """Changed geo should be detected as an in-place update (no replace)."""
        request = DiffRequest(
            urn="urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract",
            resource_id="contract-123",
            old_state={
                "geo": PropertyValue("unitedstates"),
            },
            new_inputs={
                "geo": PropertyValue("europe"),
            },
            ignore_changes=[],
        )
        response = await isv_contract_handler.diff(request)
        assert response.changes is True
        assert "geo" in response.diffs
        assert response.detailed_diff["geo"].kind == PropertyDiffKind.UPDATE
