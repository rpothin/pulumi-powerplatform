"""Example: Create a Power Platform DLP Policy."""

import pulumi

# Create a DLP policy with a simple rule set.
dlp_policy = pulumi.CustomResource(
    "my-dlp-policy",
    "powerplatform:index:DlpPolicy",
    {
        "name": "Restrict Business Data Group",
        "ruleSets": [
            {
                "id": "default-rule-set",
                "version": "1.0",
                "inputs": {
                    "businessDataGroup": ["shared_office365"],
                    "nonBusinessDataGroup": ["shared_twitter"],
                },
            }
        ],
    },
)

# Export the policy ID
pulumi.export("policyId", dlp_policy.id)
pulumi.export("policyName", dlp_policy["name"])
