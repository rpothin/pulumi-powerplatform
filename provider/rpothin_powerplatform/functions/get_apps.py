"""getApps function — lists Power Apps for a Power Platform environment via the SDK."""

from __future__ import annotations

from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from mspp_management.powerapps.environments.item.apps.apps_request_builder import (
    AppsRequestBuilder,
)
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient

_API_VERSION = "2024-10-01"


class GetAppsFunction:
    """Handles the powerplatform:index:getApps invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List Power Apps for a given environment."""
        args = request.args

        env_id_pv = args.get("environmentId")
        if env_id_pv is None or env_id_pv.value is None:
            raise ValueError("environmentId is required.")
        env_id = str(env_id_pv.value)

        query_params = AppsRequestBuilder.AppsRequestBuilderGetQueryParameters(
            api_version=_API_VERSION,
        )
        config = RequestConfiguration(query_parameters=query_params)

        try:
            result = await self._client.sdk.powerapps.environments.by_environment_id(env_id).apps.get(
                request_configuration=config
            )
        except APIError as e:
            raise RuntimeError(
                f"getApps failed with status {e.response_status_code}: {e.message}. "
                f"Response body: {getattr(e, 'response_body', 'unavailable')}"
            ) from e

        app_list: list[PropertyValue] = []
        if result and result.value:
            for app in result.value:
                app_map: dict[str, PropertyValue] = {}
                app_id = getattr(app, "id", None)
                if app_id is not None:
                    app_map["id"] = PropertyValue(app_id)
                app_name = getattr(app, "name", None)
                if app_name is not None:
                    app_map["name"] = PropertyValue(app_name)
                app_display_name = getattr(app, "display_name", None)
                if app_display_name is not None:
                    app_map["displayName"] = PropertyValue(app_display_name)
                app_list.append(PropertyValue(app_map))

        return InvokeResponse(
            return_value={"apps": PropertyValue(app_list)},
        )
