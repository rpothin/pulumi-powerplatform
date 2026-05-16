"""Power Platform Tenant Settings resource."""

import re
from typing import Any, Optional

import pulumi


class TenantSettings(pulumi.CustomResource):
    """Manages tenant-level Power Platform settings."""

    tenant_id: pulumi.Output[str]
    walk_me_opt_out: pulumi.Output[bool]
    disable_environment_creation_by_non_admin_users: pulumi.Output[bool]
    disable_trial_environment_creation_by_non_admin_users: pulumi.Output[bool]
    disable_portals_creation_by_non_admin_users: pulumi.Output[bool]
    disable_newsletter_sendout: pulumi.Output[bool]
    disable_nps_comments_reachout: pulumi.Output[bool]
    disable_survey_feedback: pulumi.Output[bool]
    disable_capacity_allocation_by_environment_admins: pulumi.Output[bool]
    disable_support_tickets_visible_by_all_users: pulumi.Output[bool]
    power_platform: pulumi.Output[Any]

    def __init__(
        self,
        resource_name: str,
        walk_me_opt_out: Optional[bool] = None,
        disable_environment_creation_by_non_admin_users: Optional[bool] = None,
        disable_trial_environment_creation_by_non_admin_users: Optional[bool] = None,
        disable_portals_creation_by_non_admin_users: Optional[bool] = None,
        disable_newsletter_sendout: Optional[bool] = None,
        disable_nps_comments_reachout: Optional[bool] = None,
        disable_survey_feedback: Optional[bool] = None,
        disable_capacity_allocation_by_environment_admins: Optional[bool] = None,
        disable_support_tickets_visible_by_all_users: Optional[bool] = None,
        power_platform: Optional[Any] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "walk_me_opt_out": walk_me_opt_out,
            "disable_environment_creation_by_non_admin_users": disable_environment_creation_by_non_admin_users,
            "disable_trial_environment_creation_by_non_admin_users": disable_trial_environment_creation_by_non_admin_users,
            "disable_portals_creation_by_non_admin_users": disable_portals_creation_by_non_admin_users,
            "disable_newsletter_sendout": disable_newsletter_sendout,
            "disable_nps_comments_reachout": disable_nps_comments_reachout,
            "disable_survey_feedback": disable_survey_feedback,
            "disable_capacity_allocation_by_environment_admins": disable_capacity_allocation_by_environment_admins,
            "disable_support_tickets_visible_by_all_users": disable_support_tickets_visible_by_all_users,
            "power_platform": power_platform,
        }
        super().__init__("powerplatform:index:TenantSettings", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        if prop == "disable_nps_comments_reachout":
            return "disableNPSCommentsReachout"
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        if prop == "disableNPSCommentsReachout":
            return "disable_nps_comments_reachout"
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
