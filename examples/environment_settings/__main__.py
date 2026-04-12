"""Example: Configure settings on a Power Platform environment."""

import pulumi
import pulumi_powerplatform as pp

# Reference an existing environment (e.g., created by the Environment resource).
environment_id = "00000000-0000-0000-0000-000000000001"

# Apply settings to the environment.
settings = pp.EnvironmentSettings(
    "my-env-settings",
    environment_id=environment_id,
    max_upload_file_size="52428800",  # 50 MB
    plugin_trace_log_setting="Exception",
    is_audit_enabled="true",
    is_user_access_audit_enabled="true",
    is_activity_logging_enabled="false",
)

pulumi.export("environmentId", settings.environment_id)
pulumi.export("maxUploadFileSize", settings.max_upload_file_size)
