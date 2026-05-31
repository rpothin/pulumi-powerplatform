"""AVM-aligned ``ResDlpPolicy`` component resource.

Mirrors the ``rpothin/terraform-powerplatform-res-dlppolicy`` AVM module:
composes a single ``DlpPolicy`` resource with an AVM-compatible interface
(``enable_telemetry``, ``resource_id``/``resource`` outputs).

The AVM module auto-classifies connectors via a Terraform data source that is
not replicable inside a Pulumi ``construct`` call (no side-effecting API calls
during preview).  This component therefore accepts ``rule_sets`` directly.
The companion ``getDlpPolicyMigrationConfig`` invoke function (Phase 5) will
help build rule-set configurations from existing DLP policies.

No ``from __future__ import annotations`` — the Pulumi Analyzer needs runtime
type objects, not lazy string annotations.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

import pulumi

from ._base import COMPONENT_TOKEN_PREFIX, ComponentArgs, register_component, register_construct

#: Pulumi type token for this component.
COMPONENT_TYPE = f"{COMPONENT_TOKEN_PREFIX}ResDlpPolicy"


# ---------------------------------------------------------------------------
# Args dataclass
# ---------------------------------------------------------------------------


@dataclass(kw_only=True)
class ResDlpPolicyArgs(ComponentArgs):
    """Input arguments for :class:`ResDlpPolicy`.

    Mirrors ``var`` inputs from the ``rpothin/terraform-powerplatform-res-dlppolicy``
    AVM module.
    """

    display_name: str = field(default="")
    """Display name for the DLP policy.  Required."""

    rule_sets: Optional[list[Any]] = None
    """DLP rule-set definitions.

    Each element is a rule-set dict with ``classification`` (``"Business"``,
    ``"NonBusiness"``, or ``"Blocked"``) and ``connectors`` list.  When
    ``None``, the provider applies its own defaults.
    """


# ---------------------------------------------------------------------------
# Component resource
# ---------------------------------------------------------------------------


@register_component
class ResDlpPolicy(pulumi.ComponentResource):
    """AVM-aligned Pulumi component for a Power Platform DLP Policy.

    Composes a single ``powerplatform:index:DlpPolicy`` child resource with
    an opinionated, AVM-compatible interface.

    .. important::
        DLP policies apply tenant-wide.  Ensure only one stack manages a
        given policy to prevent conflicts between stacks.

    Example (Python)::

        import rpothin_powerplatform as pp

        policy = pp.components.ResDlpPolicy(
            "my-policy",
            pp.components.ResDlpPolicyArgs(
                display_name="My DLP Policy",
                rule_sets=[
                    {
                        "classification": "Business",
                        "connectors": [
                            {"id": "/providers/Microsoft.PowerApps/apis/shared_office365"},
                        ],
                    }
                ],
            ),
        )
    """

    resource_id: pulumi.Output[str]
    """ARM resource ID of the underlying ``DlpPolicy`` resource."""

    policy_name: pulumi.Output[str]
    """Display name of the created DLP policy."""

    rule_set_count: pulumi.Output[int]
    """Number of rule sets on the policy (as returned by the provider)."""

    last_modified: pulumi.Output[str]
    """ISO-8601 timestamp of the last modification to the policy."""

    tenant_id: pulumi.Output[str]
    """AAD tenant GUID that owns the policy."""

    def __init__(
        self,
        name: str,
        args: ResDlpPolicyArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(COMPONENT_TYPE, name, {}, opts)

        # Child resources inherit this component as their parent and share
        # provider configuration from the caller.
        child_opts = pulumi.ResourceOptions(
            parent=self,
            providers=opts.providers if opts else None,
            provider=opts.provider if opts else None,
        )

        from ._resource_wrappers import _DlpPolicyWrap  # local import avoids circular refs

        policy = _DlpPolicyWrap(
            f"{name}-policy",
            display_name=args.display_name,
            rule_sets=args.rule_sets,
            opts=child_opts,
        )

        self.resource_id = policy.id
        self.policy_name = policy.policy_name
        self.rule_set_count = policy.rule_set_count
        self.last_modified = policy.last_modified
        self.tenant_id = policy.tenant_id

        self.register_outputs(
            {
                "resourceId": self.resource_id,
                "policyName": self.policy_name,
                "ruleSetCount": self.rule_set_count,
                "lastModified": self.last_modified,
                "tenantId": self.tenant_id,
            }
        )


# ---------------------------------------------------------------------------
# Construct factory
# ---------------------------------------------------------------------------


@register_construct(COMPONENT_TYPE)
def _construct_res_dlp_policy(
    name: str,
    inputs: dict[str, Any],
    opts: Optional[pulumi.ResourceOptions],
) -> ResDlpPolicy:
    """Bridge factory: called by the Pulumi engine during ``construct``."""

    def _pv(key: str) -> Any:
        """Extract a value from the PropertyValue inputs dict by camelCase key."""
        v = inputs.get(key)
        if v is None:
            return None
        # PropertyValue wraps the real value; expose it to the SDK layer.
        if hasattr(v, "value"):
            return v.value
        return v

    args = ResDlpPolicyArgs(
        display_name=_pv("displayName") or "",
        rule_sets=_pv("ruleSets"),
        enable_telemetry=_pv("enableTelemetry"),
    )
    return ResDlpPolicy(name, args, opts)
