"""getSecurityRoles function — queries Dataverse security roles."""

from __future__ import annotations

from urllib.parse import urlparse

from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest, InvokeResponse

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import pv_str as _pv_str
from rpothin_powerplatform.utils import resolve_dataverse_url


class GetSecurityRolesFunction:
    """Handles the ``powerplatform:index:getSecurityRoles`` invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """Fetch Dataverse security roles for an environment."""
        env_id = _pv_str(request.args.get("environmentId"))
        business_unit_id = _pv_str(request.args.get("businessUnitId"))

        if not env_id:
            raise ValueError("environmentId is required.")

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(f"Environment {env_id!r} has no Dataverse instance.")

        dv_client = self._make_dataverse_client(instance_url)

        path = "/api/data/v9.2/roles?$select=roleid,name,_businessunitid_value"
        if business_unit_id:
            path = f"{path}&$filter=_businessunitid_value eq '{business_unit_id}'"

        result = await dv_client.request("GET", path, api_version=None) or {}
        security_roles = result.get("value", [])

        return InvokeResponse(
            return_value={
                "securityRoles": PropertyValue([
                    PropertyValue({
                        "roleId": PropertyValue(str(role.get("roleid", ""))),
                        "name": PropertyValue(str(role.get("name", ""))),
                        "businessUnitId": PropertyValue(str(role.get("_businessunitid_value", ""))),
                    })
                    for role in security_roles
                ])
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
