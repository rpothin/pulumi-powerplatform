"""Power Platform Environment Backup resource."""

import re
from typing import Optional

import pulumi


class EnvironmentBackup(pulumi.CustomResource):
    """Creates a manual backup of a Power Platform environment."""

    environment_id: pulumi.Output[str]
    label: pulumi.Output[str]
    backup_point_date_time: pulumi.Output[str]
    backup_expiry_date_time: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        label: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environment_id": environment_id,
            "label": label,
            "backup_point_date_time": None,
            "backup_expiry_date_time": None,
        }
        super().__init__("powerplatform:index:EnvironmentBackup", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
