"""PipelineSharing resource: grants Dataverse pipeline access to a team."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from pulumi.provider.experimental.property_value import Computed, PropertyValue
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

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import HttpError, resolve_dataverse_url
from rpothin_powerplatform.utils import pv_str as _pv_str

_ENV_PROP = "environmentId"
_PIPELINE_PROP = "pipelineId"
_TEAM_PROP = "teamId"
_ACCESS_MASK_PROP = "accessMask"
_GRANTED_ACCESS_MASK_PROP = "grantedAccessMask"
_DEFAULT_ACCESS_MASK = "ReadAccess"
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class PipelineSharingResource:
    """Handles the ``powerplatform:index:PipelineSharing`` resource."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate required immutable inputs and apply defaults."""
        inputs = dict(request.new_inputs)
        failures: list[CheckFailure] = []

        _normalize_guid(inputs, _ENV_PROP, failures)
        _normalize_guid(inputs, _PIPELINE_PROP, failures)
        _normalize_guid(inputs, _TEAM_PROP, failures)

        access_mask_pv = inputs.get(_ACCESS_MASK_PROP)
        if access_mask_pv is None or not isinstance(access_mask_pv.value, Computed):
            # Only apply the default when the value is known; preserve Computed as-is
            access_mask = _pv_str(access_mask_pv) or _DEFAULT_ACCESS_MASK
            inputs[_ACCESS_MASK_PROP] = PropertyValue(access_mask)

        return CheckResponse(inputs=inputs, failures=failures or None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """All input changes require replacement."""
        diffs: list[str] = []
        replaces: list[str] = []
        detailed_diff: dict[str, PropertyDiff] = {}

        for prop in (_ENV_PROP, _PIPELINE_PROP, _TEAM_PROP):
            new_pv = request.new_inputs.get(prop)
            # Unknown during preview — skip comparison, validate at create time
            if new_pv is not None and isinstance(new_pv.value, Computed):
                continue
            old_value = _normalized_value(request.old_state, prop)
            new_value = _normalized_value(request.new_inputs, prop)
            if old_value != new_value:
                diffs.append(prop)
                replaces.append(prop)
                detailed_diff[prop] = PropertyDiff(
                    kind=PropertyDiffKind.UPDATE_REPLACE,
                    input_diff=True,
                )

        new_access_pv = request.new_inputs.get(_ACCESS_MASK_PROP)
        if new_access_pv is None or not isinstance(new_access_pv.value, Computed):
            old_access_mask = _normalized_access_mask(request.old_state)
            new_access_mask = _normalized_access_mask(request.new_inputs)
            if old_access_mask != new_access_mask:
                diffs.append(_ACCESS_MASK_PROP)
                replaces.append(_ACCESS_MASK_PROP)
                detailed_diff[_ACCESS_MASK_PROP] = PropertyDiff(
                    kind=PropertyDiffKind.UPDATE_REPLACE,
                    input_diff=True,
                )

        return DiffResponse(
            changes=bool(diffs),
            delete_before_replace=True if diffs else False,
            diffs=diffs,
            replaces=replaces or None,
            detailed_diff=detailed_diff or None,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Grant team access to the deployment pipeline."""
        props = dict(request.properties)

        if request.preview:
            # Preserve Computed (unknown) values in outputs rather than stringifying them.
            env_pv = props.get(_ENV_PROP, PropertyValue(None))
            pipeline_pv = props.get(_PIPELINE_PROP, PropertyValue(None))
            team_pv = props.get(_TEAM_PROP, PropertyValue(None))
            access_mask_pv = props.get(_ACCESS_MASK_PROP)
            if access_mask_pv is None or isinstance(access_mask_pv.value, Computed):
                access_mask_pv = PropertyValue(_DEFAULT_ACCESS_MASK)
            return CreateResponse(
                resource_id="preview-id",
                properties={
                    _ENV_PROP: env_pv,
                    _PIPELINE_PROP: pipeline_pv,
                    _TEAM_PROP: team_pv,
                    _ACCESS_MASK_PROP: access_mask_pv,
                    _GRANTED_ACCESS_MASK_PROP: access_mask_pv,
                },
            )

        env_id = _pv_str(props.get(_ENV_PROP))
        pipeline_id = _pv_str(props.get(_PIPELINE_PROP))
        team_id = _pv_str(props.get(_TEAM_PROP))
        access_mask = _normalized_access_mask(props)
        resource_id = f"{env_id}/{pipeline_id}/{team_id}"

        outputs = {
            _ENV_PROP: PropertyValue(env_id),
            _PIPELINE_PROP: PropertyValue(pipeline_id),
            _TEAM_PROP: PropertyValue(team_id),
            _ACCESS_MASK_PROP: PropertyValue(access_mask),
            _GRANTED_ACCESS_MASK_PROP: PropertyValue(access_mask),
        }

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)
        await dv_client.request(
            "POST",
            "/api/data/v9.0/GrantAccess",
            body={
                "Target": {
                    "deploymentpipelineid": pipeline_id,
                    "@odata.type": "Microsoft.Dynamics.CRM.deploymentpipeline",
                },
                "PrincipalAccess": {
                    "Principal": {
                        "teamid": team_id,
                        "@odata.type": "Microsoft.Dynamics.CRM.team",
                    },
                    "AccessMask": access_mask,
                },
            },
            api_version=None,
        )

        return CreateResponse(resource_id=resource_id, properties=outputs)

    async def update(self, request) -> None:
        """Not supported — all property changes require replacement (see diff)."""
        raise NotImplementedError(
            "PipelineSharing is immutable; all changes require replacement."
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Return stored state; this resource does not support drift detection."""
        props = dict(request.properties)
        env_id, pipeline_id, team_id = _resolve_ids(request)
        access_mask = _pv_str(props.get(_ACCESS_MASK_PROP)) or _normalized_access_mask(request.inputs)
        granted_access_mask = _pv_str(props.get(_GRANTED_ACCESS_MASK_PROP)) or access_mask

        inputs = {
            _ENV_PROP: PropertyValue(env_id),
            _PIPELINE_PROP: PropertyValue(pipeline_id),
            _TEAM_PROP: PropertyValue(team_id),
            _ACCESS_MASK_PROP: PropertyValue(access_mask),
        }
        outputs = {
            **inputs,
            _GRANTED_ACCESS_MASK_PROP: PropertyValue(granted_access_mask),
        }
        return ReadResponse(resource_id=request.resource_id, properties=outputs, inputs=inputs)

    async def delete(self, request: DeleteRequest) -> None:
        """Revoke team access from the deployment pipeline."""
        env_id, pipeline_id, team_id = _resolve_ids(request)

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            return

        dv_client = self._make_dataverse_client(instance_url)
        try:
            await dv_client.request(
                "POST",
                "/api/data/v9.0/RevokeAccess",
                body={
                    "Target": {
                        "deploymentpipelineid": pipeline_id,
                        "@odata.type": "Microsoft.Dynamics.CRM.deploymentpipeline",
                    },
                    "Revokee": {
                        "teamid": team_id,
                        "@odata.type": "Microsoft.Dynamics.CRM.team",
                    },
                },
                api_version=None,
            )
        except HttpError as exc:
            if exc.status_code != 404:
                raise

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        parsed = urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )


def _normalize_guid(inputs: dict[str, PropertyValue], prop: str, failures: list[CheckFailure]) -> str | None:
    value_pv = inputs.get(prop)
    if value_pv is None:
        failures.append(CheckFailure(property=prop, reason=f"{prop} is required and cannot be empty."))
        return None
    if isinstance(value_pv.value, Computed):
        # Unknown during preview — defer GUID validation to create time
        return None
    value = _pv_str(value_pv)
    if not value:
        failures.append(CheckFailure(property=prop, reason=f"{prop} is required and cannot be empty."))
        return None
    if not _UUID_RE.match(value):
        failures.append(CheckFailure(property=prop, reason=f"{prop} must be a valid UUID/GUID, got: {value!r}."))
        return None
    lowered = value.lower()
    inputs[prop] = PropertyValue(lowered)
    return lowered


def _normalized_value(values: dict[str, PropertyValue], prop: str) -> str | None:
    value = _pv_str(values.get(prop))
    return value.lower() if value else None


def _normalized_access_mask(values: dict[str, PropertyValue]) -> str:
    return _pv_str(values.get(_ACCESS_MASK_PROP)) or _DEFAULT_ACCESS_MASK


def _resolve_ids(request: ReadRequest | DeleteRequest) -> tuple[str, str, str]:
    inputs = getattr(request, "inputs", {}) or {}
    env_id = _pv_str(request.properties.get(_ENV_PROP)) or _pv_str(inputs.get(_ENV_PROP))
    pipeline_id = _pv_str(request.properties.get(_PIPELINE_PROP)) or _pv_str(inputs.get(_PIPELINE_PROP))
    team_id = _pv_str(request.properties.get(_TEAM_PROP)) or _pv_str(inputs.get(_TEAM_PROP))
    if env_id and pipeline_id and team_id:
        return env_id, pipeline_id, team_id

    parts = request.resource_id.split("/", 2)
    if len(parts) != 3:
        raise ValueError(f"Invalid pipeline sharing resource ID: {request.resource_id!r}")
    return parts[0], parts[1], parts[2]
