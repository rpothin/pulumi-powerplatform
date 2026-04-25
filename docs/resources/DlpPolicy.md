`DlpPolicy` manages a Power Platform Data Loss Prevention (DLP) policy and its rule sets.

**Deletion behavior:** The Power Platform SDK does not expose a direct policy delete endpoint. When Pulumi destroys a `DlpPolicy` resource, it deletes each rule set currently attached to the policy individually via the rule-set API. The policy object itself is not deleted and may remain in Power Platform without any rule sets after `pulumi destroy`.

If you need to fully remove the policy object, delete it manually in the Power Platform admin center after running `pulumi destroy`.

**Rule set updates:** Rule sets are replaced in their entirety on every update — partial updates are not supported by the API. Pulumi sends the full desired rule set list on each apply.
