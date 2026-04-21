"""Power Platform Role Assignment resource."""

import re
from typing import Optional

import pulumi


class RoleAssignment(pulumi.CustomResource):
    """Assigns a role to a principal at a specified scope."""

    principal_object_id: pulumi.Output[str]
    principal_type: pulumi.Output[str]
    role_definition_id: pulumi.Output[str]
    scope: pulumi.Output[str]
    created_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        principal_object_id: Optional[str] = None,
        principal_type: Optional[str] = None,
        role_definition_id: Optional[str] = None,
        scope: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "principalObjectId": principal_object_id,
            "principalType": principal_type,
            "roleDefinitionId": role_definition_id,
            "scope": scope,
            "createdOn": None,
        }
        super().__init__("powerplatform:index:RoleAssignment", resource_name, props, opts)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
