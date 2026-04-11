"""Environment Group resource handler — full CRUD via the Power Platform Management SDK."""

from __future__ import annotations

from uuid import UUID

from mspp_management.models.environment_group import EnvironmentGroup
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


class EnvironmentGroupResource:
    """Handles CRUD operations for powerplatform:index:EnvironmentGroup."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for an environment group."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        display_name = _pv_str(inputs.get("displayName"))
        if not display_name:
            failures.append(CheckFailure(property="displayName", reason="displayName is required and cannot be empty."))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for an environment group."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}

        old = request.old_state
        new = request.new_inputs

        for prop in ("displayName", "description", "parentGroupId"):
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
        """Create a new environment group."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties

        body = EnvironmentGroup()
        body.display_name = _pv_str(props.get("displayName"))
        body.description = _pv_str(props.get("description"))
        parent_id = _pv_str(props.get("parentGroupId"))
        if parent_id:
            body.parent_group_id = UUID(parent_id)

        result = await self._client.sdk.environmentmanagement.environment_groups.post(body)
        if result is None:
            raise RuntimeError("Failed to create environment group: API returned no result.")

        group_id = str(result.id) if result.id else ""
        return CreateResponse(
            resource_id=group_id,
            properties=_group_to_outputs(result),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of an environment group."""
        group_id = request.resource_id
        result = await self._client.sdk.environmentmanagement.environment_groups.by_group_id(group_id).get()

        if result is None:
            # Resource no longer exists.
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _group_to_outputs(result)
        # Reconstruct inputs from the outputs (input properties only).
        inputs = {
            k: v for k, v in outputs.items() if k in ("displayName", "description", "parentGroupId")
        }
        return ReadResponse(resource_id=group_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update an existing environment group."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        group_id = request.resource_id
        props = request.news

        body = EnvironmentGroup()
        body.display_name = _pv_str(props.get("displayName"))
        body.description = _pv_str(props.get("description"))
        parent_id = _pv_str(props.get("parentGroupId"))
        if parent_id:
            body.parent_group_id = UUID(parent_id)

        result = await self._client.sdk.environmentmanagement.environment_groups.by_group_id(group_id).put(body)
        if result is None:
            raise RuntimeError(f"Failed to update environment group {group_id}: API returned no result.")

        return UpdateResponse(properties=_group_to_outputs(result))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete an environment group."""
        group_id = request.resource_id
        await self._client.sdk.environmentmanagement.environment_groups.by_group_id(group_id).delete()


def _group_to_outputs(group: EnvironmentGroup) -> dict[str, PropertyValue]:
    """Convert an EnvironmentGroup SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}

    if group.display_name is not None:
        outputs["displayName"] = PropertyValue(group.display_name)
    if group.description is not None:
        outputs["description"] = PropertyValue(group.description)
    if group.parent_group_id is not None:
        outputs["parentGroupId"] = PropertyValue(str(group.parent_group_id))
    if group.created_time is not None:
        outputs["createdTime"] = PropertyValue(group.created_time.isoformat())
    if group.last_modified_time is not None:
        outputs["lastModifiedTime"] = PropertyValue(group.last_modified_time.isoformat())

    return outputs
