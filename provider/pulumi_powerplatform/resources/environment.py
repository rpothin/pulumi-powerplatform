"""Environment resource handler — full CRUD via the Power Platform BAP admin API."""

from __future__ import annotations

import asyncio
import logging

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

logger = logging.getLogger(__name__)

_VALID_ENV_TYPES = {"Sandbox", "Production", "Trial", "Developer", "Default"}

# Immutable properties that require replacement when changed.
_REPLACE_PROPS = {"location", "environmentType"}

# Updatable properties.
_UPDATE_PROPS = {"displayName", "description", "domainName"}

_BAP_API_VERSION = "2021-04-01"

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
        body = {
            "properties": {
                "displayName": _pv_str(props.get("displayName")),
                "description": _pv_str(props.get("description")) or "",
                "environmentSku": _pv_str(props.get("environmentType")),
            },
            "location": _pv_str(props.get("location")),
        }

        domain_name = _pv_str(props.get("domainName"))
        if domain_name:
            body["properties"]["linkedEnvironmentMetadata"] = {"domainName": domain_name}

        currency_code = _pv_str(props.get("currencyCode"))
        language_code = _pv_str(props.get("languageCode"))
        if currency_code or language_code:
            linked = body["properties"].setdefault("linkedEnvironmentMetadata", {})
            if currency_code:
                linked["currency"] = {"code": currency_code}
            if language_code:
                linked["baseLanguage"] = int(language_code)

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

        if provisioning_state and provisioning_state not in _TERMINAL_STATES:
            # Poll until terminal state
            max_polls = max(1, request.timeout // _POLL_INTERVAL_SECONDS) if request.timeout else _DEFAULT_MAX_POLLS
            await self._poll_provisioning(env_id, max_polls)

        if provisioning_state == "Failed":
            raise RuntimeError(f"Environment creation failed: {result}")

        # Fetch the final environment state via the admin read endpoint
        final = await self._client.raw.request(
            "GET",
            f"/scopes/admin/environments/{env_id}",
            api_version=_BAP_API_VERSION,
        )

        if final is None:
            raise RuntimeError("Failed to read newly created environment.")

        return CreateResponse(
            resource_id=env_id,
            properties=_env_to_outputs(final),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of an environment."""
        env_id = request.resource_id

        from pulumi_powerplatform.utils import HttpError

        try:
            result = await self._client.raw.request(
                "GET",
                f"/scopes/admin/environments/{env_id}",
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
        """Update an existing environment (display name, description, domain)."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        env_id = request.resource_id
        props = request.news

        patch_body: dict = {"properties": {}}
        display_name = _pv_str(props.get("displayName"))
        if display_name is not None:
            patch_body["properties"]["displayName"] = display_name

        description = _pv_str(props.get("description"))
        if description is not None:
            patch_body["properties"]["description"] = description

        result = await self._client.raw.request(
            "PATCH",
            f"/providers/Microsoft.BusinessAppPlatform/environments/{env_id}",
            body=patch_body,
            api_version=_BAP_API_VERSION,
        )

        if result is None:
            # Re-read if PATCH returned no body
            result = await self._client.raw.request(
                "GET",
                f"/scopes/admin/environments/{env_id}",
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
            f"/providers/Microsoft.BusinessAppPlatform/environments/{env_id}",
            api_version=_BAP_API_VERSION,
        )

    async def _poll_provisioning(self, env_id: str, max_polls: int) -> None:
        """Poll the environment until it reaches a terminal provisioning state."""
        for _ in range(max_polls):
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            result = await self._client.raw.request(
                "GET",
                f"/scopes/admin/environments/{env_id}",
                api_version=_BAP_API_VERSION,
            )
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


# Input property names (for reconstructing inputs from outputs during read).
_INPUT_PROPS = {
    "displayName", "description", "location", "environmentType",
    "domainName", "currencyCode", "languageCode",
}


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

    linked = props.get("linkedEnvironmentMetadata", {})
    if linked.get("domainName"):
        outputs["domainName"] = PropertyValue(linked["domainName"])
    if linked.get("currency", {}).get("code"):
        outputs["currencyCode"] = PropertyValue(linked["currency"]["code"])
    if linked.get("baseLanguage") is not None:
        outputs["languageCode"] = PropertyValue(str(linked["baseLanguage"]))

    state = props.get("states", {}).get("runtime", {}).get("runtimeReasonCode")
    if not state:
        state = props.get("provisioningState")
    if state:
        outputs["state"] = PropertyValue(state)

    if props.get("linkedEnvironmentMetadata", {}).get("instanceUrl"):
        outputs["url"] = PropertyValue(linked["instanceUrl"])

    if props.get("createdTime"):
        outputs["createdTime"] = PropertyValue(props["createdTime"])

    if props.get("lastModifiedTime"):
        outputs["lastModifiedTime"] = PropertyValue(props["lastModifiedTime"])

    return outputs
