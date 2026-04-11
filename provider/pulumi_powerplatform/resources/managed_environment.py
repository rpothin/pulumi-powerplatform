"""Managed Environment resource handler — enable/disable toggle via the Power Platform Management SDK."""

from __future__ import annotations

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
)

from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.utils import pv_str as _pv_str


class ManagedEnvironmentResource:
    """Handles CRUD operations for powerplatform:index:ManagedEnvironment."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for a managed environment."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        if not env_id:
            failures.append(CheckFailure(
                property="environmentId",
                reason="environmentId is required and cannot be empty.",
            ))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for a managed environment."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        old = request.old_state
        new = request.new_inputs

        # Changing environmentId requires replacement.
        if _pv_str(old.get("environmentId")) != _pv_str(new.get("environmentId")):
            diffs.append("environmentId")
            detailed["environmentId"] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)
            replaces.append("environmentId")

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
            replaces=replaces if replaces else None,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Enable managed environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties
        env_id = _pv_str(props.get("environmentId")) or ""

        gov = self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).governancesetting
        await gov.enablemanaged.post()

        outputs: dict[str, PropertyValue] = {
            "environmentId": PropertyValue(env_id),
            "enabled": PropertyValue(True),
        }
        return CreateResponse(resource_id=env_id, properties=outputs)

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of a managed environment."""
        env_id = request.resource_id
        result = await self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).get()

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        protection_level = getattr(result, "protection_level", None)
        is_managed = protection_level is not None and str(protection_level).lower() == "managed"

        if not is_managed:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs: dict[str, PropertyValue] = {
            "environmentId": PropertyValue(env_id),
            "enabled": PropertyValue(True),
        }
        inputs = {"environmentId": PropertyValue(env_id)}
        return ReadResponse(resource_id=env_id, properties=outputs, inputs=inputs)

    async def delete(self, request: DeleteRequest) -> None:
        """Disable managed environment."""
        env_id = request.resource_id
        gov = self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).governancesetting
        await gov.disablemanaged.post()
