"""Thin ``pulumi.CustomResource`` wrappers for use inside component ``construct`` methods.

The provider and SDK share the Python package name ``rpothin_powerplatform``.
When the provider plugin runs, ``import rpothin_powerplatform`` resolves to the
*provider* package, not the generated SDK.  These wrappers register child
resources with the correct type tokens (``powerplatform:index:*``) without
importing the SDK, avoiding the namespace collision entirely.

These classes are **internal** and must only be used from component ``__init__``
methods.  They are not part of the public provider API.
"""

from __future__ import annotations

from typing import Any, Optional

import pulumi


class _EnvironmentWrap(pulumi.CustomResource):
    """Thin wrapper for ``powerplatform:index:Environment``."""

    def __init__(
        self,
        resource_name: str,
        *,
        display_name: Any,
        environment_type: Any,
        location: Any,
        allow_bing_search: Any = None,
        allow_moving_data_across_regions: Any = None,
        azure_region: Any = None,
        billing_policy_id: Any = None,
        cadence: Any = None,
        dataverse: Any = None,
        description: Any = None,
        environment_group_id: Any = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        props: dict[str, Any] = {
            "displayName": display_name,
            "environmentType": environment_type,
            "location": location,
            "allowBingSearch": allow_bing_search,
            "allowMovingDataAcrossRegions": allow_moving_data_across_regions,
            "azureRegion": azure_region,
            "billingPolicyId": billing_policy_id,
            "cadence": cadence,
            "dataverse": dataverse,
            "description": description,
            "environmentGroupId": environment_group_id,
            # computed output-only fields — must be declared so the resource
            # state shape matches what the provider returns on read
            "createdTime": None,
            "lastModifiedTime": None,
            "state": None,
        }
        super().__init__("powerplatform:index:Environment", resource_name, props, opts)

    @property
    def display_name(self) -> pulumi.Output[str]:
        return pulumi.get(self, "displayName")

    @property
    def environment_url(self) -> pulumi.Output[Optional[str]]:
        """URL of the Dataverse instance, if provisioned."""
        return pulumi.get(self, "dataverse").apply(
            lambda d: (d.get("url") if isinstance(d, dict) else None) or None
        )

    @property
    def dataverse_organization_id(self) -> pulumi.Output[Optional[str]]:
        """Dataverse organisation GUID, if provisioned."""
        return pulumi.get(self, "dataverse").apply(
            lambda d: (d.get("organizationId") if isinstance(d, dict) else None) or None
        )


class _DlpPolicyWrap(pulumi.CustomResource):
    """Thin wrapper for ``powerplatform:index:DlpPolicy``."""

    def __init__(
        self,
        resource_name: str,
        *,
        display_name: Any,
        rule_sets: Any = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "powerplatform:index:DlpPolicy",
            resource_name,
            {
                # DlpPolicy uses "name" as its display-name input property.
                "name": display_name,
                "ruleSets": rule_sets,
                # computed output-only fields
                "lastModified": None,
                "ruleSetCount": None,
                "tenantId": None,
            },
            opts,
        )

    @property
    def policy_name(self) -> pulumi.Output[str]:
        return pulumi.get(self, "name")

    @property
    def last_modified(self) -> pulumi.Output[str]:
        return pulumi.get(self, "lastModified")

    @property
    def rule_set_count(self) -> pulumi.Output[int]:
        return pulumi.get(self, "ruleSetCount")

    @property
    def tenant_id(self) -> pulumi.Output[str]:
        return pulumi.get(self, "tenantId")


class _TenantSettingsWrap(pulumi.CustomResource):
    """Thin wrapper for ``powerplatform:index:TenantSettings``."""

    def __init__(
        self,
        resource_name: str,
        *,
        disable_capacity_allocation_by_environment_admins: Any = None,
        disable_environment_creation_by_non_admin_users: Any = None,
        # NPS is all-caps in the provider; the wrapper translates the
        # standard-camelCase component key to the provider's wire key.
        disable_nps_comments_reachout: Any = None,
        disable_newsletter_sendout: Any = None,
        disable_portals_creation_by_non_admin_users: Any = None,
        disable_support_tickets_visible_by_all_users: Any = None,
        disable_survey_feedback: Any = None,
        disable_trial_environment_creation_by_non_admin_users: Any = None,
        power_platform: Any = None,
        walk_me_opt_out: Any = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "powerplatform:index:TenantSettings",
            resource_name,
            {
                "disableCapacityAllocationByEnvironmentAdmins": disable_capacity_allocation_by_environment_admins,
                "disableEnvironmentCreationByNonAdminUsers": disable_environment_creation_by_non_admin_users,
                # Provider uses all-caps NPS; component schema uses standard camelCase.
                "disableNPSCommentsReachout": disable_nps_comments_reachout,
                "disableNewsletterSendout": disable_newsletter_sendout,
                "disablePortalsCreationByNonAdminUsers": disable_portals_creation_by_non_admin_users,
                "disableSupportTicketsVisibleByAllUsers": disable_support_tickets_visible_by_all_users,
                "disableSurveyFeedback": disable_survey_feedback,
                "disableTrialEnvironmentCreationByNonAdminUsers": disable_trial_environment_creation_by_non_admin_users,
                "powerPlatform": power_platform,
                "walkMeOptOut": walk_me_opt_out,
                # computed output-only field
                "tenantId": None,
            },
            opts,
        )

    @property
    def tenant_id(self) -> pulumi.Output[str]:
        return pulumi.get(self, "tenantId")


class _ManagedEnvironmentWrap(pulumi.CustomResource):
    """Thin wrapper for ``powerplatform:index:ManagedEnvironment``."""

    def __init__(
        self,
        resource_name: str,
        *,
        environment_id: Any,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "powerplatform:index:ManagedEnvironment",
            resource_name,
            {"environmentId": environment_id, "enabled": None},
            opts,
        )


class _EnvironmentSettingsWrap(pulumi.CustomResource):
    """Thin wrapper for ``powerplatform:index:EnvironmentSettings``."""

    def __init__(
        self,
        resource_name: str,
        *,
        environment_id: Any,
        is_audit_enabled: Any = None,
        is_read_audit_enabled: Any = None,
        is_user_access_audit_enabled: Any = None,
        audit_retention_period_in_days: Any = None,
        plugin_trace_log_setting: Any = None,
        max_upload_file_size: Any = None,
        show_dashboard_cards_in_expanded_state: Any = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(
            "powerplatform:index:EnvironmentSettings",
            resource_name,
            {
                "environmentId": environment_id,
                "isAuditEnabled": is_audit_enabled,
                "isReadAuditEnabled": is_read_audit_enabled,
                "isUserAccessAuditEnabled": is_user_access_audit_enabled,
                "auditRetentionPeriodInDays": audit_retention_period_in_days,
                "pluginTraceLogSetting": plugin_trace_log_setting,
                "maxUploadFileSize": max_upload_file_size,
                "showDashboardCardsInExpandedState": show_dashboard_cards_in_expanded_state,
            },
            opts,
        )
