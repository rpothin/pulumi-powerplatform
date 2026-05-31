"""Tests for GetDlpPolicyMigrationConfigFunction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_dlp_policy_migration_config import GetDlpPolicyMigrationConfigFunction


def _make_request(source_policy_id: str | None = "pol-123") -> InvokeRequest:
    args: dict[str, PropertyValue] = {}
    if source_policy_id is not None:
        args["sourcePolicyId"] = PropertyValue(source_policy_id)
    return InvokeRequest(tok="powerplatform:index:getDlpPolicyMigrationConfig", args=args)


def _make_rule_set(rs_id: str = "RS-HBAC", version: str = "1", additional_data: dict | None = None) -> MagicMock:
    rs = MagicMock()
    rs.id = rs_id
    rs.version = version
    rs_inputs = MagicMock()
    rs_inputs.additional_data = additional_data or {}
    rs.inputs = rs_inputs
    return rs


def _make_policy(name: str = "Source Policy", rule_sets: list | None = None) -> MagicMock:
    policy = MagicMock()
    policy.name = name
    policy.rule_sets = rule_sets or []
    return policy


@pytest.mark.asyncio
async def test_invoke_returns_display_name_and_rule_sets():
    """Happy-path: displayName and name are the same value; ruleSets are serialized."""
    rs = _make_rule_set("RS1", "2")
    policy = _make_policy("Source Policy", rule_sets=[rs])

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=policy)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    response = await fn.invoke(_make_request("pol-123"))

    assert response.return_value["displayName"].value == "Source Policy"
    assert response.return_value["name"].value == "Source Policy"

    rule_sets_pv = response.return_value["ruleSets"]
    assert isinstance(rule_sets_pv, PropertyValue)
    assert len(rule_sets_pv.value) == 1
    rs_map = rule_sets_pv.value[0].value
    assert rs_map["id"].value == "RS1"
    assert rs_map["version"].value == "2"


@pytest.mark.asyncio
async def test_missing_source_policy_id_raises():
    """A missing sourcePolicyId must raise ValueError, not crash unhandled."""
    client = MagicMock(spec=PowerPlatformClient)
    fn = GetDlpPolicyMigrationConfigFunction(client)

    with pytest.raises(ValueError, match="sourcePolicyId is required"):
        await fn.invoke(_make_request(source_policy_id=None))


@pytest.mark.asyncio
async def test_none_value_source_policy_id_raises():
    """sourcePolicyId with PropertyValue(None) must also raise ValueError."""
    client = MagicMock(spec=PowerPlatformClient)
    fn = GetDlpPolicyMigrationConfigFunction(client)

    request = InvokeRequest(
        tok="powerplatform:index:getDlpPolicyMigrationConfig",
        args={"sourcePolicyId": PropertyValue(None)},
    )
    with pytest.raises(ValueError, match="sourcePolicyId is required"):
        await fn.invoke(request)


@pytest.mark.asyncio
async def test_policy_not_found_raises_runtime_error():
    """A None return from the SDK (policy not found) must raise RuntimeError."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=None)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    with pytest.raises(RuntimeError, match="not found"):
        await fn.invoke(_make_request("missing-id"))


@pytest.mark.asyncio
async def test_api_error_404_raises_runtime_error():
    """A 404 APIError from the SDK is wrapped in a RuntimeError."""
    from kiota_abstractions.api_error import APIError

    err = APIError()
    err.response_status_code = 404
    err.message = "Not Found"

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(side_effect=err)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    with pytest.raises(RuntimeError, match="getDlpPolicyMigrationConfig failed"):
        await fn.invoke(_make_request("pol-123"))


@pytest.mark.asyncio
async def test_api_error_raises_runtime_error():
    """Any APIError from the SDK is wrapped in a RuntimeError with context."""
    from kiota_abstractions.api_error import APIError

    err = APIError()
    err.response_status_code = 503
    err.message = "Service Unavailable"

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(side_effect=err)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    with pytest.raises(RuntimeError, match="getDlpPolicyMigrationConfig failed"):
        await fn.invoke(_make_request("pol-999"))


@pytest.mark.asyncio
async def test_nested_rule_set_inputs_preserved():
    """Nested additional_data in ruleSets.inputs round-trips through PropertyValue correctly."""
    additional = {
        "connectors": ["connector-x", "connector-y"],
        "metadata": {"enforce": True, "priority": 5},
    }
    rs = _make_rule_set("RS-NBAC", "3", additional_data=additional)
    policy = _make_policy("Migration Policy", rule_sets=[rs])

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=policy)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    response = await fn.invoke(_make_request("pol-123"))

    rule_sets_pv = response.return_value["ruleSets"].value
    assert len(rule_sets_pv) == 1

    rs_map = rule_sets_pv[0].value
    assert rs_map["id"].value == "RS-NBAC"
    assert rs_map["version"].value == "3"

    inputs_pv = rs_map["inputs"].value
    connectors_pv = inputs_pv["connectors"].value
    assert len(connectors_pv) == 2
    assert connectors_pv[1].value == "connector-y"

    meta_pv = inputs_pv["metadata"].value
    assert meta_pv["enforce"].value is True
    assert meta_pv["priority"].value == 5.0


@pytest.mark.asyncio
async def test_display_name_and_name_are_equal():
    """displayName and name must always be the same value."""
    policy = _make_policy("Replicated Policy ABC")

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=policy)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    response = await fn.invoke(_make_request("pol-456"))

    assert response.return_value["displayName"].value == response.return_value["name"].value


@pytest.mark.asyncio
async def test_empty_rule_sets_returns_empty_list():
    """A policy with no rule sets returns an empty ruleSets array."""
    policy = _make_policy("Empty Policy", rule_sets=[])

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=policy)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    response = await fn.invoke(_make_request("pol-789"))

    assert len(response.return_value["ruleSets"].value) == 0


@pytest.mark.asyncio
async def test_correct_policy_id_passed_to_sdk():
    """The provided sourcePolicyId is forwarded to the SDK .by_policy_id() call."""
    policy = _make_policy("Test Policy")

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.by_policy_id.return_value.get = AsyncMock(return_value=policy)

    fn = GetDlpPolicyMigrationConfigFunction(client)
    await fn.invoke(_make_request("exact-id-check"))

    client.sdk.governance.rule_based_policies.by_policy_id.assert_called_once_with("exact-id-check")
