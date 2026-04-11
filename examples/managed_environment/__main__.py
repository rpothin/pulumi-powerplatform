"""Example: Enable a Managed Environment in Power Platform."""

import pulumi
import pulumi_powerplatform as pp

managed_env = pp.ManagedEnvironment(
    "my-managed-env",
    environment_id="00000000-0000-0000-0000-000000000000",
)

pulumi.export("managedEnvId", managed_env.id)
pulumi.export("environmentId", managed_env.environment_id)
