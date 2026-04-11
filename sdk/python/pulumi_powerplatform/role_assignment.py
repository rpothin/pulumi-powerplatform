"""Power Platform Role Assignment resource."""

import pulumi
from typing import Optional


class RoleAssignment(pulumi.CustomResource):
    """Assigns a role to a principal at a specified scope."""

    principal_object_id: pulumi.Output[str]
    principal_type: pulumi.Output[str]
    role_definition_id: pulumi.Output[str]
    scope: pulumi.Output[Optional[str]]
    created_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        principal_object_id: str = None,
        principal_type: str = None,
        role_definition_id: str = None,
        scope: str = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "principalObjectId": principal_object_id,
            "principalType": principal_type,
            "roleDefinitionId": role_definition_id,
            "scope": scope,
            "createdOn": None,
        }
        super().__init__("powerplatform:index:RoleAssignment", resource_name, props, opts)
