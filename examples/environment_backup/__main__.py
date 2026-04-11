"""Example: Create a Power Platform Environment Backup."""

import pulumi
import pulumi_powerplatform as pp

backup = pp.EnvironmentBackup(
    "my-env-backup",
    environment_id="00000000-0000-0000-0000-000000000000",
    label="pre-release-backup",
)

pulumi.export("backupId", backup.id)
pulumi.export("backupLabel", backup.label)
