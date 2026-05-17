"""Power Platform Environment Settings resource."""

import re
from typing import Optional

import pulumi


class EnvironmentSettings(pulumi.CustomResource):
    """Manages settings on a Power Platform environment.

    Settings are applied across two API surfaces:
    - Tier 1 (PP API): maxUploadFileSize, pluginTraceLogSetting, isAuditEnabled,
      isUserAccessAuditEnabled, isActivityLoggingEnabled
    - Tier 2 (Dataverse): isReadAuditEnabled, auditRetentionPeriodInDays,
      allowApplicationUserAccess, allowMicrosoftTrustedServiceTags,
      reverseProxyIpAddresses, powerAppsComponentFrameworkForCanvasApps,
      showDashboardCardsInExpandedState
    """

    environment_id: pulumi.Output[str]
    # Tier-1 (Power Platform API) settings
    max_upload_file_size: pulumi.Output[str]
    plugin_trace_log_setting: pulumi.Output[str]
    is_audit_enabled: pulumi.Output[str]
    is_user_access_audit_enabled: pulumi.Output[str]
    is_activity_logging_enabled: pulumi.Output[str]
    # Tier-2 (Dataverse organizations table) settings
    is_read_audit_enabled: pulumi.Output[bool]
    audit_retention_period_in_days: pulumi.Output[int]
    allow_application_user_access: pulumi.Output[bool]
    allow_microsoft_trusted_service_tags: pulumi.Output[bool]
    reverse_proxy_ip_addresses: pulumi.Output[str]
    power_apps_component_framework_for_canvas_apps: pulumi.Output[bool]
    show_dashboard_cards_in_expanded_state: pulumi.Output[bool]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        # Tier-1 settings
        max_upload_file_size: Optional[str] = None,
        plugin_trace_log_setting: Optional[str] = None,
        is_audit_enabled: Optional[str] = None,
        is_user_access_audit_enabled: Optional[str] = None,
        is_activity_logging_enabled: Optional[str] = None,
        # Tier-2 (Dataverse) settings
        is_read_audit_enabled: Optional[bool] = None,
        audit_retention_period_in_days: Optional[int] = None,
        allow_application_user_access: Optional[bool] = None,
        allow_microsoft_trusted_service_tags: Optional[bool] = None,
        reverse_proxy_ip_addresses: Optional[str] = None,
        power_apps_component_framework_for_canvas_apps: Optional[bool] = None,
        show_dashboard_cards_in_expanded_state: Optional[bool] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environment_id": environment_id,
            "max_upload_file_size": max_upload_file_size,
            "plugin_trace_log_setting": plugin_trace_log_setting,
            "is_audit_enabled": is_audit_enabled,
            "is_user_access_audit_enabled": is_user_access_audit_enabled,
            "is_activity_logging_enabled": is_activity_logging_enabled,
            "is_read_audit_enabled": is_read_audit_enabled,
            "audit_retention_period_in_days": audit_retention_period_in_days,
            "allow_application_user_access": allow_application_user_access,
            "allow_microsoft_trusted_service_tags": allow_microsoft_trusted_service_tags,
            "reverse_proxy_ip_addresses": reverse_proxy_ip_addresses,
            "power_apps_component_framework_for_canvas_apps": power_apps_component_framework_for_canvas_apps,
            "show_dashboard_cards_in_expanded_state": show_dashboard_cards_in_expanded_state,
        }
        super().__init__("powerplatform:index:EnvironmentSettings", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
