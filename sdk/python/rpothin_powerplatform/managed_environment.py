"""Power Platform Managed Environment resource."""

import re
from typing import Optional

import pulumi


class ManagedEnvironment(pulumi.CustomResource):
    """Enables managed environment governance on a Power Platform environment."""

    environment_id: pulumi.Output[str]
    enabled: pulumi.Output[bool]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environmentId": environment_id,
            "enabled": None,
        }
        super().__init__("powerplatform:index:ManagedEnvironment", resource_name, props, opts)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
