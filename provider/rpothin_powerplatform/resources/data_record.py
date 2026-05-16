"""DataRecord resource: manages a generic Dataverse table record via OData."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

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
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import HttpError, pv_to_python, resolve_dataverse_url
from rpothin_powerplatform.utils import pv_str as _pv_str

logger = logging.getLogger(__name__)

_ENV_PROP = "environmentId"
_TABLE_PROP = "tableLogicalName"
_COLUMNS_PROP = "columns"
_DISABLE_PROP = "disableOnDestroy"
_RECORD_ID_PROP = "dataRecordId"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
# Dataverse table/column logical names: lowercase letters, digits, underscore.
_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# ---- Entity metadata cache (per-operation, not shared across calls) -----


class _MetaCache:
    """Lightweight per-operation cache for Dataverse entity metadata."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, str]] = {}

    async def get(self, dv_client: RawApiClient, table_name: str) -> dict[str, str]:
        """Return ``{primaryIdAttribute, logicalCollectionName}`` for *table_name*."""
        if table_name not in self._cache:
            result = await dv_client.request(
                "GET",
                (
                    f"/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')"
                    "?$select=PrimaryIdAttribute,LogicalCollectionName"
                ),
                api_version=None,
            )
            self._cache[table_name] = {
                "primaryIdAttribute": result["PrimaryIdAttribute"],
                "logicalCollectionName": result["LogicalCollectionName"],
            }
        return self._cache[table_name]


# ---- Column helpers --------------------------------------------------------


def _is_lookup(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and "tableLogicalName" in value
        and "dataRecordId" in value
    )


def _is_m2m(value: Any) -> bool:
    return isinstance(value, list)


async def _encode_columns_create(
    meta: _MetaCache, dv_client: RawApiClient, cols: dict[str, Any]
) -> dict[str, Any]:
    """Encode columns dict into a Dataverse POST body (M2M entries excluded)."""
    body: dict[str, Any] = {}
    for key, value in cols.items():
        if _is_m2m(value):
            continue  # handled via $ref after create
        if _is_lookup(value):
            related_meta = await meta.get(dv_client, value["tableLogicalName"])
            collection = related_meta["logicalCollectionName"]
            body[f"{key}@odata.bind"] = f"/{collection}({value['dataRecordId']})"
        else:
            body[key] = value  # scalar or None (JSON null)
    return body


async def _encode_columns_patch(
    meta: _MetaCache,
    dv_client: RawApiClient,
    new_cols: dict[str, Any],
    old_cols: dict[str, Any],
) -> dict[str, Any]:
    """Encode changed columns into a Dataverse PATCH body (M2M excluded)."""
    body: dict[str, Any] = {}
    for key, new_value in new_cols.items():
        old_value = old_cols.get(key)
        if _is_m2m(new_value) or _is_m2m(old_value):
            continue  # handled via $ref operations
        if _is_lookup(new_value):
            related_meta = await meta.get(dv_client, new_value["tableLogicalName"])
            collection = related_meta["logicalCollectionName"]
            body[f"{key}@odata.bind"] = f"/{collection}({new_value['dataRecordId']})"
        elif new_value is None and _is_lookup(old_value):
            # Clearing a lookup requires the @odata.bind style
            body[f"{key}@odata.bind"] = None
        elif new_value != old_value:
            body[key] = new_value  # scalar that actually changed
    # Handle columns that were in old but not in new (being removed → set to null)
    for key, old_value in old_cols.items():
        if key in new_cols:
            continue
        if _is_m2m(old_value):
            continue
        if _is_lookup(old_value):
            body[f"{key}@odata.bind"] = None
        else:
            body[key] = None
    return body


def _m2m_set(items: list[Any]) -> set[tuple[str, str]]:
    """Normalize an M2M list to a frozenset of (tableLogicalName_lower, id_lower) tuples."""
    result: set[tuple[str, str]] = set()
    for item in items:
        if _is_lookup(item):
            result.add((item["tableLogicalName"].lower(), item["dataRecordId"].lower()))
    return result


async def _apply_m2m_diff(
    meta: _MetaCache,
    dv_client: RawApiClient,
    collection: str,
    record_id: str,
    nav_prop: str,
    old_items: list[Any],
    new_items: list[Any],
    instance_base: str,
) -> None:
    """Add or remove M2M $ref entries based on set diff."""
    old_set = _m2m_set(old_items)
    new_set = _m2m_set(new_items)

    # Build lookup-normalised → original item map for adds
    new_by_key = {
        (item["tableLogicalName"].lower(), item["dataRecordId"].lower()): item
        for item in new_items
        if _is_lookup(item)
    }

    # Add new relationships
    for key in new_set - old_set:
        item = new_by_key[key]
        related_meta = await meta.get(dv_client, item["tableLogicalName"])
        related_collection = related_meta["logicalCollectionName"]
        related_id = item["dataRecordId"]
        await dv_client.request(
            "POST",
            f"/api/data/v9.2/{collection}({record_id})/{nav_prop}/$ref",
            body={
                "@odata.id": f"{instance_base}/api/data/v9.2/{related_collection}({related_id})"
            },
            api_version=None,
        )

    # Remove deleted relationships
    for tbl_lower, id_lower in old_set - new_set:
        # Find original ID (preserve case for URL)
        orig_id = next(
            (item["dataRecordId"] for item in old_items
             if _is_lookup(item)
             and item["tableLogicalName"].lower() == tbl_lower
             and item["dataRecordId"].lower() == id_lower),
            id_lower,
        )
        await dv_client.request(
            "DELETE",
            f"/api/data/v9.2/{collection}({record_id})/{nav_prop}({orig_id})/$ref",
            api_version=None,
        )


def _build_select(cols: dict[str, Any]) -> Optional[str]:
    """Build a ``$select`` query string for the given columns.

    Lookup fields are requested via the ``_{name}_value`` alternate key
    (returns the GUID without expanding the related entity).
    M2M (list) columns are excluded — they are queried separately.
    """
    fields: list[str] = []
    for key, value in cols.items():
        if _is_m2m(value):
            continue
        if _is_lookup(value):
            fields.append(f"_{key}_value")
        else:
            fields.append(key)
    return ",".join(fields) if fields else None


async def _reconstruct_columns(
    meta: _MetaCache,
    dv_client: RawApiClient,
    collection: str,
    record_id: str,
    record_data: dict[str, Any],
    reference_cols: dict[str, Any],
) -> dict[str, Any]:
    """Rebuild the columns dict from a Dataverse GET response.

    ``reference_cols`` is the previously stored columns dict; it carries
    the ``tableLogicalName`` information needed to reconstruct lookup/M2M
    entries (Dataverse only returns GUIDs, not type names).
    """
    result: dict[str, Any] = {}
    for key, ref_value in reference_cols.items():
        if _is_m2m(ref_value):
            # Determine the related entity from the first stored item
            if ref_value and _is_lookup(ref_value[0]):
                related_table = ref_value[0]["tableLogicalName"]
                related_meta = await meta.get(dv_client, related_table)
                primary_id = related_meta["primaryIdAttribute"]
                nav_response = await dv_client.request(
                    "GET",
                    f"/api/data/v9.2/{collection}({record_id})/{key}?$select={primary_id}",
                    api_version=None,
                )
                items = (nav_response or {}).get("value", [])
                result[key] = [
                    {"tableLogicalName": related_table, "dataRecordId": str(r[primary_id])}
                    for r in items
                ]
            else:
                result[key] = []
        elif _is_lookup(ref_value):
            guid = record_data.get(f"_{key}_value")
            if guid is not None:
                result[key] = {
                    "tableLogicalName": ref_value["tableLogicalName"],
                    "dataRecordId": str(guid),
                }
            else:
                result[key] = None
        else:
            result[key] = record_data.get(key)
    return result


def _extract_record_id(post_result: Any, headers: dict[str, str], primary_id_attr: str) -> Optional[str]:
    """Extract the new record GUID from a Dataverse POST response."""
    # 201 with body
    if isinstance(post_result, dict) and primary_id_attr in post_result:
        return str(post_result[primary_id_attr]).lower()
    # 204 with OData-EntityId header
    entity_id_header = headers.get("odata-entityid") or headers.get("OData-EntityId") or ""
    match = re.search(
        r"\(([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\)",
        entity_id_header,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower()
    return None


# ---- Resource handler ------------------------------------------------------


class DataRecordResource:
    """Handles CRUD for ``powerplatform:index:DataRecord``."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for a DataRecord resource."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get(_ENV_PROP))
        table_name = _pv_str(inputs.get(_TABLE_PROP))

        if not env_id:
            failures.append(CheckFailure(
                property=_ENV_PROP, reason="environmentId is required and cannot be empty."
            ))
        elif not _UUID_RE.match(env_id):
            failures.append(CheckFailure(
                property=_ENV_PROP,
                reason=f"environmentId must be a valid UUID/GUID, got: {env_id!r}.",
            ))
        else:
            inputs[_ENV_PROP] = PropertyValue(env_id.lower())
            env_id = env_id.lower()

        if not table_name:
            failures.append(CheckFailure(
                property=_TABLE_PROP, reason="tableLogicalName is required and cannot be empty."
            ))
        elif not _IDENTIFIER_RE.match(table_name):
            failures.append(CheckFailure(
                property=_TABLE_PROP,
                reason=f"tableLogicalName must be a lowercase Dataverse logical name, got: {table_name!r}.",
            ))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute diff; environmentId and tableLogicalName trigger replacement."""
        old = request.old_state
        new = request.new_inputs

        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        for prop in (_ENV_PROP, _TABLE_PROP):
            if _pv_str(old.get(prop)) != _pv_str(new.get(prop)):
                diffs.append(prop)
                replaces.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)

        old_cols_str = _cols_comparable(old.get(_COLUMNS_PROP))
        new_cols_str = _cols_comparable(new.get(_COLUMNS_PROP))
        if old_cols_str != new_cols_str:
            diffs.append(_COLUMNS_PROP)
            detailed[_COLUMNS_PROP] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        old_disable = _pv_str(old.get(_DISABLE_PROP))
        new_disable = _pv_str(new.get(_DISABLE_PROP))
        if old_disable != new_disable:
            diffs.append(_DISABLE_PROP)
            detailed[_DISABLE_PROP] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        if diffs:
            return DiffResponse(changes=True, diffs=diffs, detailed_diff=detailed, replaces=replaces or None)
        return DiffResponse(changes=False, diffs=[], detailed_diff=None)

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create a Dataverse record."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        env_id = _pv_str(request.properties.get(_ENV_PROP))
        table_name = _pv_str(request.properties.get(_TABLE_PROP))
        cols = pv_to_python(request.properties.get(_COLUMNS_PROP)) or {}
        disable_on_destroy = bool(
            (request.properties.get(_DISABLE_PROP) or PropertyValue(False)).value
        )

        if not env_id or not table_name:
            raise ValueError("environmentId and tableLogicalName are required.")

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)
        instance_base = instance_url.rstrip("/")
        meta = _MetaCache()

        parent_meta = await meta.get(dv_client, table_name)
        collection = parent_meta["logicalCollectionName"]
        primary_id_attr = parent_meta["primaryIdAttribute"]

        body = await _encode_columns_create(meta, dv_client, cols)

        post_result, resp_headers = await dv_client.request(
            "POST",
            f"/api/data/v9.2/{collection}",
            body=body,
            api_version=None,
            return_headers=True,
        )

        record_id = _extract_record_id(post_result, resp_headers, primary_id_attr)
        if not record_id:
            raise RuntimeError(
                f"Could not determine record ID after creating {table_name!r} record. "
                "POST succeeded but neither the response body nor OData-EntityId header "
                "contained a recognisable GUID."
            )

        # Wire up M2M relationships
        for nav_prop, items in cols.items():
            if _is_m2m(items) and items:
                await _apply_m2m_diff(
                    meta, dv_client, collection, record_id, nav_prop, [], items, instance_base
                )

        return CreateResponse(
            resource_id=record_id,
            properties=_build_output_properties(env_id, table_name, cols, disable_on_destroy, record_id),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Refresh a DataRecord's state from Dataverse."""
        record_id = request.resource_id
        old_props = request.properties

        env_id = _pv_str(old_props.get(_ENV_PROP))
        table_name = _pv_str(old_props.get(_TABLE_PROP))
        old_cols = pv_to_python(old_props.get(_COLUMNS_PROP)) or {}
        disable_on_destroy = bool(
            (old_props.get(_DISABLE_PROP) or PropertyValue(False)).value
        )

        if not env_id or not table_name:
            return ReadResponse(resource_id="", properties={}, inputs={})

        try:
            instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        if not instance_url:
            return ReadResponse(resource_id="", properties={}, inputs={})

        dv_client = self._make_dataverse_client(instance_url)
        meta = _MetaCache()

        parent_meta = await meta.get(dv_client, table_name)
        collection = parent_meta["logicalCollectionName"]

        select_str = _build_select(old_cols)
        path = f"/api/data/v9.2/{collection}({record_id})"
        if select_str:
            path = f"{path}?$select={select_str}"

        try:
            record_data = await dv_client.request("GET", path, api_version=None) or {}
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        cols = await _reconstruct_columns(meta, dv_client, collection, record_id, record_data, old_cols)
        props = _build_output_properties(env_id, table_name, cols, disable_on_destroy, record_id)
        inputs = {k: v for k, v in props.items() if k != _RECORD_ID_PROP}
        return ReadResponse(resource_id=record_id, properties=props, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Apply column changes to an existing Dataverse record."""
        record_id = request.resource_id
        env_id = _pv_str(request.news.get(_ENV_PROP))
        table_name = _pv_str(request.news.get(_TABLE_PROP))
        new_cols = pv_to_python(request.news.get(_COLUMNS_PROP)) or {}
        old_cols = pv_to_python(request.olds.get(_COLUMNS_PROP)) or {}
        disable_on_destroy = bool(
            (request.news.get(_DISABLE_PROP) or PropertyValue(False)).value
        )

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)  # type: ignore[arg-type]
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)
        instance_base = instance_url.rstrip("/")
        meta = _MetaCache()

        parent_meta = await meta.get(dv_client, table_name)  # type: ignore[arg-type]
        collection = parent_meta["logicalCollectionName"]

        # Scalar / lookup PATCH
        patch_body = await _encode_columns_patch(meta, dv_client, new_cols, old_cols)
        if patch_body:
            await dv_client.request(
                "PATCH",
                f"/api/data/v9.2/{collection}({record_id})",
                body=patch_body,
                api_version=None,
            )

        # M2M diff
        all_nav_props = set(k for k, v in new_cols.items() if _is_m2m(v)) | \
                        set(k for k, v in old_cols.items() if _is_m2m(v))
        for nav_prop in all_nav_props:
            old_items = old_cols.get(nav_prop, []) if _is_m2m(old_cols.get(nav_prop)) else []
            new_items = new_cols.get(nav_prop, []) if _is_m2m(new_cols.get(nav_prop)) else []
            await _apply_m2m_diff(
                meta, dv_client, collection, record_id, nav_prop, old_items, new_items, instance_base
            )

        return UpdateResponse(
            properties=_build_output_properties(env_id, table_name, new_cols, disable_on_destroy, record_id)
        )

    async def delete(self, request: DeleteRequest) -> None:
        """Delete a Dataverse record, optionally deactivating it first."""
        record_id = request.resource_id
        props = request.properties

        env_id = _pv_str(props.get(_ENV_PROP))
        table_name = _pv_str(props.get(_TABLE_PROP))
        disable_on_destroy = bool((props.get(_DISABLE_PROP) or PropertyValue(False)).value)

        if not env_id or not table_name:
            return

        try:
            instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return
            raise

        if not instance_url:
            return

        dv_client = self._make_dataverse_client(instance_url)
        meta = _MetaCache()
        parent_meta = await meta.get(dv_client, table_name)
        collection = parent_meta["logicalCollectionName"]

        if disable_on_destroy:
            try:
                await dv_client.request(
                    "PATCH",
                    f"/api/data/v9.2/{collection}({record_id})",
                    body={"statecode": 1},
                    api_version=None,
                )
            except HttpError as exc:
                if exc.status_code == 404:
                    return
                raise

        try:
            await dv_client.request(
                "DELETE",
                f"/api/data/v9.2/{collection}({record_id})",
                api_version=None,
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return
            raise

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        """Create a RawApiClient scoped to the given Dataverse instance URL."""
        parsed = urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )


# ---- Helpers ---------------------------------------------------------------


def _cols_comparable(pv: Optional[PropertyValue]) -> str:
    """Stable JSON string for deep column equality comparison."""
    import json
    return json.dumps(pv_to_python(pv), sort_keys=True, default=str)


def _build_output_properties(
    env_id: str,
    table_name: str,
    cols: dict[str, Any],
    disable_on_destroy: bool,
    record_id: str,
) -> dict[str, PropertyValue]:
    """Build the Pulumi output properties dict for a DataRecord."""
    props: dict[str, PropertyValue] = {
        _ENV_PROP: PropertyValue(env_id),
        _TABLE_PROP: PropertyValue(table_name),
        _RECORD_ID_PROP: PropertyValue(record_id),
        _DISABLE_PROP: PropertyValue(disable_on_destroy),
    }
    if cols:
        props[_COLUMNS_PROP] = _cols_to_pv(cols)
    return props


def _cols_to_pv(cols: dict[str, Any]) -> PropertyValue:
    """Recursively convert a columns dict to a PropertyValue map."""
    return PropertyValue({k: _any_to_pv(v) for k, v in cols.items()})


def _any_to_pv(value: Any) -> PropertyValue:
    if value is None:
        return PropertyValue(None)
    if isinstance(value, (bool, int, float, str)):
        return PropertyValue(value)
    if isinstance(value, dict):
        return PropertyValue({k: _any_to_pv(v) for k, v in value.items()})
    if isinstance(value, list):
        return PropertyValue([_any_to_pv(item) for item in value])
    return PropertyValue(str(value))
