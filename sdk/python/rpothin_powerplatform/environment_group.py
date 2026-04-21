"""Power Platform Environment Group resource."""

import re
from typing import Optional

import pulumi


class EnvironmentGroup(pulumi.CustomResource):
    """Manages a Power Platform environment group."""

    display_name: pulumi.Output[str]
    description: pulumi.Output[str]
    parent_group_id: pulumi.Output[str]
    created_time: pulumi.Output[str]
    last_modified_time: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        parent_group_id: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "display_name": display_name,
            "description": description,
            "parent_group_id": parent_group_id,
            "created_time": None,
            "last_modified_time": None,
        }
        super().__init__("powerplatform:index:EnvironmentGroup", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
