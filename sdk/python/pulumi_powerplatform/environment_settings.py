"""Power Platform Environment Settings resource."""

import pulumi
from typing import Optional


class EnvironmentSettings(pulumi.CustomResource):
    """Manages settings on a Power Platform environment."""

    environment_id: pulumi.Output[str]
    max_upload_file_size: pulumi.Output[str]
    plugin_trace_log_setting: pulumi.Output[str]
    is_audit_enabled: pulumi.Output[str]
    is_user_access_audit_enabled: pulumi.Output[str]
    is_activity_logging_enabled: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        max_upload_file_size: Optional[str] = None,
        plugin_trace_log_setting: Optional[str] = None,
        is_audit_enabled: Optional[str] = None,
        is_user_access_audit_enabled: Optional[str] = None,
        is_activity_logging_enabled: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environmentId": environment_id,
            "maxUploadFileSize": max_upload_file_size,
            "pluginTraceLogSetting": plugin_trace_log_setting,
            "isAuditEnabled": is_audit_enabled,
            "isUserAccessAuditEnabled": is_user_access_audit_enabled,
            "isActivityLoggingEnabled": is_activity_logging_enabled,
        }
        super().__init__("powerplatform:index:EnvironmentSettings", resource_name, props, opts)
