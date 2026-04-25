`DlpPolicy` manages a Power Platform Data Loss Prevention (DLP) policy and its rule sets.

**Deletion behavior:** The Power Platform SDK does not expose a direct policy delete endpoint. When Pulumi destroys a `DlpPolicy` resource, it removes all rule sets from the policy rather than deleting the policy object itself. The empty policy remains in Power Platform after `pulumi destroy`.

If you need to fully remove the policy, delete it manually in the Power Platform admin center after running `pulumi destroy`.

**Rule set updates:** Rule sets are replaced in their entirety on every update — partial updates are not supported by the API. Pulumi sends the full desired rule set list on each apply.
