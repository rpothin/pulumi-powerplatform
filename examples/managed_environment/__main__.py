"""Example: Enable a Managed Environment in Power Platform."""

import pulumi

# Enable managed environment governance on an existing environment.
managed_env = pulumi.CustomResource(
    "my-managed-env",
    "powerplatform:index:ManagedEnvironment",
    {
        "environmentId": "00000000-0000-0000-0000-000000000000",
    },
)

# Export the managed environment details
pulumi.export("managedEnvId", managed_env.id)
pulumi.export("environmentId", managed_env["environmentId"])
