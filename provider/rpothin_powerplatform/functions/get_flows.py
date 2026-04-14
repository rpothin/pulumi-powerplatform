"""getFlows function — lists Cloud Flows for a Power Platform environment via the SDK."""

from __future__ import annotations

from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient


class GetFlowsFunction:
    """Handles the powerplatform:index:getFlows invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List Cloud Flows for a given environment."""
        args = request.args

        env_id_pv = args.get("environmentId")
        if env_id_pv is None or env_id_pv.value is None:
            raise ValueError("environmentId is required.")
        env_id = str(env_id_pv.value)

        result = await self._client.sdk.powerautomate.environments.by_environment_id(env_id).cloud_flows.get()

        flow_list: list[PropertyValue] = []
        if result and result.value:
            for flow in result.value:
                flow_map: dict[str, PropertyValue] = {}
                flow_id = getattr(flow, "id", None)
                if flow_id is not None:
                    flow_map["id"] = PropertyValue(flow_id)
                flow_name = getattr(flow, "name", None)
                if flow_name is not None:
                    flow_map["name"] = PropertyValue(flow_name)
                flow_display_name = getattr(flow, "display_name", None)
                if flow_display_name is not None:
                    flow_map["displayName"] = PropertyValue(flow_display_name)
                flow_list.append(PropertyValue(flow_map))

        return InvokeResponse(
            return_value={"flows": PropertyValue(flow_list)},
        )
