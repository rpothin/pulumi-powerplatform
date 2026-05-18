"""getConnectors function — lists connectors for a Power Platform environment via the SDK."""

from __future__ import annotations

from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from mspp_management.connectivity.environments.item.connectors.connectors_request_builder import (
    ConnectorsRequestBuilder,
)
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient

_API_VERSION = "2024-10-01"


class GetConnectorsFunction:
    """Handles the powerplatform:index:getConnectors invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List connectors for a given environment."""
        args = request.args

        env_id_pv = args.get("environmentId")
        if env_id_pv is None or env_id_pv.value is None:
            raise ValueError("environmentId is required.")
        env_id = str(env_id_pv.value)

        # The kiota URL template uses a non-optional RFC 6570 simple expansion for
        # $filter, so an empty/None filter renders as "$filter=" and causes HTTP 400.
        # Pass the environment filter so the API returns connectors for this environment.
        query_params = ConnectorsRequestBuilder.ConnectorsRequestBuilderGetQueryParameters(
            filter=f"environment eq '{env_id}'",
            api_version=_API_VERSION,
        )
        config = RequestConfiguration(query_parameters=query_params)

        try:
            result = await self._client.sdk.connectivity.environments.by_environment_id(env_id).connectors.get(
                request_configuration=config
            )
        except APIError as e:
            raise RuntimeError(
                f"getConnectors failed with status {e.response_status_code}: {e.message}. "
                f"Response body: {getattr(e, 'response_body', 'unavailable')}"
            ) from e

        connector_list: list[PropertyValue] = []
        if result and result.value:
            for c in result.value:
                c_map: dict[str, PropertyValue] = {}
                c_id = getattr(c, "id", None)
                if c_id is not None:
                    c_map["id"] = PropertyValue(c_id)
                c_name = getattr(c, "name", None)
                if c_name is not None:
                    c_map["name"] = PropertyValue(c_name)
                c_display_name = getattr(c, "display_name", None)
                if c_display_name is not None:
                    c_map["displayName"] = PropertyValue(c_display_name)
                c_type = getattr(c, "type", None)
                if c_type is not None:
                    c_map["type"] = PropertyValue(c_type)
                connector_list.append(PropertyValue(c_map))

        return InvokeResponse(
            return_value={"connectors": PropertyValue(connector_list)},
        )
