"""Example: Create a Power Platform Role Assignment."""

import pulumi

# Assign a role to a user at the tenant scope.
role_assignment = pulumi.CustomResource(
    "my-role-assignment",
    "powerplatform:index:RoleAssignment",
    {
        "principalObjectId": "00000000-0000-0000-0000-000000000000",
        "principalType": "User",
        "roleDefinitionId": "00000000-0000-0000-0000-000000000001",
        "scope": "/providers/Microsoft.PowerPlatform",
    },
)

# Export the role assignment details
pulumi.export("roleAssignmentId", role_assignment.id)
pulumi.export("principalType", role_assignment["principalType"])
