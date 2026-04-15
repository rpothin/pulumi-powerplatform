"""getEnvironments function — lists Power Platform environments via the SDK."""

from __future__ import annotations

from typing import Optional

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
        )
        config = RequestConfiguration(query_parameters=query_params)

        result = await self._client.sdk.environmentmanagement.environments.get(request_configuration=config)

        env_list: list[PropertyValue] = []
        if result and result.value:
            for env in result.value:
                env_map: dict[str, PropertyValue] = {}
                if env.id is not None:
                    env_map["id"] = PropertyValue(env.id)
                if env.display_name is not None:
                    env_map["displayName"] = PropertyValue(env.display_name)
                if env.domain_name is not None:
                    env_map["domainName"] = PropertyValue(env.domain_name)
                if env.state is not None:
                    env_map["state"] = PropertyValue(env.state)
                if env.type is not None:
                    env_map["type"] = PropertyValue(env.type)
                if env.url is not None:
                    env_map["url"] = PropertyValue(env.url)
                if env.geo is not None:
                    env_map["geo"] = PropertyValue(env.geo)
                if env.azure_region is not None:
                    env_map["azureRegion"] = PropertyValue(env.azure_region)
                if env.security_group_id is not None:
                    env_map["securityGroupId"] = PropertyValue(env.security_group_id)
                if env.tenant_id is not None:
                    env_map["tenantId"] = PropertyValue(env.tenant_id)
                if env.environment_group_id is not None:
                    env_map["environmentGroupId"] = PropertyValue(env.environment_group_id)
                if env.dataverse_id is not None:
                    env_map["dataverseId"] = PropertyValue(env.dataverse_id)
                if env.version is not None:
                    env_map["version"] = PropertyValue(env.version)

                env_list.append(PropertyValue(env_map))

        return InvokeResponse(
            return_value={"environments": PropertyValue(env_list)},
        )
