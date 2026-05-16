"""Power Platform EnvironmentApplicationAdmin resource."""

import re
from typing import Optional

import pulumi


class EnvironmentApplicationAdmin(pulumi.CustomResource):
    """Adds a service principal as System Administrator in a Dataverse-enabled
    Power Platform environment.

    Both ``environment_id`` and ``application_id`` are immutable — any change
    to either triggers resource replacement.

    This resource is typically used after registering the service principal as
    an admin management application (see ``AdminManagementApplication``).
    """

    environment_id: pulumi.Output[str]
    application_id: pulumi.Output[str]
    system_user_id: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        application_id: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environment_id": environment_id,
            "application_id": application_id,
            "system_user_id": None,
        }
        super().__init__(
            "powerplatform:index:EnvironmentApplicationAdmin", resource_name, props, opts
        )

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
