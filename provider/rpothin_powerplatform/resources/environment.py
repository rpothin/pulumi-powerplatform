"""Environment resource handler — full CRUD via the Power Platform BAP admin API."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

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

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.utils import HttpError
from rpothin_powerplatform.utils import pv_str as _pv_str

logger = logging.getLogger(__name__)

_VALID_ENV_TYPES = {"Sandbox", "Production", "Trial", "Developer", "Default"}
_VALID_CADENCE = {"Frequent", "Moderate"}

# Maps user-facing policy type names to API named keys and back.
_POLICY_TYPE_TO_KEY = {
    "NetworkInjection": "vnets",
    "Encryption": "customerManagedKeys",
    "Identity": "identity",
}
_POLICY_KEY_TO_TYPE = {v: k for k, v in _POLICY_TYPE_TO_KEY.items()}

# Immutable properties that require replacement when changed.
_REPLACE_PROPS = {"location", "environmentType", "azureRegion", "cadence", "templates", "templateMetadata"}

# Updatable properties.
_UPDATE_PROPS = {
    "displayName",
    "description",
    "domainName",
    "securityGroupId",
    "administrationModeEnabled",
    "backgroundOperationEnabled",
    "allowBingSearch",
    "allowMovingDataAcrossRegions",
    "ownerId",
    "billingPolicyId",
    "environmentGroupId",
    "linkedAppType",
    "linkedAppId",
    "enterprisePolicies",
}

_BAP_API_VERSION = "2021-04-01"

_ADMIN_ENV_PATH = "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments"

_POLL_INTERVAL_SECONDS = 10

_DEFAULT_MAX_POLLS = 30

_TERMINAL_STATES = {"Succeeded", "Failed", "Canceled", "Cancelled"}


class EnvironmentResource:
    """Handles CRUD operations for powerplatform:index:Environment."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for an environment."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        display_name = _pv_str(inputs.get("displayName"))
        if not display_name:
            failures.append(CheckFailure(property="displayName", reason="displayName is required and cannot be empty."))

        location = _pv_str(inputs.get("location"))
        if not location:
            failures.append(CheckFailure(property="location", reason="location is required and cannot be empty."))

        env_type = _pv_str(inputs.get("environmentType"))
        if not env_type:
            failures.append(
                CheckFailure(property="environmentType", reason="environmentType is required and cannot be empty.")
            )
        elif env_type not in _VALID_ENV_TYPES:
            failures.append(
                CheckFailure(
                    property="environmentType",
                    reason=f"environmentType must be one of: {', '.join(sorted(_VALID_ENV_TYPES))}.",
                )
            )

        cadence = _pv_str(inputs.get("cadence"))
        if cadence and cadence not in _VALID_CADENCE:
            failures.append(
                CheckFailure(
                    property="cadence",
                    reason=f"cadence must be one of: {', '.join(sorted(_VALID_CADENCE))}.",
                )
            )

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for an environment."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}

        old = request.old_state
        new = request.new_inputs

        for prop in _REPLACE_PROPS:
            if prop == "templates":
                old_val = _pv_list(old.get(prop))
                new_val = _pv_list(new.get(prop))
            else:
                old_val = _pv_str(old.get(prop))
                new_val = _pv_str(new.get(prop))
            if old_val != new_val:
                diffs.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)

        for prop in _UPDATE_PROPS:
            if prop == "enterprisePolicies":
                old_json = _pv_list_json(old.get(prop))
                new_json = _pv_list_json(new.get(prop))
                if old_json != new_json:
                    diffs.append(prop)
                    detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)
            elif prop in {
                "administrationModeEnabled",
                "backgroundOperationEnabled",
                "allowBingSearch",
                "allowMovingDataAcrossRegions",
            }:
                old_val = _pv_bool(old.get(prop))
                new_val = _pv_bool(new.get(prop))
                if old_val != new_val:
                    diffs.append(prop)
                    detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)
            else:
                old_val = _pv_str(old.get(prop))
                new_val = _pv_str(new.get(prop))
                if old_val != new_val:
                    diffs.append(prop)
                    detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create a new Power Platform environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties
        body: dict[str, Any] = {
            "properties": {
                "displayName": _pv_str(props.get("displayName")),
                "description": _pv_str(props.get("description")) or "",
                "environmentSku": _pv_str(props.get("environmentType")),
            },
            "location": _pv_str(props.get("location")),
        }

        azure_region = _pv_str(props.get("azureRegion"))
        if azure_region:
            body["properties"]["azureRegion"] = azure_region

        cadence = _pv_str(props.get("cadence"))
        if cadence:
            body["properties"]["updateCadence"] = {"id": cadence}

        billing_policy_id = _pv_str(props.get("billingPolicyId"))
        if billing_policy_id:
            body["properties"]["billingPolicy"] = {"id": billing_policy_id}

        env_group_id = _pv_str(props.get("environmentGroupId"))
        if env_group_id:
            body["properties"]["parentEnvironmentGroup"] = {"id": env_group_id}

        owner_id = _pv_str(props.get("ownerId"))
        if owner_id:
            body["properties"]["usedBy"] = {"id": owner_id, "type": "1"}

        allow_bing = _pv_bool(props.get("allowBingSearch"))
        if allow_bing is not None:
            body["properties"]["bingChatEnabled"] = allow_bing

        allow_cross_region = _pv_bool(props.get("allowMovingDataAcrossRegions"))
        if allow_cross_region is not None:
            body["properties"]["copilotPolicies"] = {
                "crossGeoCopilotDataMovementEnabled": allow_cross_region
            }

        linked = body["properties"].setdefault("linkedEnvironmentMetadata", {})

        domain_name = _pv_str(props.get("domainName"))
        if domain_name:
            linked["domainName"] = domain_name

        currency_code = _pv_str(props.get("currencyCode"))
        if currency_code:
            linked["currency"] = {"code": currency_code}

        language_code = _pv_str(props.get("languageCode"))
        if language_code:
            linked["baseLanguage"] = int(language_code)

        security_group_id = _pv_str(props.get("securityGroupId"))
        if security_group_id:
            linked["securityGroupId"] = security_group_id

        admin_mode = _pv_bool(props.get("administrationModeEnabled"))
        if admin_mode:
            body["properties"]["states"] = {"runtime": {"id": "AdminMode"}}

        bg_ops = _pv_bool(props.get("backgroundOperationEnabled"))
        if bg_ops is not None:
            linked["backgroundOperationsState"] = "Enabled" if bg_ops else "Disabled"

        templates = _pv_list(props.get("templates"))
        if templates:
            linked["templates"] = templates

        template_metadata_str = _pv_str(props.get("templateMetadata"))
        if template_metadata_str:
            try:
                linked["templateMetadata"] = json.loads(template_metadata_str)
            except json.JSONDecodeError:
                linked["templateMetadata"] = template_metadata_str

        linked_app_type = _pv_str(props.get("linkedAppType"))
        linked_app_id = _pv_str(props.get("linkedAppId"))
        if linked_app_type or linked_app_id:
            body["properties"]["linkedAppMetadata"] = {}
            if linked_app_type:
                body["properties"]["linkedAppMetadata"]["type"] = linked_app_type
            if linked_app_id:
                body["properties"]["linkedAppMetadata"]["id"] = linked_app_id

        enterprise_policies = _pv_enterprise_policies(props.get("enterprisePolicies"))
        if enterprise_policies:
            body["properties"]["enterprisePolicies"] = enterprise_policies

        # Remove empty linkedEnvironmentMetadata if nothing was set.
        if not linked:
            del body["properties"]["linkedEnvironmentMetadata"]

        result = await self._client.raw.request(
            "POST",
            "/providers/Microsoft.BusinessAppPlatform/environments",
            body=body,
            api_version=_BAP_API_VERSION,
        )

        if result is None:
            raise RuntimeError("Failed to create environment: API returned no result.")

        # Handle async provisioning (202 Accepted pattern).
        # The BAP API may return a response with provisioningState != "Succeeded",
        # indicating that the environment is still being created.
        provisioning_state = result.get("properties", {}).get("provisioningState", "")
        env_id = result.get("name", "")
        if not env_id:
            raise RuntimeError("Environment create response did not include an environment id.")

        if provisioning_state and provisioning_state not in _TERMINAL_STATES:
            # Poll until terminal state
            max_polls = max(1, request.timeout // _POLL_INTERVAL_SECONDS) if request.timeout else _DEFAULT_MAX_POLLS
            await self._poll_provisioning(env_id, max_polls)

        if provisioning_state == "Failed":
            raise RuntimeError(f"Environment creation failed: {result}")

        # Fetch the final environment state via the admin read endpoint,
        # retrying on 404 until the resource is propagated (eventual consistency).
        final = await self._wait_for_visibility(env_id)

        return CreateResponse(
            resource_id=env_id,
            properties=_env_to_outputs(final),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of an environment."""
        env_id = request.resource_id

        try:
            result = await self._client.raw.request(
                "GET",
                f"{_ADMIN_ENV_PATH}/{env_id}",
                api_version=_BAP_API_VERSION,
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _env_to_outputs(result)
        inputs = {k: v for k, v in outputs.items() if k in _INPUT_PROPS}
        return ReadResponse(resource_id=env_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update an existing environment."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        env_id = request.resource_id
        props = request.news

        patch_body: dict[str, Any] = {"properties": {}}

        display_name = _pv_str(props.get("displayName"))
        if display_name is not None:
            patch_body["properties"]["displayName"] = display_name

        description = _pv_str(props.get("description"))
        if description is not None:
            patch_body["properties"]["description"] = description

        billing_policy_id = _pv_str(props.get("billingPolicyId"))
        if billing_policy_id is not None:
            patch_body["properties"]["billingPolicy"] = {"id": billing_policy_id}

        env_group_id = _pv_str(props.get("environmentGroupId"))
        if env_group_id is not None:
            patch_body["properties"]["parentEnvironmentGroup"] = {"id": env_group_id}

        owner_id = _pv_str(props.get("ownerId"))
        if owner_id is not None:
            patch_body["properties"]["usedBy"] = {"id": owner_id, "type": "1"}

        allow_bing = _pv_bool(props.get("allowBingSearch"))
        if allow_bing is not None:
            patch_body["properties"]["bingChatEnabled"] = allow_bing

        allow_cross_region = _pv_bool(props.get("allowMovingDataAcrossRegions"))
        if allow_cross_region is not None:
            patch_body["properties"]["copilotPolicies"] = {
                "crossGeoCopilotDataMovementEnabled": allow_cross_region
            }

        admin_mode = _pv_bool(props.get("administrationModeEnabled"))
        if admin_mode is not None:
            patch_body["properties"]["states"] = {
                "runtime": {"id": "AdminMode" if admin_mode else "Enabled"}
            }

        linked_app_type = _pv_str(props.get("linkedAppType"))
        linked_app_id = _pv_str(props.get("linkedAppId"))
        if linked_app_type is not None or linked_app_id is not None:
            linked_app: dict[str, str] = {}
            if linked_app_type is not None:
                linked_app["type"] = linked_app_type
            if linked_app_id is not None:
                linked_app["id"] = linked_app_id
            patch_body["properties"]["linkedAppMetadata"] = linked_app

        enterprise_policies = _pv_enterprise_policies(props.get("enterprisePolicies"))
        if enterprise_policies:
            patch_body["properties"]["enterprisePolicies"] = enterprise_policies

        # Build linkedEnvironmentMetadata patch if needed.
        linked_patch: dict[str, Any] = {}

        domain_name = _pv_str(props.get("domainName"))
        if domain_name is not None:
            linked_patch["domainName"] = domain_name

        security_group_id = _pv_str(props.get("securityGroupId"))
        if security_group_id is not None:
            linked_patch["securityGroupId"] = security_group_id

        bg_ops = _pv_bool(props.get("backgroundOperationEnabled"))
        if bg_ops is not None:
            linked_patch["backgroundOperationsState"] = "Enabled" if bg_ops else "Disabled"

        if linked_patch:
            patch_body["properties"]["linkedEnvironmentMetadata"] = linked_patch

        result = await self._client.raw.request(
            "PATCH",
            f"{_ADMIN_ENV_PATH}/{env_id}",
            body=patch_body,
            api_version=_BAP_API_VERSION,
        )

        if result is None:
            # Re-read if PATCH returned no body
            result = await self._client.raw.request(
                "GET",
                f"{_ADMIN_ENV_PATH}/{env_id}",
                api_version=_BAP_API_VERSION,
            )

        if result is None:
            raise RuntimeError(f"Failed to update environment {env_id}: API returned no result.")

        return UpdateResponse(properties=_env_to_outputs(result))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete an environment."""
        env_id = request.resource_id
        await self._client.raw.request(
            "DELETE",
            f"{_ADMIN_ENV_PATH}/{env_id}",
            api_version=_BAP_API_VERSION,
        )

    async def _poll_provisioning(self, env_id: str, max_polls: int) -> None:
        """Poll the environment until it reaches a terminal provisioning state."""
        for _ in range(max_polls):
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            try:
                result = await self._client.raw.request(
                    "GET",
                    f"{_ADMIN_ENV_PATH}/{env_id}",
                    api_version=_BAP_API_VERSION,
                )
            except HttpError as exc:
                if exc.status_code == 404:
                    continue  # not yet propagated, keep polling
                raise
            if result is None:
                continue
            state = result.get("properties", {}).get("provisioningState", "")
            if state in _TERMINAL_STATES:
                if state in {"Failed", "Canceled", "Cancelled"}:
                    raise RuntimeError(
                        f"Environment provisioning ended in non-successful terminal state '{state}': {result}"
                    )
                return
        raise RuntimeError(f"Environment provisioning timed out after polling {max_polls} times.")

    async def _wait_for_visibility(self, env_id: str, max_polls: int = _DEFAULT_MAX_POLLS) -> dict:
        """Wait for the environment to become visible on the admin endpoint.

        After creation, the BAP admin GET endpoint may transiently return 404
        before the resource is propagated. Retry until a non-None response is
        returned or max_polls is exhausted.
        """
        for attempt in range(max_polls):
            try:
                result = await self._client.raw.request(
                    "GET",
                    f"{_ADMIN_ENV_PATH}/{env_id}",
                    api_version=_BAP_API_VERSION,
                )
                if result is not None:
                    return result
            except HttpError as exc:
                if exc.status_code != 404:
                    raise
            # 404 or None response — not yet visible, wait and retry
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
        raise RuntimeError(
            f"Environment {env_id} did not become visible on the admin endpoint after {max_polls} polls."
        )


# Input property names (for reconstructing inputs from outputs during read).
_INPUT_PROPS = {
    "displayName", "description", "location", "environmentType",
    "domainName", "currencyCode", "languageCode",
    "azureRegion", "ownerId", "cadence", "billingPolicyId", "environmentGroupId",
    "allowBingSearch", "allowMovingDataAcrossRegions", "securityGroupId",
    "administrationModeEnabled", "backgroundOperationEnabled",
    "templates", "templateMetadata", "linkedAppType", "linkedAppId",
    "enterprisePolicies",
}


def _pv_bool(val: Any) -> bool | None:
    """Extract a bool from a PropertyValue, or None if absent/null."""
    if val is None:
        return None
    raw = val.value if isinstance(val, PropertyValue) else val
    if raw is None:
        return None
    return bool(raw)


def _deep_to_python(val: Any) -> Any:
    """Recursively convert PropertyValue (with tuple/mappingproxy internals) to plain Python."""
    from types import MappingProxyType
    if val is None:
        return None
    if isinstance(val, PropertyValue):
        return _deep_to_python(val.value)
    if isinstance(val, (list, tuple)):
        return [_deep_to_python(item) for item in val]
    if isinstance(val, (dict, MappingProxyType)):
        return {k: _deep_to_python(v) for k, v in val.items()}
    return val


def _pv_list(val: Any) -> list | None:
    """Extract a plain Python list from a PropertyValue, or None if absent/null."""
    result = _deep_to_python(val)
    if isinstance(result, list):
        return result
    return None


def _pv_list_json(val: Any) -> str:
    """Serialize a list PropertyValue to a JSON string for comparison."""
    lst = _pv_list(val)
    if lst is None:
        return "null"
    return json.dumps(lst, sort_keys=True)


def _pv_enterprise_policies(val: Any) -> dict | None:
    """Convert user-facing array of enterprise policies to API named-key structure."""
    policies_list = _pv_list(val)
    if not policies_list:
        return None
    result: dict[str, dict] = {}
    for item in policies_list:
        if not isinstance(item, dict):
            continue
        policy_type = item.get("type", "")
        api_key = _POLICY_TYPE_TO_KEY.get(policy_type)
        if api_key:
            entry: dict[str, str] = {}
            if item.get("id"):
                entry["id"] = item["id"]
            if item.get("location"):
                entry["location"] = item["location"]
            if item.get("systemId"):
                entry["systemId"] = item["systemId"]
            if item.get("status"):
                entry["linkStatus"] = item["status"]
            result[api_key] = entry
    return result or None


def _env_to_outputs(env: dict) -> dict[str, PropertyValue]:
    """Convert a BAP API environment JSON response to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}
    props = env.get("properties", {})

    if props.get("displayName"):
        outputs["displayName"] = PropertyValue(props["displayName"])
    if props.get("description"):
        outputs["description"] = PropertyValue(props["description"])

    location = env.get("location")
    if location:
        outputs["location"] = PropertyValue(location)

    env_sku = props.get("environmentSku")
    if env_sku:
        outputs["environmentType"] = PropertyValue(env_sku)

    if props.get("azureRegion"):
        outputs["azureRegion"] = PropertyValue(props["azureRegion"])

    update_cadence = props.get("updateCadence", {})
    if update_cadence.get("id"):
        outputs["cadence"] = PropertyValue(update_cadence["id"])

    billing_policy = props.get("billingPolicy", {})
    if billing_policy.get("id"):
        outputs["billingPolicyId"] = PropertyValue(billing_policy["id"])

    env_group = props.get("parentEnvironmentGroup", {})
    if env_group.get("id"):
        outputs["environmentGroupId"] = PropertyValue(env_group["id"])

    used_by = props.get("usedBy", {})
    if used_by.get("id"):
        outputs["ownerId"] = PropertyValue(used_by["id"])

    if "bingChatEnabled" in props:
        outputs["allowBingSearch"] = PropertyValue(bool(props["bingChatEnabled"]))

    copilot_policies = props.get("copilotPolicies", {})
    if copilot_policies.get("crossGeoCopilotDataMovementEnabled") is not None:
        outputs["allowMovingDataAcrossRegions"] = PropertyValue(
            bool(copilot_policies["crossGeoCopilotDataMovementEnabled"])
        )

    linked = props.get("linkedEnvironmentMetadata", {})
    if linked.get("domainName"):
        outputs["domainName"] = PropertyValue(linked["domainName"])
    if linked.get("currency", {}).get("code"):
        outputs["currencyCode"] = PropertyValue(linked["currency"]["code"])
    if linked.get("baseLanguage") is not None:
        outputs["languageCode"] = PropertyValue(str(linked["baseLanguage"]))
    if linked.get("securityGroupId"):
        outputs["securityGroupId"] = PropertyValue(linked["securityGroupId"])
    if linked.get("resourceId"):
        outputs["organizationId"] = PropertyValue(linked["resourceId"])
    if linked.get("uniqueName"):
        outputs["uniqueName"] = PropertyValue(linked["uniqueName"])
    if linked.get("version"):
        outputs["dataverseVersion"] = PropertyValue(linked["version"])
    if linked.get("backgroundOperationsState"):
        outputs["backgroundOperationEnabled"] = PropertyValue(
            linked["backgroundOperationsState"] == "Enabled"
        )
    templates = linked.get("template") or linked.get("templates")
    if templates:
        outputs["templates"] = PropertyValue([PropertyValue(t) for t in templates])
    template_metadata = linked.get("templateMetadata")
    if template_metadata:
        if isinstance(template_metadata, dict):
            outputs["templateMetadata"] = PropertyValue(json.dumps(template_metadata))
        else:
            outputs["templateMetadata"] = PropertyValue(str(template_metadata))

    states = props.get("states", {})
    runtime = states.get("runtime", {})
    admin_mode_id = runtime.get("id", "")
    outputs["administrationModeEnabled"] = PropertyValue(admin_mode_id == "AdminMode")

    runtime_code = runtime.get("runtimeReasonCode") or admin_mode_id
    if runtime_code:
        outputs["state"] = PropertyValue(runtime_code)
    elif props.get("provisioningState"):
        outputs["state"] = PropertyValue(props["provisioningState"])

    linked_app = props.get("linkedAppMetadata", {})
    if linked_app.get("type"):
        outputs["linkedAppType"] = PropertyValue(linked_app["type"])
    if linked_app.get("id"):
        outputs["linkedAppId"] = PropertyValue(linked_app["id"])
    if linked_app.get("url"):
        outputs["linkedAppUrl"] = PropertyValue(linked_app["url"])

    if linked.get("instanceUrl"):
        outputs["url"] = PropertyValue(linked["instanceUrl"])

    enterprise_policies_dto = props.get("enterprisePolicies")
    if enterprise_policies_dto:
        policies_out = []
        for api_key, type_name in _POLICY_KEY_TO_TYPE.items():
            policy = enterprise_policies_dto.get(api_key)
            if policy:
                policies_out.append(PropertyValue({
                    "type": PropertyValue(type_name),
                    "id": PropertyValue(policy.get("id", "")),
                    "location": PropertyValue(policy.get("location", "")),
                    "systemId": PropertyValue(policy.get("systemId", "")),
                    "status": PropertyValue(policy.get("linkStatus", "")),
                }))
        if policies_out:
            outputs["enterprisePolicies"] = PropertyValue(policies_out)

    if props.get("createdTime"):
        outputs["createdTime"] = PropertyValue(props["createdTime"])

    if props.get("lastModifiedTime"):
        outputs["lastModifiedTime"] = PropertyValue(props["lastModifiedTime"])

    return outputs
