"""Example: provision a Power Platform environment using ResEnvironment component."""

import pulumi
import rpothin_powerplatform as pp

env = pp.components.ResEnvironment(
    "demo-environment",
    args=pp.components.ResEnvironmentArgs(
        display_name="Demo Environment",
        location="unitedstates",
        environment_type="Sandbox",
    ),
)

pulumi.export("environment_id", env.resource_id)
pulumi.export("environment_url", env.environment_url)
