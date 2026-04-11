"""Environment Backup resource handler — create/read/delete via the Power Platform Management SDK."""

from __future__ import annotations

from mspp_management.models.create_backup_request import CreateBackupRequest
from mspp_management.models.environment_backup import EnvironmentBackup as EnvironmentBackupModel
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
from pulumi_powerplatform.utils import retry_with_backoff


class EnvironmentBackupResource:
    """Handles CRUD operations for powerplatform:index:EnvironmentBackup."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for an environment backup."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        if not env_id:
            failures.append(CheckFailure(
                property="environmentId",
                reason="environmentId is required and cannot be empty.",
            ))

        label = _pv_str(inputs.get("label"))
        if not label:
            failures.append(CheckFailure(property="label", reason="label is required and cannot be empty."))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for an environment backup."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        old = request.old_state
        new = request.new_inputs

        # Backups are immutable — any input change requires replacement.
        for prop in ("environmentId", "label"):
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
        """Create a new environment backup."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties
        env_id = _pv_str(props.get("environmentId")) or ""

        body = CreateBackupRequest()
        body.label = _pv_str(props.get("label"))

        result = await retry_with_backoff(
            lambda: self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).backups.post(body)
        )
        if result is None:
            raise RuntimeError("Failed to create environment backup: API returned no result.")

        backup_id = str(result.id) if result.id else ""
        resource_id = f"{env_id}/{backup_id}"

        return CreateResponse(
            resource_id=resource_id,
            properties=_backup_to_outputs(env_id, result),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of an environment backup."""
        env_id, backup_id = _parse_resource_id(request.resource_id)

        env_backups = self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).backups
        result = await retry_with_backoff(lambda: env_backups.by_backup_id(backup_id).get())

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _backup_to_outputs(env_id, result)
        inputs = {k: v for k, v in outputs.items() if k in ("environmentId", "label")}
        return ReadResponse(resource_id=request.resource_id, properties=outputs, inputs=inputs)

    async def delete(self, request: DeleteRequest) -> None:
        """Delete an environment backup."""
        env_id, backup_id = _parse_resource_id(request.resource_id)
        env_backups = self._client.sdk.environmentmanagement.environments.by_environment_id(env_id).backups
        await retry_with_backoff(lambda: env_backups.by_backup_id(backup_id).delete())


def _parse_resource_id(resource_id: str) -> tuple[str, str]:
    """Parse a composite resource ID of the form '{environmentId}/{backupId}'."""
    parts = resource_id.split("/", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid environment backup resource ID: "
            f"expected '{{environmentId}}/{{backupId}}', got '{resource_id}'"
        )
    return parts[0], parts[1]


def _backup_to_outputs(env_id: str, backup: EnvironmentBackupModel) -> dict[str, PropertyValue]:
    """Convert an EnvironmentBackup SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {
        "environmentId": PropertyValue(env_id),
    }

    if backup.label is not None:
        outputs["label"] = PropertyValue(backup.label)
    if backup.backup_point_date_time is not None:
        outputs["backupPointDateTime"] = PropertyValue(backup.backup_point_date_time.isoformat())
    if backup.backup_expiry_date_time is not None:
        outputs["backupExpiryDateTime"] = PropertyValue(backup.backup_expiry_date_time.isoformat())

    return outputs
