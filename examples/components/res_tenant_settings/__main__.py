"""Example: manage tenant-wide settings using ResTenantSettings component."""

import pulumi
import rpothin_powerplatform as pp

tenant_settings = pp.components.ResTenantSettings(
    "demo-tenant-settings",
    args=pp.components.ResTenantSettingsArgs(
        walk_me_opt_out=True,
        disable_support_tickets_visible_by_all_users=False,
    ),
)

pulumi.export("tenant_settings_id", tenant_settings.resource_id)
