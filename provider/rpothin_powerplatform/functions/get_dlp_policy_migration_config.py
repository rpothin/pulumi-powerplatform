"""getDlpPolicyMigrationConfig function — reads a DLP policy and returns its config for ResDlpPolicy / DlpPolicy."""

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


class GetDlpPolicyMigrationConfigFunction:
    """Handles the powerplatform:index:getDlpPolicyMigrationConfig invoke.

    Reads an existing DLP policy by ID and returns its display name and rule sets
    in the format expected by :class:`~rpothin_powerplatform.components.ResDlpPolicy`
    (``displayName`` + ``ruleSets``) and by ``powerplatform:index:DlpPolicy``
    (``name`` + ``ruleSets``), making it straightforward to replicate or migrate
    an existing tenant-level DLP policy.

    This function is the Pulumi equivalent of the ``rpothin/terraform-powerplatform-utl-dlppolicy-replicator``
    module.  It is read-only — no enforcement or reclassification is applied.
    Callers should review ``ruleSets`` before applying them to a new policy.
    """

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        """Read a DLP policy and return its configuration for migration.

        **Required input:**
        - ``sourcePolicyId`` (string): ID of the existing DLP policy to read.

        **Outputs:**
        - ``displayName`` (string): use as ``displayName`` for ``ResDlpPolicy``.
        - ``name`` (string): use as ``name`` for ``powerplatform:index:DlpPolicy``.
        - ``ruleSets`` (array): rule sets from the source policy, in the wire
          format accepted by both ``ResDlpPolicy`` and ``DlpPolicy``.
        """
        args = request.args

        source_id_pv = args.get("sourcePolicyId")
        if source_id_pv is None or source_id_pv.value is None:
            raise ValueError("sourcePolicyId is required.")
        source_policy_id = str(source_id_pv.value)

        try:
            policy = await retry_with_backoff(
                lambda: self._client.sdk.governance.rule_based_policies.by_policy_id(source_policy_id).get()
            )
        except APIError as e:
            raise RuntimeError(
                f"getDlpPolicyMigrationConfig failed with status {e.response_status_code}: {e.message}. "
                f"Response body: {getattr(e, 'response_body', 'unavailable')}"
            ) from e

        if policy is None:
            raise RuntimeError(
                f"DLP policy '{source_policy_id}' not found or returned no data."
            )

        rule_set_pvs: list[PropertyValue] = []
        for rs in getattr(policy, "rule_sets", None) or []:
            rule_set_pvs.append(rule_set_to_pv(rs))

        display_name = getattr(policy, "name", None) or ""

        return InvokeResponse(
            return_value={
                "displayName": PropertyValue(display_name),
                "name": PropertyValue(display_name),
                "ruleSets": PropertyValue(rule_set_pvs),
            }
        )
