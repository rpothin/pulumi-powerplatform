"""getDlpPolicies function — lists all DLP policies in the tenant via the SDK."""

from __future__ import annotations

from kiota_abstractions.api_error import APIError
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions._dlp_helpers import rule_set_to_pv
from rpothin_powerplatform.utils import retry_with_backoff


class GetDlpPoliciesFunction:
    """Handles the powerplatform:index:getDlpPolicies invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List all DLP policies in the tenant.

        No inputs are required.  Returns all rule-based DLP policies visible to
        the configured service principal.
        """
        try:
            result = await retry_with_backoff(
                lambda: self._client.sdk.governance.rule_based_policies.get()
            )
        except APIError as e:
            raise RuntimeError(
                f"getDlpPolicies failed with status {e.response_status_code}: {e.message}. "
                f"Response body: {getattr(e, 'response_body', 'unavailable')}"
            ) from e

        policy_list: list[PropertyValue] = []
        if result is not None:
            for policy in result.value or []:
                p_map: dict[str, PropertyValue] = {}

                p_id = getattr(policy, "id", None)
                if p_id is not None:
                    p_map["id"] = PropertyValue(p_id)

                p_name = getattr(policy, "name", None)
                if p_name is not None:
                    p_map["name"] = PropertyValue(p_name)

                p_tenant = getattr(policy, "tenant_id", None)
                if p_tenant is not None:
                    p_map["tenantId"] = PropertyValue(p_tenant)

                p_modified = getattr(policy, "last_modified", None)
                if p_modified is not None:
                    p_map["lastModified"] = PropertyValue(p_modified.isoformat())

                p_count = getattr(policy, "rule_set_count", None)
                if p_count is not None:
                    p_map["ruleSetCount"] = PropertyValue(float(p_count))

                p_rule_sets = getattr(policy, "rule_sets", None)
                if p_rule_sets is not None:
                    p_map["ruleSets"] = PropertyValue([rule_set_to_pv(rs) for rs in p_rule_sets])

                policy_list.append(PropertyValue(p_map))

        return InvokeResponse(
            return_value={"policies": PropertyValue(policy_list)},
        )
