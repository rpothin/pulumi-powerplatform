"""TenantSettings resource handler — singleton tenant settings with sparse drift tracking."""

from __future__ import annotations

import json
from types import MappingProxyType
from typing import Any, Optional

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
from rpothin_powerplatform.utils import HttpError, retry_with_backoff
from rpothin_powerplatform.utils import pv_str as _pv_str

_API_VERSION = "2023-06-01"
_TENANT_PATH = "/providers/Microsoft.BusinessAppPlatform/tenant"
_LIST_TENANT_SETTINGS_PATH = "/providers/Microsoft.BusinessAppPlatform/listTenantSettings"
_UPDATE_TENANT_SETTINGS_PATH = "/providers/Microsoft.BusinessAppPlatform/scopes/admin/updateTenantSettings"

_TENANT_ID_PROP = "tenantId"
_ORIGINAL_SETTINGS_PROP = "_originalSettings"

_ZERO_UUID = "00000000-0000-0000-0000-000000000000"
_ZERO_UUID_KEYS = {
    "powerPlatform.governance.environmentRoutingTargetEnvironmentGroupId",
    "powerPlatform.governance.environmentRoutingTargetSecurityGroupId",
}


class TenantSettingsResource:
    """Handles CRUD operations for powerplatform:index:TenantSettings."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate and normalize tenant settings inputs."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)
        inputs.pop(_ORIGINAL_SETTINGS_PROP, None)

        power_platform = _pv_to_python(inputs.get("powerPlatform"))
        if power_platform is not None and not isinstance(power_platform, dict):
            failures.append(
                CheckFailure(
                    property="powerPlatform",
                    reason="powerPlatform must be an object/map when provided.",
                )
            )

        managed_settings = _normalize_settings_for_state(_managed_settings_from_props(inputs))
        for key in list(inputs.keys()):
            if key in {_TENANT_ID_PROP, _ORIGINAL_SETTINGS_PROP}:
                continue
            inputs.pop(key, None)
        inputs.update(_managed_settings_to_pv_props(managed_settings))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute diffs only for user-managed settings keys."""
        old_settings = _normalize_settings_for_state(_managed_settings_from_props(request.old_state))
        new_settings = _normalize_settings_for_state(_managed_settings_from_props(request.new_inputs))

        old_flat = _flatten_settings(old_settings)
        new_flat = _flatten_settings(new_settings)
        managed_paths = sorted(set(old_flat.keys()) | set(new_flat.keys()))

        changed_paths = [path for path in managed_paths if old_flat.get(path) != new_flat.get(path)]

        detailed: dict[str, PropertyDiff] = {}
        diffs: list[str] = sorted(changed_paths)
        if changed_paths:
            detailed = {
                path: PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True) for path in changed_paths
            }

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed if detailed else None,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create/apply tenant settings and persist baseline for managed keys."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        desired_settings = _normalize_settings_for_state(_managed_settings_from_props(request.properties))
        desired_flat = _flatten_settings(desired_settings)
        managed_paths = sorted(desired_flat.keys())

        tenant_id = await self._get_tenant_id()

        original_settings: dict[str, Any] = {}
        managed_outputs: dict[str, Any] = {}

        if managed_paths:
            current_before = await self._list_tenant_settings()
            original_flat = _select_flat_values(current_before, managed_paths, include_missing=True)
            original_settings = _flat_to_nested(original_flat)

            to_write = _apply_flat_patch(current_before, desired_flat)
            await self._update_tenant_settings(to_write)

            current_after = await self._list_tenant_settings()
            managed_outputs = _flat_to_nested(
                _select_flat_values(current_after, managed_paths, include_missing=True)
            )

        return CreateResponse(
            resource_id=tenant_id,
            properties={
                _TENANT_ID_PROP: PropertyValue(tenant_id),
                **_managed_settings_to_pv_props(managed_outputs),
                _ORIGINAL_SETTINGS_PROP: _python_to_pv(_normalize_settings_for_state(original_settings)),
            },
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read tenant settings and return only user-managed keys."""
        managed_paths = _managed_paths_from_read_request(request)
        baseline = _normalize_settings_for_state(_original_settings_from_props(request.properties))
        tenant_id = request.resource_id

        try:
            current = await self._list_tenant_settings()
            if not tenant_id:
                tenant_id = await self._get_tenant_id()
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        managed_outputs = _flat_to_nested(_select_flat_values(current, managed_paths, include_missing=True))
        outputs = {
            _TENANT_ID_PROP: PropertyValue(tenant_id),
            **_managed_settings_to_pv_props(managed_outputs),
            _ORIGINAL_SETTINGS_PROP: _python_to_pv(baseline),
        }

        inputs = _managed_settings_to_pv_props(managed_outputs)
        return ReadResponse(resource_id=tenant_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update only managed tenant settings keys and preserve deterministic baseline."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        tenant_id = request.resource_id or await self._get_tenant_id()
        desired_settings = _normalize_settings_for_state(_managed_settings_from_props(request.news))
        desired_flat = _flatten_settings(desired_settings)
        managed_paths = sorted(desired_flat.keys())

        original_flat = _flatten_settings(
            _normalize_settings_for_state(_original_settings_from_props(request.olds))
        )
        managed_outputs: dict[str, Any] = {}

        if managed_paths:
            current_before = await self._list_tenant_settings()

            for path, value in _select_flat_values(
                current_before,
                [p for p in managed_paths if p not in original_flat],
                include_missing=True,
            ).items():
                original_flat[path] = value

            to_write = _apply_flat_patch(current_before, desired_flat)
            await self._update_tenant_settings(to_write)

            current_after = await self._list_tenant_settings()
            managed_outputs = _flat_to_nested(
                _select_flat_values(current_after, managed_paths, include_missing=True)
            )

        baseline = _flat_to_nested(original_flat)
        return UpdateResponse(
            properties={
                _TENANT_ID_PROP: PropertyValue(tenant_id),
                **_managed_settings_to_pv_props(managed_outputs),
                _ORIGINAL_SETTINGS_PROP: _python_to_pv(baseline),
            }
        )

    async def delete(self, request: DeleteRequest) -> None:
        """Restore managed keys to their captured baseline values."""
        managed_paths = sorted(_flatten_settings(_managed_settings_from_props(request.properties)).keys())
        if not managed_paths:
            return

        original_flat = _flatten_settings(_original_settings_from_props(request.properties))
        restore_flat = {path: original_flat[path] for path in managed_paths if path in original_flat}
        if not restore_flat:
            return

        current = await self._list_tenant_settings()
        to_write = _apply_flat_patch(current, restore_flat)
        await self._update_tenant_settings(to_write)

    async def _get_tenant_id(self) -> str:
        tenant = await retry_with_backoff(
            lambda: self._client.raw.request("GET", _TENANT_PATH, api_version=_API_VERSION)
        )
        tenant_id = _extract_tenant_id(tenant)
        if not tenant_id:
            raise RuntimeError(f"Failed to resolve tenantId from '{_TENANT_PATH}' response.")
        return tenant_id

    async def _list_tenant_settings(self) -> dict[str, Any]:
        response = await retry_with_backoff(
            lambda: self._client.raw.request(
                "POST",
                _LIST_TENANT_SETTINGS_PATH,
                body={},
                api_version=_API_VERSION,
            )
        )
        settings = _extract_tenant_settings(response)
        if settings is None:
            if response:
                raise RuntimeError(
                    "listTenantSettings returned a non-empty unrecognized response; "
                    "refusing to treat as empty to avoid silently overwriting tenant settings. "
                    f"Top-level keys: {sorted(response.keys())}"
                )
            return {}
        if not isinstance(settings, dict):
            raise RuntimeError("listTenantSettings returned a non-object tenant settings payload.")
        return _normalize_settings_for_state(settings)

    async def _update_tenant_settings(self, settings: dict[str, Any]) -> None:
        settings_for_write = _normalize_settings_for_write(settings)
        primary_body = {"tenantSettings": settings_for_write}
        try:
            await retry_with_backoff(
                lambda: self._client.raw.request(
                    "POST",
                    _UPDATE_TENANT_SETTINGS_PATH,
                    body=primary_body,
                    api_version=_API_VERSION,
                )
            )
            return
        except HttpError as exc:
            if exc.status_code not in (400, 422):
                raise

        fallback_body = {"properties": {"tenantSettings": settings_for_write}}
        await retry_with_backoff(
            lambda: self._client.raw.request(
                "POST",
                _UPDATE_TENANT_SETTINGS_PATH,
                body=fallback_body,
                api_version=_API_VERSION,
            )
        )


def _managed_paths_from_read_request(request: ReadRequest) -> list[str]:
    inputs_settings = _managed_settings_from_props(request.inputs)
    if inputs_settings:
        return sorted(_flatten_settings(_normalize_settings_for_state(inputs_settings)).keys())
    return sorted(_flatten_settings(_managed_settings_from_props(request.properties)).keys())


def _managed_settings_from_props(props: Optional[dict[str, PropertyValue]]) -> dict[str, Any]:
    if props is None:
        return {}
    managed: dict[str, Any] = {}
    for key in sorted(props.keys()):
        if key in {_TENANT_ID_PROP, _ORIGINAL_SETTINGS_PROP}:
            continue
        managed[key] = _pv_to_python(props[key])
    return managed


def _managed_settings_to_pv_props(settings: dict[str, Any]) -> dict[str, PropertyValue]:
    return {key: _python_to_pv(settings[key]) for key in sorted(settings.keys())}


def _original_settings_from_props(props: Optional[dict[str, PropertyValue]]) -> dict[str, Any]:
    if props is None:
        return {}
    original = _pv_to_plain_dict(props.get(_ORIGINAL_SETTINGS_PROP))
    return original or {}


def _extract_tenant_id(tenant_response: Any) -> Optional[str]:
    if isinstance(tenant_response, dict):
        candidates = [
            tenant_response.get("tenantId"),
            tenant_response.get("id"),
            tenant_response.get("name"),
            (tenant_response.get("properties") or {}).get("tenantId"),
            (tenant_response.get("properties") or {}).get("id"),
        ]
        for candidate in candidates:
            tenant_id = _pv_str(PropertyValue(candidate)) if candidate is not None else None
            if tenant_id:
                return tenant_id
    return None


def _extract_tenant_settings(response: Any) -> Any:
    if not isinstance(response, dict):
        return None
    if "tenantSettings" in response:
        return response["tenantSettings"]
    if "settings" in response:
        return response["settings"]
    props = response.get("properties")
    if isinstance(props, dict):
        if "tenantSettings" in props:
            return props["tenantSettings"]
        if "settings" in props:
            return props["settings"]
    value = response.get("value")
    if isinstance(value, dict):
        return _extract_tenant_settings(value)
    if isinstance(value, list) and value:
        for item in value:
            if isinstance(item, dict):
                extracted = _extract_tenant_settings(item)
                if extracted is not None:
                    return extracted
    return None


def _normalize_settings_for_state(settings: dict[str, Any]) -> dict[str, Any]:
    flat = _flatten_settings(settings)
    normalized_flat = {path: _normalize_value_for_state(path, value) for path, value in flat.items()}
    return _flat_to_nested(normalized_flat)


def _normalize_settings_for_write(settings: dict[str, Any]) -> dict[str, Any]:
    flat = _flatten_settings(settings)
    write_flat = {path: _normalize_value_for_write(path, value) for path, value in flat.items()}
    return _flat_to_nested(write_flat)


def _normalize_value_for_state(path: str, value: Any) -> Any:
    if path in _ZERO_UUID_KEYS:
        if value is None:
            return None
        if isinstance(value, str) and value.lower() == _ZERO_UUID:
            return None
    return value


def _normalize_value_for_write(path: str, value: Any) -> Any:
    state_value = _normalize_value_for_state(path, value)
    if path in _ZERO_UUID_KEYS and state_value is None:
        return _ZERO_UUID
    return state_value


def _select_flat_values(
    source_settings: dict[str, Any],
    paths: list[str],
    *,
    include_missing: bool,
) -> dict[str, Any]:
    source_flat = _flatten_settings(_normalize_settings_for_state(source_settings))
    result: dict[str, Any] = {}
    for path in sorted(paths):
        if path in source_flat:
            result[path] = source_flat[path]
        elif include_missing:
            result[path] = None
    return result


def _apply_flat_patch(source_settings: dict[str, Any], patch_flat: dict[str, Any]) -> dict[str, Any]:
    merged_flat = _flatten_settings(_normalize_settings_for_state(source_settings))
    for path, value in sorted(patch_flat.items()):
        merged_flat[path] = value
    return _flat_to_nested(merged_flat)


def _flatten_settings(settings: dict[str, Any], *, _prefix: str = "") -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted(settings.keys()):
        value = settings[key]
        path = f"{_prefix}.{key}" if _prefix else key
        if isinstance(value, dict):
            result.update(_flatten_settings(value, _prefix=path))
        else:
            result[path] = value
    return result


def _flat_to_nested(flat: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for path in sorted(flat.keys()):
        _set_value_by_path(nested, path, flat[path])
    return nested


def _set_value_by_path(target: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    cursor = target
    for part in parts[:-1]:
        next_val = cursor.get(part)
        if not isinstance(next_val, dict):
            next_val = {}
            cursor[part] = next_val
        cursor = next_val
    cursor[parts[-1]] = value


def _pv_to_plain_dict(pv: Optional[PropertyValue]) -> Optional[dict[str, Any]]:
    py = _pv_to_python(pv)
    if py is None:
        return None
    if isinstance(py, dict):
        return py
    return None


def _pv_to_python(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, PropertyValue):
        return _pv_to_python(value.value)
    if isinstance(value, (dict, MappingProxyType)):
        return {str(k): _pv_to_python(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_pv_to_python(v) for v in value]
    return value


def _python_to_pv(value: Any) -> PropertyValue:
    if value is None:
        return PropertyValue(None)
    if isinstance(value, dict):
        ordered = {k: _python_to_pv(value[k]) for k in sorted(value.keys())}
        return PropertyValue(ordered)
    if isinstance(value, list):
        return PropertyValue([_python_to_pv(v) for v in value])
    if isinstance(value, bool):
        return PropertyValue(value)
    if isinstance(value, (float, int)):
        return PropertyValue(value)
    if isinstance(value, str):
        return PropertyValue(value)
    return PropertyValue(json.loads(json.dumps(value)))
