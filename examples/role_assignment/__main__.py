"""Example: Create a Power Platform Role Assignment."""

import pulumi
import pulumi_powerplatform as pp

role_assignment = pp.RoleAssignment(
    "my-role-assignment",
    principal_object_id="00000000-0000-0000-0000-000000000000",
    principal_type="User",
    role_definition_id="00000000-0000-0000-0000-000000000001",
    scope="/providers/Microsoft.PowerPlatform",
)

pulumi.export("roleAssignmentId", role_assignment.id)
pulumi.export("principalType", role_assignment.principal_type)
