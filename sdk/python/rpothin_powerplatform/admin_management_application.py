"""Power Platform AdminManagementApplication resource."""

import re
from typing import Optional

import pulumi


class AdminManagementApplication(pulumi.CustomResource):
    """Registers a service principal as a Power Platform admin management application.

    This is a prerequisite for managing environment application administrators
    (``EnvironmentApplicationAdmin``). The resource is fully immutable — any
    change to ``application_id`` triggers a replacement.
    """

    application_id: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        application_id: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "application_id": application_id,
        }
        super().__init__("powerplatform:index:AdminManagementApplication", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
