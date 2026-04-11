"""Role Assignment resource handler — create/read/delete via the Power Platform Management SDK."""

from __future__ import annotations

from typing import Optional

from mspp_management.models.role_assignment_request import RoleAssignmentRequest
from mspp_management.models.role_assignment_response import RoleAssignmentResponse
from mspp_management.models.role_assignment_response_value import RoleAssignmentResponse_value
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


def _pv_str(pv: Optional[PropertyValue]) -> Optional[str]:
    """Extract a string from a PropertyValue, returning None if null/missing."""
    if pv is None or pv.value is None:
        return None
    return str(pv.value)


class RoleAssignmentResource:
    """Handles CRUD operations for powerplatform:index:RoleAssignment."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for a role assignment."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        principal_object_id = _pv_str(inputs.get("principalObjectId"))
        if not principal_object_id:
            failures.append(CheckFailure(
                property="principalObjectId",
                reason="principalObjectId is required and cannot be empty.",
            ))

        principal_type = _pv_str(inputs.get("principalType"))
        if not principal_type:
            failures.append(CheckFailure(
                property="principalType",
                reason="principalType is required and cannot be empty.",
            ))

        role_definition_id = _pv_str(inputs.get("roleDefinitionId"))
        if not role_definition_id:
            failures.append(CheckFailure(
                property="roleDefinitionId",
                reason="roleDefinitionId is required and cannot be empty.",
            ))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for a role assignment."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        old = request.old_state
        new = request.new_inputs

        # Role assignments are immutable — any input change requires replacement.
        for prop in ("principalObjectId", "principalType", "roleDefinitionId", "scope"):
            old_val = _pv_str(old.get(prop))
            new_val = _pv_str(new.get(prop))
            if old_val != new_val:
                diffs.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)
                replaces.append(prop)

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
            replaces=replaces if replaces else None,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create a new role assignment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties

        body = RoleAssignmentRequest()
        body.principal_object_id = _pv_str(props.get("principalObjectId"))
        body.principal_type = _pv_str(props.get("principalType"))
        body.role_definition_id = _pv_str(props.get("roleDefinitionId"))
        body.scope = _pv_str(props.get("scope"))

        result = await self._client.sdk.authorization.role_assignments.post(body)
        if result is None:
            raise RuntimeError("Failed to create role assignment: API returned no result.")

        value = _first_value(result)
        role_assignment_id = str(value.role_assignment_id) if value.role_assignment_id else ""

        return CreateResponse(
            resource_id=role_assignment_id,
            properties=_role_assignment_to_outputs(value),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of a role assignment."""
        assignment_id = request.resource_id
        result = await self._client.sdk.authorization.role_assignments.by_role_assignment_id(assignment_id).get()

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        value = _first_value(result)
        outputs = _role_assignment_to_outputs(value)
        inputs = {
            k: v for k, v in outputs.items()
            if k in ("principalObjectId", "principalType", "roleDefinitionId", "scope")
        }
        return ReadResponse(resource_id=assignment_id, properties=outputs, inputs=inputs)

    async def delete(self, request: DeleteRequest) -> None:
        """Delete a role assignment."""
        assignment_id = request.resource_id
        await self._client.sdk.authorization.role_assignments.by_role_assignment_id(assignment_id).delete()


def _first_value(response: RoleAssignmentResponse) -> RoleAssignmentResponse_value:
    """Extract the first value item from a RoleAssignmentResponse."""
    if response.value and len(response.value) > 0:
        return response.value[0]
    raise RuntimeError("RoleAssignmentResponse contained no value items.")


def _role_assignment_to_outputs(value: RoleAssignmentResponse_value) -> dict[str, PropertyValue]:
    """Convert a RoleAssignmentResponse_value SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}

    if value.principal_object_id is not None:
        outputs["principalObjectId"] = PropertyValue(str(value.principal_object_id))
    if value.principal_type is not None:
        outputs["principalType"] = PropertyValue(str(value.principal_type))
    if value.role_definition_id is not None:
        outputs["roleDefinitionId"] = PropertyValue(str(value.role_definition_id))
    if value.scope is not None:
        outputs["scope"] = PropertyValue(str(value.scope))
    if value.created_on is not None:
        outputs["createdOn"] = PropertyValue(value.created_on.isoformat())

    return outputs
