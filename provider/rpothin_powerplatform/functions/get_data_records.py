"""getDataRecords function — queries Dataverse records via OData."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest, InvokeResponse

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import pv_str as _pv_str
from rpothin_powerplatform.utils import pv_to_python, resolve_dataverse_url

logger = logging.getLogger(__name__)


class GetDataRecordsFunction:
    """Handles the ``powerplatform:index:getDataRecords`` invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """Query Dataverse records with optional OData parameters.

        Returns the first page of results. If the server includes an
        ``@odata.nextLink``, a warning is logged; use the ``top`` parameter to
        control page size when processing large tables.
        """
        args = request.args

        env_id = _pv_str(args.get("environmentId"))
        table_name = _pv_str(args.get("tableLogicalName"))

        if not env_id or not table_name:
            raise ValueError("environmentId and tableLogicalName are required.")

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)

        # Resolve the OData collection name
        entity_meta = await dv_client.request(
            "GET",
            f"/api/data/v9.2/EntityDefinitions(LogicalName='{table_name}')?$select=LogicalCollectionName",
            api_version=None,
        )
        collection = entity_meta["LogicalCollectionName"]

        # Build query string
        params: list[str] = []

        odata_filter = _pv_str(args.get("filter"))
        if odata_filter:
            params.append(f"$filter={odata_filter}")

        select_pv = args.get("select")
        if select_pv is not None and select_pv.value is not None:
            select_cols = pv_to_python(select_pv)
            if isinstance(select_cols, list):
                params.append(f"$select={','.join(str(c) for c in select_cols)}")

        orderby = _pv_str(args.get("orderby"))
        if orderby:
            params.append(f"$orderby={orderby}")

        top_pv = args.get("top")
        if top_pv is not None and top_pv.value is not None:
            params.append(f"$top={int(top_pv.value)}")

        expand_pv = args.get("expand")
        expand_list = pv_to_python(expand_pv) if expand_pv is not None else None
        if expand_list and isinstance(expand_list, list):
            expand_clauses: list[str] = []
            for exp in expand_list:
                if not isinstance(exp, dict):
                    continue
                nav_prop = exp.get("navigationProperty", "")
                if not nav_prop:
                    continue
                parts: list[str] = []
                sel = exp.get("select")
                if sel:
                    parts.append(f"$select={sel}")
                flt = exp.get("filter")
                if flt:
                    parts.append(f"$filter={flt}")
                if parts:
                    expand_clauses.append(f"{nav_prop}({';'.join(parts)})")
                else:
                    expand_clauses.append(nav_prop)
            if expand_clauses:
                params.append(f"$expand={','.join(expand_clauses)}")

        query_string = "&".join(params)
        path = f"/api/data/v9.2/{collection}"
        if query_string:
            path = f"{path}?{query_string}"

        result = await dv_client.request("GET", path, api_version=None) or {}

        if "@odata.nextLink" in result:
            logger.warning(
                "getDataRecords: response contains @odata.nextLink — "
                "only the first page of results was returned. "
                "Use the 'top' parameter to control page size."
            )

        records: list[Any] = result.get("value", [])
        records_pv = PropertyValue([_record_to_pv(r) for r in records])

        return InvokeResponse(return_value={"records": records_pv})

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        """Create a RawApiClient scoped to the given Dataverse instance URL."""
        parsed = urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )


def _record_to_pv(record: Any) -> PropertyValue:
    """Recursively convert a plain record dict to a PropertyValue."""
    if record is None:
        return PropertyValue(None)
    if isinstance(record, (bool, int, float, str)):
        return PropertyValue(record)
    if isinstance(record, dict):
        return PropertyValue({k: _record_to_pv(v) for k, v in record.items()})
    if isinstance(record, list):
        return PropertyValue([_record_to_pv(item) for item in record])
    return PropertyValue(str(record))
