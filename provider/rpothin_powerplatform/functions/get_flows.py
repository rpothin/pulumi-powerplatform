"""getFlows function — lists Cloud Flows via the Dataverse workflow table (category=5)."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import HttpError as _HttpError
from rpothin_powerplatform.utils import pv_str as _pv_str
from rpothin_powerplatform.utils import pv_to_python, resolve_dataverse_url

logger = logging.getLogger(__name__)

# Cloud flows have category=5 in the Dataverse workflow table.
_CATEGORY_FILTER = "category eq 5"
# Columns required to build the output; always merged even when caller passes select.
_REQUIRED_SELECT = frozenset({"workflowid", "name", "statecode"})
_DEFAULT_SELECT = ",".join(sorted(_REQUIRED_SELECT))


class GetFlowsFunction:
    """Handles the powerplatform:index:getFlows invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List Cloud Flows for a given environment via Dataverse.

        Queries the Dataverse ``workflow`` entity table filtered to
        ``category eq 5`` (Modern Flow / Cloud Flow). This approach works
        with service principal credentials and does not require a per-user
        Power Automate license.

        Returns the first page of results. If the server includes an
        ``@odata.nextLink``, a warning is logged; use the ``top`` parameter to
        control page size when processing environments with large numbers of flows.
        """
        args = request.args

        env_id = _pv_str(args.get("environmentId"))
        if not env_id:
            raise ValueError("environmentId is required.")

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)

        # Build OData query parameters
        params: list[str] = []

        # Filter: always restrict to cloud flows; parenthesize any caller-supplied clause.
        extra_filter = _pv_str(args.get("filter"))
        odata_filter = f"{_CATEGORY_FILTER} and ({extra_filter})" if extra_filter else _CATEGORY_FILTER
        params.append(f"$filter={odata_filter}")

        # Select: merge required columns with any caller-supplied list.
        select_pv = args.get("select")
        if select_pv is not None and select_pv.value is not None:
            caller_cols = pv_to_python(select_pv)
            if isinstance(caller_cols, list):
                merged = sorted(_REQUIRED_SELECT | {str(c) for c in caller_cols})
                params.append(f"$select={','.join(merged)}")
            else:
                params.append(f"$select={_DEFAULT_SELECT}")
        else:
            params.append(f"$select={_DEFAULT_SELECT}")

        top_pv = args.get("top")
        if top_pv is not None and top_pv.value is not None:
            params.append(f"$top={int(top_pv.value)}")

        params.append("$count=true")

        path = f"/api/data/v9.2/workflows?{'&'.join(params)}"

        try:
            result = await dv_client.request("GET", path, api_version=None) or {}
        except _HttpError as e:
            if e.status_code == 403 and (
                "0x80072560" in str(e) or "not a member of the organization" in str(e).lower()
            ):
                raise RuntimeError(
                    "Service principal is not a Dataverse organization member (HTTP 403, code 0x80072560). "
                    "Add the service principal as an Application User in the target Dataverse environment "
                    "and assign a security role with read access to the workflow entity."
                ) from e
            raise RuntimeError(
                f"getFlows Dataverse query failed with HTTP {e.status_code}: {e}"
            ) from e

        if "@odata.nextLink" in result:
            logger.warning(
                "getFlows: response contains @odata.nextLink — "
                "only the first page of results was returned. "
                "Use the 'top' parameter to control page size."
            )

        flow_list: list[PropertyValue] = []
        for record in result.get("value", []):
            flow_id = str(record.get("workflowid", ""))
            flow_name = str(record.get("name", ""))
            state_code = record.get("statecode")
            flow_map: dict[str, PropertyValue] = {
                "id": PropertyValue(flow_id),
                "name": PropertyValue(flow_name),
                "displayName": PropertyValue(flow_name),
                "stateCode": PropertyValue(float(state_code) if state_code is not None else 0.0),
            }
            flow_list.append(PropertyValue(flow_map))

        total_rows_count = result.get("@odata.count", 0)
        limit_exceeded = bool(result.get("@Microsoft.Dynamics.CRM.totalrecordcountlimitexceeded", False))

        return InvokeResponse(
            return_value={
                "flows": PropertyValue(flow_list),
                "totalRowsCount": PropertyValue(float(total_rows_count)),
                "totalRowsCountLimitExceeded": PropertyValue(bool(limit_exceeded)),
            }
        )

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        """Create a RawApiClient scoped to the given Dataverse instance URL."""
        parsed = urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )
