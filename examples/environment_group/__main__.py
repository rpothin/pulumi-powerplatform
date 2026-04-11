"""Example: Create a Power Platform Environment Group."""

import pulumi

# This example uses the provider directly via Pulumi's custom resource mechanism.
# In a production setup, you would use a generated SDK (e.g., pulumi_powerplatform.EnvironmentGroup).

# Create an environment group
env_group = pulumi.CustomResource(
    "my-env-group",
    "powerplatform:index:EnvironmentGroup",
    {
        "displayName": "Development Environments",
        "description": "Group for all development Power Platform environments",
    },
)

# Export the group ID
pulumi.export("groupId", env_group.id)
pulumi.export("displayName", env_group["displayName"])
