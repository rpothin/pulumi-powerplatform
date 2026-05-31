"""AVM-aligned ``ResTenantSettings`` component resource.

Mirrors the ``rpothin/terraform-powerplatform-res-tenantsettings`` AVM module:
composes a single ``TenantSettings`` resource with an AVM-compatible interface
(``enable_telemetry``, ``resource_id``/``resource`` outputs).

.. important::
    ``TenantSettings`` is a singleton — only one tenant-settings record exists
    per AAD tenant.  Only one stack should own this component.  Multiple stacks
    managing the same tenant's settings will conflict.

No ``from __future__ import annotations`` — the Pulumi Analyzer needs runtime
type objects, not lazy string annotations.
"""

from dataclasses import dataclass
from typing import Any, Optional

import pulumi

from ._base import COMPONENT_TOKEN_PREFIX, ComponentArgs, register_component, register_construct

#: Pulumi type token for this component.
COMPONENT_TYPE = f"{COMPONENT_TOKEN_PREFIX}ResTenantSettings"


# ---------------------------------------------------------------------------
# Args dataclass
# ---------------------------------------------------------------------------


@dataclass(kw_only=True)
class ResTenantSettingsArgs(ComponentArgs):
    """Input arguments for :class:`ResTenantSettings`.

    Mirrors ``var`` inputs from the ``rpothin/terraform-powerplatform-res-tenantsettings``
    AVM module.  All fields are optional because a tenant may choose to manage only
    a subset of settings while leaving others at their platform defaults.

    .. note::
        ``disable_nps_comments_reachout`` maps to ``disableNPSCommentsReachout``
        in the underlying ``TenantSettings`` resource.  The Pulumi Analyzer
        converts the Python field name to standard camelCase
        (``disableNpsCommentsReachout``); the component wrapper translates this
        to the provider's all-caps ``disableNPSCommentsReachout`` wire key.
    """

    disable_capacity_allocation_by_environment_admins: Optional[bool] = None
    """Prevent environment admins from allocating add-on and trial capacity."""

    disable_environment_creation_by_non_admin_users: Optional[bool] = None
    """Restrict environment creation to admin users only."""

    disable_nps_comments_reachout: Optional[bool] = None
    """Disable NPS (Net Promoter Score) comments reachout to end-users."""

    disable_newsletter_sendout: Optional[bool] = None
    """Disable the Power Platform newsletter email campaigns."""

    disable_portals_creation_by_non_admin_users: Optional[bool] = None
    """Restrict Power Pages / portals creation to admin users only."""

    disable_support_tickets_visible_by_all_users: Optional[bool] = None
    """Hide support tickets from non-admin users."""

    disable_survey_feedback: Optional[bool] = None
    """Disable in-product survey feedback prompts."""

    disable_trial_environment_creation_by_non_admin_users: Optional[bool] = None
    """Restrict trial environment creation to admin users only."""

    power_platform: Optional[dict[str, Any]] = None
    """Opaque nested Power Platform settings dict.

    Passed through directly to the ``powerPlatform`` property of the
    underlying ``TenantSettings`` resource.  Accepts any key/value pairs
    recognised by the provider.
    """

    walk_me_opt_out: Optional[bool] = None
    """Opt the tenant out of WalkMe in-app guidance."""


# ---------------------------------------------------------------------------
# Component resource
# ---------------------------------------------------------------------------


@register_component
class ResTenantSettings(pulumi.ComponentResource):
    """AVM-aligned Pulumi component for Power Platform Tenant Settings.

    Composes a single ``powerplatform:index:TenantSettings`` child resource
    with an opinionated, AVM-compatible interface.

    .. important::
        ``TenantSettings`` is a singleton resource — only one exists per AAD
        tenant.  Assign ownership of this component to a single, dedicated
        infrastructure stack to avoid conflicts.

    Example (Python)::

        import rpothin_powerplatform as pp

        tenant_cfg = pp.components.ResTenantSettings(
            "tenant-settings",
            pp.components.ResTenantSettingsArgs(
                disable_environment_creation_by_non_admin_users=True,
                disable_trial_environment_creation_by_non_admin_users=True,
            ),
        )
    """

    resource_id: pulumi.Output[str]
    """ARM resource ID of the underlying ``TenantSettings`` resource."""

    tenant_id: pulumi.Output[str]
    """AAD tenant GUID of the managed tenant."""

    def __init__(
        self,
        name: str,
        args: ResTenantSettingsArgs,
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

        from ._resource_wrappers import _TenantSettingsWrap  # local import avoids circular refs

        settings = _TenantSettingsWrap(
            f"{name}-settings",
            disable_capacity_allocation_by_environment_admins=args.disable_capacity_allocation_by_environment_admins,
            disable_environment_creation_by_non_admin_users=args.disable_environment_creation_by_non_admin_users,
            disable_nps_comments_reachout=args.disable_nps_comments_reachout,
            disable_newsletter_sendout=args.disable_newsletter_sendout,
            disable_portals_creation_by_non_admin_users=args.disable_portals_creation_by_non_admin_users,
            disable_support_tickets_visible_by_all_users=args.disable_support_tickets_visible_by_all_users,
            disable_survey_feedback=args.disable_survey_feedback,
            disable_trial_environment_creation_by_non_admin_users=args.disable_trial_environment_creation_by_non_admin_users,
            power_platform=args.power_platform,
            walk_me_opt_out=args.walk_me_opt_out,
            opts=child_opts,
        )

        self.resource_id = settings.id
        self.tenant_id = settings.tenant_id

        self.register_outputs(
            {
                "resourceId": self.resource_id,
                "tenantId": self.tenant_id,
            }
        )


# ---------------------------------------------------------------------------
# Construct factory
# ---------------------------------------------------------------------------


@register_construct(COMPONENT_TYPE)
async def _construct_res_tenant_settings(
    name: str,
    inputs: dict[str, Any],
    opts: Optional[pulumi.ResourceOptions],
) -> object:
    """Async bridge factory: called by the Pulumi engine during ``construct``.

    All inputs are converted via :func:`~construct_bridge.pv_to_input` so that
    secret, unknown, and dependency metadata is preserved for the Pulumi engine.
    """
    from pulumi.provider.experimental.property_value import PropertyValue  # noqa: PLC0415
    from pulumi.provider.experimental.provider import ConstructResponse  # noqa: PLC0415

    from ..construct_bridge import pv_to_input, resolve_outputs  # noqa: PLC0415

    def _pv(key: str, default: Any = None) -> Any:
        """Convert a named input to a Python value / Output, preserving metadata."""
        return pv_to_input(inputs.get(key, PropertyValue(default)))

    # All boolean fields use _pv (not _pv_bool) — no conditional child resources.
    # Booleans drive property values only, not control flow, so we preserve
    # Output/secret/unknown metadata rather than extracting raw Python bools.
    args = ResTenantSettingsArgs(
        disable_capacity_allocation_by_environment_admins=_pv(
            "disableCapacityAllocationByEnvironmentAdmins"
        ),
        disable_environment_creation_by_non_admin_users=_pv(
            "disableEnvironmentCreationByNonAdminUsers"
        ),
        # Analyzer generates disableNpsCommentsReachout (standard camelCase);
        # the wrapper maps this to the provider's disableNPSCommentsReachout.
        disable_nps_comments_reachout=_pv("disableNpsCommentsReachout"),
        disable_newsletter_sendout=_pv("disableNewsletterSendout"),
        disable_portals_creation_by_non_admin_users=_pv(
            "disablePortalsCreationByNonAdminUsers"
        ),
        disable_support_tickets_visible_by_all_users=_pv(
            "disableSupportTicketsVisibleByAllUsers"
        ),
        disable_survey_feedback=_pv("disableSurveyFeedback"),
        disable_trial_environment_creation_by_non_admin_users=_pv(
            "disableTrialEnvironmentCreationByNonAdminUsers"
        ),
        power_platform=_pv("powerPlatform"),
        walk_me_opt_out=_pv("walkMeOptOut"),
        enable_telemetry=_pv("enableTelemetry"),
    )
    comp = ResTenantSettings(name, args, opts)
    urn = await comp.urn.future()
    state = await resolve_outputs(
        {
            "resourceId": comp.resource_id,
            "tenantId": comp.tenant_id,
        }
    )
    return ConstructResponse(urn=urn, state=state, state_dependencies={})
