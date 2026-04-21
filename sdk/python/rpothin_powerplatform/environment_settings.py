"""Power Platform Environment Settings resource."""

import re
from typing import Optional

import pulumi


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
            "environment_id": environment_id,
            "max_upload_file_size": max_upload_file_size,
            "plugin_trace_log_setting": plugin_trace_log_setting,
            "is_audit_enabled": is_audit_enabled,
            "is_user_access_audit_enabled": is_user_access_audit_enabled,
            "is_activity_logging_enabled": is_activity_logging_enabled,
        }
        super().__init__("powerplatform:index:EnvironmentSettings", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
