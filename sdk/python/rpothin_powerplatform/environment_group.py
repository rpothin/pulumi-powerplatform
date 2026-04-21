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
            "displayName": display_name,
            "description": description,
            "parentGroupId": parent_group_id,
            "createdTime": None,
            "lastModifiedTime": None,
        }
        super().__init__("powerplatform:index:EnvironmentGroup", resource_name, props, opts)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
