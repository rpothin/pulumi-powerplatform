"""Power Platform Managed Environment resource."""

import pulumi


class ManagedEnvironment(pulumi.CustomResource):
    """Enables managed environment governance on a Power Platform environment."""

    environment_id: pulumi.Output[str]
    enabled: pulumi.Output[bool]

    def __init__(
        self,
        resource_name: str,
        environment_id: str = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "environmentId": environment_id,
            "enabled": None,
        }
        super().__init__("powerplatform:index:ManagedEnvironment", resource_name, props, opts)
