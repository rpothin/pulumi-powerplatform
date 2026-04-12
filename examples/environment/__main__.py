"""Example: Create a Power Platform environment."""

import pulumi
import pulumi_powerplatform as pp

# Create a new Sandbox environment in the United States region.
environment = pp.Environment(
    "my-dev-environment",
    display_name="Development Environment",
    description="Development sandbox for app building",
    location="unitedstates",
    environment_type="Sandbox",
    domain_name="mydevenv",
    currency_code="USD",
    language_code="1033",
)

pulumi.export("environmentId", environment.id)
pulumi.export("displayName", environment.display_name)
pulumi.export("state", environment.state)
pulumi.export("url", environment.url)
