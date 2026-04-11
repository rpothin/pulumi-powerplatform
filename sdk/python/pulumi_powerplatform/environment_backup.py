"""Power Platform Environment Backup resource."""

import pulumi
from typing import Optional


class EnvironmentBackup(pulumi.CustomResource):
    """Creates a manual backup of a Power Platform environment."""

    environment_id: pulumi.Output[str]
    label: pulumi.Output[str]
    backup_point_date_time: pulumi.Output[Optional[str]]
    backup_expiry_date_time: pulumi.Output[Optional[str]]

    def __init__(
        self,
        resource_name: str,
        environment_id: str = None,
        label: str = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "environmentId": environment_id,
            "label": label,
            "backupPointDateTime": None,
            "backupExpiryDateTime": None,
        }
        super().__init__("powerplatform:index:EnvironmentBackup", resource_name, props, opts)
