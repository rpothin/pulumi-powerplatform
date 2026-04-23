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

# Sub-fields of the `dataverse` block that are immutable after creation.
_DATAVERSE_IMMUTABLE_FIELDS = {"currencyCode", "languageCode", "templates", "templateMetadata"}
# All writable input fields of the `dataverse` block.
_DATAVERSE_INPUT_FIELDS = _DATAVERSE_IMMUTABLE_FIELDS | {
    "domainName", "securityGroupId", "administrationModeEnabled", "backgroundOperationEnabled"
}

# Immutable properties that require replacement when changed.
_REPLACE_PROPS = {"location", "environmentType", "azureRegion", "cadence"}

# Updatable properties.
_UPDATE_PROPS = {
    "displayName",
    "description",
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

        # WARNING 6a: ownerId is only supported for Developer environments.
        owner_id = _pv_str(inputs.get("ownerId"))
        if owner_id and env_type and env_type != "Developer":
            failures.append(
                CheckFailure(
                    property="ownerId",
                    reason="ownerId is only valid for environmentType 'Developer'.",
                )
            )

        dv = _pv_dataverse_dict(inputs.get("dataverse"))
        old_dv = _pv_dataverse_dict(request.old_inputs.get("dataverse"))

        # WARNING 6b: Developer environments cannot have a Dataverse database provisioned.
        if dv is not None and env_type == "Developer":
            failures.append(
                CheckFailure(
                    property="dataverse",
                    reason="The dataverse block is not supported for environmentType 'Developer'.",
                )
            )
        elif dv is not None:
            if not dv.get("currencyCode") and not (old_dv or {}).get("currencyCode"):
                failures.append(
                    CheckFailure(
                        property="dataverse",
                        reason="dataverse.currencyCode is required when dataverse is specified.",
                    )
                )
            if dv.get("languageCode") is None and (old_dv or {}).get("languageCode") is None:
                failures.append(
                    CheckFailure(
                        property="dataverse",
                        reason="dataverse.languageCode is required when dataverse is specified.",
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
            elif prop in {"allowBingSearch", "allowMovingDataAcrossRegions"}:
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

        # Diff the nested dataverse block using only writable input fields.
        old_dv = _pv_dataverse_inputs(old.get("dataverse"))
        new_dv = _pv_dataverse_inputs(new.get("dataverse"))
        if old_dv != new_dv:
            old_immutable = {k: v for k, v in (old_dv or {}).items() if k in _DATAVERSE_IMMUTABLE_FIELDS}
            new_immutable = {k: v for k, v in (new_dv or {}).items() if k in _DATAVERSE_IMMUTABLE_FIELDS}
            # Treat adding/removing Dataverse entirely as replace; also replace on immutable changes.
            if old_dv is None or new_dv is None or old_immutable != new_immutable:
                kind = PropertyDiffKind.UPDATE_REPLACE
            else:
                kind = PropertyDiffKind.UPDATE
            diffs.append("dataverse")
            detailed["dataverse"] = PropertyDiff(kind=kind, input_diff=True)

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

        result = await self._client.raw.request(
            "POST",
            "/providers/Microsoft.BusinessAppPlatform/environments",
            body=body,
            api_version=_BAP_API_VERSION,
        )

        if result is None:
            raise RuntimeError("Failed to create environment: API returned no result.")

        provisioning_state = result.get("properties", {}).get("provisioningState", "")
        env_id = result.get("name", "")
        if not env_id:
            raise RuntimeError("Environment create response did not include an environment id.")

        # Compute per-stage poll budget. Splitting the total timeout across three sequential
        # stages prevents one slow stage from consuming the entire deadline.
        # Shell creation gets 2/3 (usually the fastest), visibility and Dataverse 1/3 each.
        if request.timeout:
            stage_polls = max(1, request.timeout // _POLL_INTERVAL_SECONDS // 3)
        else:
            stage_polls = _DEFAULT_MAX_POLLS // 3  # 10 polls ≈ 100 seconds per stage

        if provisioning_state and provisioning_state not in _TERMINAL_STATES:
            await self._poll_provisioning(env_id, stage_polls * 2)

        # Note: _poll_provisioning() already raises on Failed/Canceled states.
        # The provisioning_state captured above is from the initial POST response and
        # may be stale by the time we reach here. Failure detection is handled by
        # the polling loop above.

        # Wait for environment to be visible before any follow-up calls.
        visible_env = await self._wait_for_visibility(env_id, stage_polls)

        # Step 2: provision Dataverse if requested.
        dv = _pv_dataverse_dict(props.get("dataverse"))
        if dv:
            provision_body: dict[str, Any] = {}
            lang = dv.get("languageCode")
            if lang is not None:
                provision_body["baseLanguage"] = int(lang)
            currency = dv.get("currencyCode")
            if currency:
                provision_body["currency"] = {"code": currency}
            domain = dv.get("domainName")
            if domain:
                provision_body["domainName"] = domain
            sg = dv.get("securityGroupId")
            if sg:
                provision_body["securityGroupId"] = sg
            templates = dv.get("templates")
            if templates:
                provision_body["templates"] = templates
            tmeta = dv.get("templateMetadata")
            if tmeta:
                try:
                    provision_body["templateMetadata"] = json.loads(tmeta)
                except (json.JSONDecodeError, TypeError):
                    provision_body["templateMetadata"] = tmeta

            # BLOCKER 3: wrap provisionInstance in try/except so the environment shell
            # is always returned in CreateResponse. If Dataverse provisioning fails,
            # the env_id is still recorded in Pulumi state; the user can fix the error
            # and run 'pulumi up' again (which will trigger an update to retry).
            try:
                await self._client.raw.request(
                    "POST",
                    f"/providers/Microsoft.BusinessAppPlatform/environments/{env_id}/provisionInstance",
                    body=provision_body,
                    api_version=_BAP_API_VERSION,
                )

                await self._poll_dataverse_provisioning(env_id, stage_polls)
                # Re-read after Dataverse is provisioned.
                final: dict = await self._client.raw.request(
                    "GET",
                    f"{_ADMIN_ENV_PATH}/{env_id}",
                    api_version=_BAP_API_VERSION,
                ) or visible_env

                # WARNING 5: /provisionInstance does not accept administrationModeEnabled or
                # backgroundOperationEnabled — apply them via PATCH after provisioning.
                admin_mode = dv.get("administrationModeEnabled")
                bg_ops = dv.get("backgroundOperationEnabled")
                if admin_mode is not None or bg_ops is not None:
                    post_provision_patch: dict[str, Any] = {"properties": {}}
                    linked_patch: dict[str, Any] = {}
                    if admin_mode:  # Only patch when enabling admin mode; False/default needs no PATCH
                        post_provision_patch["properties"]["states"] = {
                            "runtime": {"id": "AdminMode"}
                        }
                    if bg_ops is not None:
                        linked_patch["backgroundOperationsState"] = "Enabled" if bg_ops else "Disabled"
                    if linked_patch:
                        post_provision_patch["properties"]["linkedEnvironmentMetadata"] = linked_patch
                    patched = await self._client.raw.request(
                        "PATCH",
                        f"{_ADMIN_ENV_PATH}/{env_id}",
                        body=post_provision_patch,
                        api_version=_BAP_API_VERSION,
                    )
                    if patched:
                        final = patched

            except Exception as exc:
                logger.error(
                    "Environment %s was created but Dataverse provisioning failed: %s. "
                    "The environment shell has been recorded in Pulumi state. "
                    "WARNING: The next 'pulumi up' will REPLACE (destroy and recreate) this "
                    "environment to retry Dataverse provisioning — not a safe in-place retry.",
                    env_id,
                    exc,
                )
                final = visible_env
        else:
            final = visible_env

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

        # Build linkedEnvironmentMetadata patch from the dataverse nested block.
        linked_patch: dict[str, Any] = {}
        dv = _pv_dataverse_dict(props.get("dataverse"))
        if dv:
            domain_name = dv.get("domainName")
            if domain_name is not None:
                linked_patch["domainName"] = domain_name
            security_group_id = dv.get("securityGroupId")
            if security_group_id is not None:
                linked_patch["securityGroupId"] = security_group_id
            bg_ops = dv.get("backgroundOperationEnabled")
            if bg_ops is not None:
                linked_patch["backgroundOperationsState"] = "Enabled" if bg_ops else "Disabled"
            admin_mode = dv.get("administrationModeEnabled")
            if admin_mode is not None:
                patch_body["properties"]["states"] = {
                    "runtime": {"id": "AdminMode" if admin_mode else "Enabled"}
                }

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

    async def _poll_dataverse_provisioning(self, env_id: str, max_polls: int) -> None:
        """Poll the environment until Dataverse is provisioned (instanceUrl appears)."""
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
                    continue
                raise
            if result is None:
                continue
            props = result.get("properties", {})
            ps = props.get("provisioningState", "")
            if ps in {"Failed", "Canceled", "Cancelled"}:
                raise RuntimeError(
                    f"Dataverse provisioning ended in non-successful terminal state '{ps}': {result}"
                )
            linked = props.get("linkedEnvironmentMetadata", {})
            if linked.get("instanceUrl") or linked.get("resourceId"):
                return
            logger.debug("Waiting for Dataverse provisioning on %s; current API response: %s", env_id, result)
        raise RuntimeError(
            f"Dataverse provisioning timed out after polling {max_polls} times. "
            f"Last API response is logged at DEBUG level. "
            f"Check the Power Platform admin center for the environment status."
        )



# Input property names (for reconstructing inputs from outputs during read).
_INPUT_PROPS = {
    "displayName", "description", "location", "environmentType",
    "azureRegion", "ownerId", "cadence", "billingPolicyId", "environmentGroupId",
    "allowBingSearch", "allowMovingDataAcrossRegions",
    "linkedAppType", "linkedAppId",
    "enterprisePolicies",
    "dataverse",
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
    """Serialize a list PropertyValue to a JSON string for stable comparison.

    Items that are dicts with a 'type' key are sorted by that key to ensure
    ordering differences (e.g. enterprise policies) don't cause perpetual drift.
    """
    lst = _pv_list(val)
    if lst is None:
        return "null"
    # Normalize list order for dicts with a 'type' key (e.g. enterprisePolicies).
    if lst and isinstance(lst[0], dict) and "type" in lst[0]:
        lst = sorted(lst, key=lambda x: x.get("type", ""))
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


def _pv_dataverse_dict(val: Any) -> dict | None:
    """Extract the dataverse nested block as a plain Python dict, or None if absent."""
    d = _deep_to_python(val)
    if not isinstance(d, dict):
        return None
    return d if d else None


def _pv_dataverse_inputs(val: Any) -> dict | None:
    """Extract only writable input fields from the dataverse block (excludes computed outputs)."""
    d = _pv_dataverse_dict(val)
    if d is None:
        return None
    result = {k: v for k, v in d.items() if k in _DATAVERSE_INPUT_FIELDS}
    return result if result else None


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

    # Build the nested dataverse block — only when Dataverse is actually provisioned.
    linked = props.get("linkedEnvironmentMetadata", {})
    if linked.get("resourceId") or linked.get("instanceUrl"):
        dv_out: dict[str, PropertyValue] = {}
        if linked.get("domainName"):
            dv_out["domainName"] = PropertyValue(linked["domainName"])
        if linked.get("currency", {}).get("code"):
            dv_out["currencyCode"] = PropertyValue(linked["currency"]["code"])
        if linked.get("baseLanguage") is not None:
            # PropertyValue does not accept int; store as float. Using int() first
            # ensures no fractional part (e.g. 1033.0, never 1033.5).
            dv_out["languageCode"] = PropertyValue(float(int(linked["baseLanguage"])))
        if linked.get("securityGroupId"):
            dv_out["securityGroupId"] = PropertyValue(linked["securityGroupId"])
        if linked.get("resourceId"):
            dv_out["organizationId"] = PropertyValue(linked["resourceId"])
        if linked.get("uniqueName"):
            dv_out["uniqueName"] = PropertyValue(linked["uniqueName"])
        if linked.get("version"):
            dv_out["version"] = PropertyValue(linked["version"])
        if linked.get("instanceUrl"):
            dv_out["url"] = PropertyValue(linked["instanceUrl"])
        templates = linked.get("template") or linked.get("templates")
        if templates:
            dv_out["templates"] = PropertyValue([PropertyValue(t) for t in templates])
        template_metadata = linked.get("templateMetadata")
        if template_metadata:
            if isinstance(template_metadata, dict):
                dv_out["templateMetadata"] = PropertyValue(json.dumps(template_metadata))
            else:
                dv_out["templateMetadata"] = PropertyValue(str(template_metadata))
        # Only emit backgroundOperationEnabled when explicitly enabled — emitting False
        # unconditionally causes perpetual drift when the user hasn't set this field.
        if linked.get("backgroundOperationsState") == "Enabled":
            dv_out["backgroundOperationEnabled"] = PropertyValue(True)
        states = props.get("states", {})
        admin_mode_id = states.get("runtime", {}).get("id", "")
        # BLOCKER 1: only emit administrationModeEnabled when the API reports admin mode
        # is active. Emitting False unconditionally causes perpetual drift when the user
        # has not specified this field (state has False, inputs have nothing → diff fires).
        if admin_mode_id == "AdminMode":
            dv_out["administrationModeEnabled"] = PropertyValue(True)
        if dv_out:
            outputs["dataverse"] = PropertyValue(dv_out)

    states = props.get("states", {})
    runtime = states.get("runtime", {})
    rc = runtime.get("runtimeReasonCode")
    runtime_code = (rc if rc and rc != "NotSpecified" else None) or runtime.get("id")
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
        # WARNING 4: sort by type name so output order is stable regardless of
        # API iteration order, preventing perpetual drift in diff().
        def _policy_sort_key(pv: PropertyValue) -> str:
            d = _deep_to_python(pv)
            return d.get("type", "") if isinstance(d, dict) else ""
        policies_out.sort(key=_policy_sort_key)
        if policies_out:
            outputs["enterprisePolicies"] = PropertyValue(policies_out)

    if props.get("createdTime"):
        outputs["createdTime"] = PropertyValue(props["createdTime"])

    if props.get("lastModifiedTime"):
        outputs["lastModifiedTime"] = PropertyValue(props["lastModifiedTime"])

    return outputs
