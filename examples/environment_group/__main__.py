"""Example: Create a Power Platform Environment Group."""

import pulumi
import rpothin_powerplatform as pp

env_group = pp.EnvironmentGroup(
    "my-env-group",
    display_name="Development Environments",
    description="Group for all development Power Platform environments",
)

pulumi.export("groupId", env_group.id)
pulumi.export("displayName", env_group.display_name)
