"""Tests for GetDlpPoliciesFunction."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_dlp_policies import GetDlpPoliciesFunction


def _make_request() -> InvokeRequest:
    return InvokeRequest(tok="powerplatform:index:getDlpPolicies", args={})


def _make_rule_set(rs_id: str = "RS1", version: str = "1", additional_data: dict | None = None) -> MagicMock:
    rs = MagicMock()
    rs.id = rs_id
    rs.version = version
    rs_inputs = MagicMock()
    rs_inputs.additional_data = additional_data or {}
    rs.inputs = rs_inputs
    return rs


def _make_policy(
    policy_id: str = "pol-1",
    name: str = "My DLP Policy",
    tenant_id: str = "tenant-abc",
    last_modified: datetime | None = None,
    rule_set_count: int = 1,
    rule_sets: list | None = None,
) -> MagicMock:
    policy = MagicMock()
    policy.id = policy_id
    policy.name = name
    policy.tenant_id = tenant_id
    policy.last_modified = last_modified or datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    policy.rule_set_count = rule_set_count
    policy.rule_sets = rule_sets or []
    return policy


@pytest.mark.asyncio
async def test_invoke_returns_policies():
    """Basic happy-path: two policies with all fields are serialized correctly."""
    rs1 = _make_rule_set("RS-HBAC", "2")
    pol1 = _make_policy("id-1", "Policy Alpha", "tenant-1", rule_sets=[rs1])
    pol2 = _make_policy("id-2", "Policy Beta", "tenant-1", rule_sets=[])

    result_mock = MagicMock()
    result_mock.value = [pol1, pol2]

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=result_mock)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    policies_pv = response.return_value["policies"]
    assert isinstance(policies_pv, PropertyValue)
    assert isinstance(policies_pv.value, (list, tuple))
    assert len(policies_pv.value) == 2

    p1 = policies_pv.value[0].value
    assert p1["id"].value == "id-1"
    assert p1["name"].value == "Policy Alpha"
    assert p1["tenantId"].value == "tenant-1"
    assert "lastModified" in p1
    assert p1["ruleSetCount"].value == 1.0
    assert isinstance(p1["ruleSets"].value, (list, tuple))
    assert len(p1["ruleSets"].value) == 1


@pytest.mark.asyncio
async def test_invoke_empty_result():
    """An empty policy list returns an empty array."""
    result_mock = MagicMock()
    result_mock.value = []

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=result_mock)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    policies_pv = response.return_value["policies"]
    assert len(policies_pv.value) == 0


@pytest.mark.asyncio
async def test_invoke_none_result():
    """A None response from the SDK returns an empty array (graceful)."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=None)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    policies_pv = response.return_value["policies"]
    assert len(policies_pv.value) == 0


@pytest.mark.asyncio
async def test_invoke_none_value_field():
    """result.value == None (not the result itself) returns an empty list."""
    result_mock = MagicMock()
    result_mock.value = None

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=result_mock)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    policies_pv = response.return_value["policies"]
    assert len(policies_pv.value) == 0


@pytest.mark.asyncio
async def test_rule_sets_nested_inputs_preserved():
    """Nested additional_data inside ruleSets.inputs is faithfully serialized."""
    additional = {
        "connectors": ["connector-a", "connector-b"],
        "metadata": {"enforce": True, "level": 3},
    }
    rs = _make_rule_set("RS-HBAC", "1", additional_data=additional)
    pol = _make_policy(rule_sets=[rs])

    result_mock = MagicMock()
    result_mock.value = [pol]

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=result_mock)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    policies_pv = response.return_value["policies"]
    p_map = policies_pv.value[0].value
    rule_sets_pv = p_map["ruleSets"].value
    assert len(rule_sets_pv) == 1

    rs_map = rule_sets_pv[0].value
    assert rs_map["id"].value == "RS-HBAC"
    assert rs_map["version"].value == "1"

    inputs_map = rs_map["inputs"].value
    connectors_pv = inputs_map["connectors"].value
    assert len(connectors_pv) == 2
    assert connectors_pv[0].value == "connector-a"

    metadata_pv = inputs_map["metadata"].value
    assert metadata_pv["enforce"].value is True
    assert metadata_pv["level"].value == 3.0


@pytest.mark.asyncio
async def test_api_error_raises_runtime_error():
    """An APIError from the SDK is wrapped in a RuntimeError."""
    from kiota_abstractions.api_error import APIError

    err = APIError()
    err.response_status_code = 403
    err.message = "Forbidden"

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(side_effect=err)

    fn = GetDlpPoliciesFunction(client)
    with pytest.raises(RuntimeError, match="getDlpPolicies failed"):
        await fn.invoke(_make_request())


@pytest.mark.asyncio
async def test_last_modified_iso_format():
    """lastModified is serialized as an ISO 8601 string."""
    dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    pol = _make_policy(last_modified=dt)

    result_mock = MagicMock()
    result_mock.value = [pol]

    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.governance.rule_based_policies.get = AsyncMock(return_value=result_mock)

    fn = GetDlpPoliciesFunction(client)
    response = await fn.invoke(_make_request())

    p_map = response.return_value["policies"].value[0].value
    assert p_map["lastModified"].value == "2025-06-01T12:00:00+00:00"
