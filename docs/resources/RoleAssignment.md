Role assignments are **immutable** — the Power Platform API does not support updating an existing role assignment.

Any change to `RoleAssignment` inputs (role, principal, or scope) will trigger a **replacement**: Pulumi deletes the existing assignment and creates a new one. This is by design — role assignments in Power Platform are identified by the combination of principal and role, so a change to either property is semantically a new assignment.

If you need to change the role for a principal, Pulumi will perform a replacement automatically. The Pulumi engine controls replacement ordering; there may be a brief window during which the principal holds neither the old nor the new role.

To make this explicit, you can use the [`replaceOnChanges`](https://www.pulumi.com/docs/concepts/options/replaceonchanges/) resource option.
