"""DLP Policy resource handler — full CRUD via the Power Platform Management SDK."""

from __future__ import annotations

from typing import Any, Optional

from mspp_management.models.policy import Policy
from mspp_management.models.policy_request import PolicyRequest
from mspp_management.models.rule_set import RuleSet
from mspp_management.models.rule_set_inputs import RuleSet_inputs
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckFailure,
    CheckRequest,
    CheckResponse,
    CreateRequest,
    CreateResponse,
    DeleteRequest,
    DiffRequest,
    DiffResponse,
    PropertyDiff,
    PropertyDiffKind,
    ReadRequest,
    ReadResponse,
    UpdateRequest,
    UpdateResponse,
)

from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.utils import pv_str as _pv_str
from pulumi_powerplatform.utils import pv_to_comparable as _pv_to_comparable


def _pv_to_rule_sets(pv: Optional[PropertyValue]) -> Optional[list[RuleSet]]:
    """Convert a PropertyValue array of rule set objects to SDK RuleSet models."""
    if pv is None or pv.value is None:
        return None

    rule_sets: list[RuleSet] = []
    items = pv.value  # Should be a list of PropertyValue

    for item_pv in items:
        if item_pv.value is None:
            continue
        obj: dict[str, PropertyValue] = item_pv.value
        rs = RuleSet()
        rs.id = _pv_str(obj.get("id"))
        rs.version = _pv_str(obj.get("version"))

        # Handle the 'inputs' field as additional data (it's a flexible object).
        inputs_pv = obj.get("inputs")
        if inputs_pv is not None and inputs_pv.value is not None:
            rs_inputs = RuleSet_inputs()
            rs_inputs.additional_data = _pv_to_dict(inputs_pv)
            rs.inputs = rs_inputs

        rule_sets.append(rs)

    return rule_sets


def _pv_to_dict(pv: PropertyValue) -> dict[str, Any]:
    """Recursively convert a PropertyValue map to a plain Python dict."""
    if pv.value is None:
        return {}
    result: dict[str, Any] = {}
    for key, val in pv.value.items():
        result[key] = _pv_to_python(val)
    return result


def _pv_to_python(pv: PropertyValue) -> Any:
    """Recursively convert a PropertyValue to a plain Python value."""
    if pv.value is None:
        return None
    if isinstance(pv.value, (str, bool, float, int)):
        return pv.value
    if isinstance(pv.value, list):
        return [_pv_to_python(item) for item in pv.value]
    if isinstance(pv.value, dict):
        return {k: _pv_to_python(v) for k, v in pv.value.items()}
    return pv.value


class DlpPolicyResource:
    """Handles CRUD operations for powerplatform:index:DlpPolicy."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for a DLP policy."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        name = _pv_str(inputs.get("name"))
        if not name:
            failures.append(CheckFailure(property="name", reason="name is required and cannot be empty."))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for a DLP policy."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}

        old = request.old_state
        new = request.new_inputs

        # Check name change.
        if _pv_str(old.get("name")) != _pv_str(new.get("name")):
            diffs.append("name")
            detailed["name"] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        # Rule sets are always diffed as a whole (complex structure).
        old_rs = old.get("ruleSets")
        new_rs = new.get("ruleSets")
        if _pv_to_comparable(old_rs) != _pv_to_comparable(new_rs):
            diffs.append("ruleSets")
            detailed["ruleSets"] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create a new DLP policy."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties

        body = PolicyRequest()
        body.name = _pv_str(props.get("name"))
        body.rule_sets = _pv_to_rule_sets(props.get("ruleSets"))

        result = await self._client.sdk.governance.rule_based_policies.post(body)
        if result is None:
            raise RuntimeError("Failed to create DLP policy: API returned no result.")

        policy_id = result.id or ""
        return CreateResponse(
            resource_id=policy_id,
            properties=_policy_to_outputs(result),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of a DLP policy."""
        policy_id = request.resource_id
        result = await self._client.sdk.governance.rule_based_policies.by_policy_id(policy_id).get()

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _policy_to_outputs(result)
        inputs = {k: v for k, v in outputs.items() if k in ("name", "ruleSets")}
        return ReadResponse(resource_id=policy_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update an existing DLP policy."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        policy_id = request.resource_id
        props = request.news

        body = PolicyRequest()
        body.name = _pv_str(props.get("name"))
        body.rule_sets = _pv_to_rule_sets(props.get("ruleSets"))

        await self._client.sdk.governance.rule_based_policies.by_policy_id(policy_id).put(body)

        # Re-read to get the authoritative state after update.
        result = await self._client.sdk.governance.rule_based_policies.by_policy_id(policy_id).get()
        if result is None:
            raise RuntimeError(f"Failed to read DLP policy {policy_id} after update.")

        return UpdateResponse(properties=_policy_to_outputs(result))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete a DLP policy.

        Note: The SDK does not expose a DELETE on rule-based policies directly.
        A policy is effectively removed by deleting all its rule sets — this is
        a known limitation documented in the schema. A future version may use
        the raw REST API for direct deletion.
        """
        policy_id = request.resource_id

        # Read the policy to get its rule sets.
        policy = await self._client.sdk.governance.rule_based_policies.by_policy_id(policy_id).get()
        if policy is None:
            return  # Already gone.

        # Delete each rule set individually.
        if policy.rule_sets:
            for rs in policy.rule_sets:
                if rs.id:
                    await self._client.sdk.governance.rule_sets.by_rule_set_id(rs.id).delete()


def _policy_to_outputs(policy: Policy) -> dict[str, PropertyValue]:
    """Convert a Policy SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}

    if policy.name is not None:
        outputs["name"] = PropertyValue(policy.name)
    if policy.tenant_id is not None:
        outputs["tenantId"] = PropertyValue(policy.tenant_id)
    if policy.last_modified is not None:
        outputs["lastModified"] = PropertyValue(policy.last_modified.isoformat())
    if policy.rule_set_count is not None:
        outputs["ruleSetCount"] = PropertyValue(float(policy.rule_set_count))

    if policy.rule_sets is not None:
        rule_set_pvs: list[PropertyValue] = []
        for rs in policy.rule_sets:
            rs_map: dict[str, PropertyValue] = {}
            if rs.id is not None:
                rs_map["id"] = PropertyValue(rs.id)
            if rs.version is not None:
                rs_map["version"] = PropertyValue(rs.version)
            if rs.inputs is not None and rs.inputs.additional_data:
                rs_map["inputs"] = PropertyValue(_dict_to_pv_map(rs.inputs.additional_data))
            rule_set_pvs.append(PropertyValue(rs_map))
        outputs["ruleSets"] = PropertyValue(rule_set_pvs)

    return outputs


def _dict_to_pv_map(data: dict[str, Any]) -> dict[str, PropertyValue]:
    """Recursively convert a Python dict to a PropertyValue map."""
    result: dict[str, PropertyValue] = {}
    for key, val in data.items():
        result[key] = _python_to_pv(val)
    return result


def _python_to_pv(val: Any) -> PropertyValue:
    """Recursively convert a Python value to a PropertyValue."""
    if val is None:
        return PropertyValue(None)
    if isinstance(val, bool):
        return PropertyValue(val)
    if isinstance(val, (int, float)):
        return PropertyValue(float(val))
    if isinstance(val, str):
        return PropertyValue(val)
    if isinstance(val, list):
        return PropertyValue([_python_to_pv(item) for item in val])
    if isinstance(val, dict):
        return PropertyValue(_dict_to_pv_map(val))
    return PropertyValue(str(val))
