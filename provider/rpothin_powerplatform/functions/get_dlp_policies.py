"""getDlpPolicies function — lists all DLP policies in the tenant via the SDK."""

from __future__ import annotations

from kiota_abstractions.api_error import APIError
from kiota_abstractions.base_request_configuration import RequestConfiguration
from mspp_management.governance.rule_based_policies.rule_based_policies_request_builder import (
    RuleBasedPoliciesRequestBuilder,
)
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    InvokeRequest,
    InvokeResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions._dlp_helpers import rule_set_to_pv
from rpothin_powerplatform.utils import retry_with_backoff

# The Power Platform governance/ruleBasedPolicies API requires an explicit
# ``api-version`` query parameter on every call (it is not defaulted anywhere in
# the SDK or this client) — omitting it returns HTTP 400 "The query parameters
# are invalid". See:
# https://learn.microsoft.com/en-us/rest/api/power-platform/governance/rule-based-policies/list-rule-based-policies
_API_VERSION = "2024-10-01"


class GetDlpPoliciesFunction:
    """Handles the powerplatform:index:getDlpPolicies invoke."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """List all DLP policies in the tenant.

        No inputs are required.  Returns all rule-based DLP policies visible to
        the configured service principal.
        """
        query_params = RuleBasedPoliciesRequestBuilder.RuleBasedPoliciesRequestBuilderGetQueryParameters(
            api_version=_API_VERSION,
        )
        config = RequestConfiguration(query_parameters=query_params)

        try:
            result = await retry_with_backoff(
                lambda: self._client.sdk.governance.rule_based_policies.get(
                    request_configuration=config
                )
            )
        except APIError as e:
            # NOTE: kiota_abstractions.APIError has no ``response_body`` attribute
            # (only message/response_status_code/response_headers). For status
            # codes with no registered error class — like this endpoint's 400 —
            # kiota's HttpxRequestAdapter.throw_failed_responses() never reads the
            # raw response body at all, so it truly is unavailable here. Surface
            # the response headers instead (e.g. a correlation/request ID) since
            # they *are* captured and are useful for a support case.
            raise RuntimeError(
                f"getDlpPolicies failed with status {e.response_status_code}: {e.message}. "
                f"Response headers: {dict(e.response_headers) if e.response_headers else 'unavailable'}"
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
