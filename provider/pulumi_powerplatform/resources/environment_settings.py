"""EnvironmentSettings resource handler — manage settings on a Power Platform environment."""

from __future__ import annotations

import logging
from typing import Optional

import pulumi
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

# Settings properties that can be managed.
_SETTINGS_PROPS = (
    "maxUploadFileSize",
    "pluginTraceLogSetting",
    "isAuditEnabled",
    "isUserAccessAuditEnabled",
    "isActivityLoggingEnabled",
)

_PP_API_VERSION = "2022-03-01-preview"


class EnvironmentSettingsResource:
    """Handles CRUD operations for powerplatform:index:EnvironmentSettings."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for environment settings."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        if not env_id:
            failures.append(
                CheckFailure(property="environmentId", reason="environmentId is required and cannot be empty.")
            )

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for environment settings."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}

        old = request.old_state
        new = request.new_inputs

        # environmentId is immutable
        old_env_id = _pv_str(old.get("environmentId"))
        new_env_id = _pv_str(new.get("environmentId"))
        if old_env_id != new_env_id:
            diffs.append("environmentId")
            detailed["environmentId"] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)

        for prop in _SETTINGS_PROPS:
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
        """Apply settings to an environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties
        env_id = _pv_str(props.get("environmentId"))
        if not env_id:
            raise RuntimeError("environmentId is required.")

        settings_body = _build_settings_body(props)

        if settings_body:
            await self._client.raw_pp.request(
                "PATCH",
                f"/environmentmanagement/environments/{env_id}/settings",
                body=settings_body,
                api_version=_PP_API_VERSION,
            )

        # Read back the current settings
        current = await self._read_settings(env_id)
        outputs = _settings_to_outputs(env_id, current)

        # Use environmentId as the resource ID
        return CreateResponse(resource_id=env_id, properties=outputs)

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current settings of an environment."""
        env_id = request.resource_id

        from pulumi_powerplatform.utils import HttpError

        try:
            current = await self._read_settings(env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        outputs = _settings_to_outputs(env_id, current)
        inputs = {k: v for k, v in outputs.items() if k in _INPUT_PROP_NAMES}
        return ReadResponse(resource_id=env_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update settings on an environment."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        env_id = request.resource_id
        props = request.news

        settings_body = _build_settings_body(props)

        if settings_body:
            await self._client.raw_pp.request(
                "PATCH",
                f"/environmentmanagement/environments/{env_id}/settings",
                body=settings_body,
                api_version=_PP_API_VERSION,
            )

        current = await self._read_settings(env_id)
        return UpdateResponse(properties=_settings_to_outputs(env_id, current))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete is a no-op for environment settings (cannot unset settings)."""
        pulumi.warn(
            f"EnvironmentSettings for environment {request.resource_id} cannot be deleted. "
            "Settings will be removed from Pulumi state only — they remain active on the environment."
        )

    async def _read_settings(self, env_id: str) -> Optional[dict]:
        """Read current settings from the API."""
        return await self._client.raw_pp.request(
            "GET",
            f"/environmentmanagement/environments/{env_id}/settings",
            api_version=_PP_API_VERSION,
        )


_INPUT_PROP_NAMES = {"environmentId"} | set(_SETTINGS_PROPS)


def _build_settings_body(props: dict[str, PropertyValue]) -> dict:
    """Build the PATCH body from input properties."""
    body: dict = {}
    for prop in _SETTINGS_PROPS:
        val = _pv_str(props.get(prop))
        if val is not None:
            # Try to convert boolean-like and numeric values
            if val.lower() in ("true", "false"):
                body[prop] = val.lower() == "true"
            else:
                try:
                    body[prop] = int(val)
                except ValueError:
                    body[prop] = val
    return body


def _settings_to_outputs(env_id: str, settings: Optional[dict]) -> dict[str, PropertyValue]:
    """Convert API settings response to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {
        "environmentId": PropertyValue(env_id),
    }

    if settings is None:
        return outputs

    for prop in _SETTINGS_PROPS:
        val = settings.get(prop)
        if val is not None:
            if isinstance(val, bool):
                outputs[prop] = PropertyValue(str(val).lower())
            else:
                outputs[prop] = PropertyValue(str(val))

    return outputs
