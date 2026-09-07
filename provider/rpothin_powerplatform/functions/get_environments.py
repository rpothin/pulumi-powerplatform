"""getEnvironments function — lists Power Platform environments via the SDK."""

from __future__ import annotations

import json
from typing import Optional

from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from mspp_management.environmentmanagement.environments.environments_request_builder import (
    EnvironmentsRequestBuilder,
)
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.utils import HttpError

_API_VERSION = "2024-10-01"
_BAP_API_VERSION = "2021-04-01"
_BAP_ENVIRONMENTS_PATH = "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments"


class GetEnvironmentsFunction:
    """Handles the powerplatform:index:getEnvironments invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List environments with optional OData filtering."""
        args = request.args

        odata_filter: Optional[str] = None
        top: Optional[int] = None

        filter_pv = args.get("filter")
        if filter_pv is not None and filter_pv.value is not None:
            odata_filter = str(filter_pv.value)

        top_pv = args.get("top")
        if top_pv is not None and top_pv.value is not None:
            top = int(top_pv.value)

        query_params = EnvironmentsRequestBuilder.EnvironmentsRequestBuilderGetQueryParameters(
            filter=odata_filter,
            top=top,
            api_version=_API_VERSION,
        )
        config = RequestConfiguration(query_parameters=query_params)

        try:
            result = await self._client.sdk.environmentmanagement.environments.get(request_configuration=config)
        except APIError as e:
            if _is_unauthorized_app_error(e):
                try:
                    result = await self._client.raw.request(
                        "GET",
                        _BAP_ENVIRONMENTS_PATH,
                        api_version=_BAP_API_VERSION,
                        query_params={"$filter": odata_filter, "$top": top},
                    )
                except HttpError as fallback_error:
                    raise RuntimeError(
                        f"getEnvironments failed with status {e.response_status_code}: {e.message}. "
                        f"Response body: {getattr(e, 'response_body', 'unavailable')}. "
                        f"BAP fallback failed with status {fallback_error.status_code}: {fallback_error}"
                    ) from fallback_error
            else:
                raise RuntimeError(
                    f"getEnvironments failed with status {e.response_status_code}: {e.message}. "
                    f"Response body: {getattr(e, 'response_body', 'unavailable')}"
                ) from e

        env_list: list[PropertyValue] = []
        environments = result.value if not isinstance(result, dict) and result else (result or {}).get("value")
        if environments:
            for env in environments:
                env_list.append(PropertyValue(_environment_map(env)))

        return InvokeResponse(
            return_value={"environments": PropertyValue(env_list)},
        )


def _is_unauthorized_app_error(error: APIError) -> bool:
    """Return whether the SDK response is the known authorized-app rejection."""
    if error.response_status_code != 403:
        return False
    body = getattr(error, "response_body", None)
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return False
    return (
        isinstance(body, dict)
        and body.get("code") == "ForbiddenAccess"
        and "Caller is not an authorized app" in str(body.get("message", ""))
    )


def _environment_map(env: object) -> dict[str, PropertyValue]:
    """Map either SDK or BAP environment data to the invoke output contract."""
    if isinstance(env, dict):
        properties = env.get("properties") or {}
        linked = properties.get("linkedEnvironmentMetadata") or {}
        values = {
            "id": env.get("id") or env.get("name"),
            "displayName": properties.get("displayName"),
            "domainName": linked.get("domainName") or properties.get("domainName"),
            "state": properties.get("state") or properties.get("states"),
            "type": properties.get("environmentType") or properties.get("environmentSku"),
            "url": linked.get("instanceUrl") or properties.get("instanceUrl"),
            "geo": properties.get("geo") or env.get("location"),
            "azureRegion": properties.get("azureRegion") or env.get("location"),
            "securityGroupId": properties.get("securityGroupId"),
            "tenantId": linked.get("tenantId") or properties.get("tenantId"),
            "environmentGroupId": properties.get("environmentGroupId"),
            "dataverseId": linked.get("uniqueName") or properties.get("dataverseId"),
            "version": linked.get("version") or properties.get("version"),
        }
    else:
        values = {
            "id": getattr(env, "id", None),
            "displayName": getattr(env, "display_name", None),
            "domainName": getattr(env, "domain_name", None),
            "state": getattr(env, "state", None),
            "type": getattr(env, "type", None),
            "url": getattr(env, "url", None),
            "geo": getattr(env, "geo", None),
            "azureRegion": getattr(env, "azure_region", None),
            "securityGroupId": getattr(env, "security_group_id", None),
            "tenantId": getattr(env, "tenant_id", None),
            "environmentGroupId": getattr(env, "environment_group_id", None),
            "dataverseId": getattr(env, "dataverse_id", None),
            "version": getattr(env, "version", None),
        }
    return {key: PropertyValue(value) for key, value in values.items() if value is not None}
