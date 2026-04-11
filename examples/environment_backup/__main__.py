"""Example: Create a Power Platform Environment Backup."""

import pulumi

# Create a manual backup of a Power Platform environment.
backup = pulumi.CustomResource(
    "my-env-backup",
    "powerplatform:index:EnvironmentBackup",
    {
        "environmentId": "00000000-0000-0000-0000-000000000000",
        "label": "pre-release-backup",
    },
)

# Export the backup details
pulumi.export("backupId", backup.id)
pulumi.export("backupLabel", backup["label"])
