"""Example: Create a Power Platform DLP Policy."""

import pulumi
import pulumi_powerplatform as pp

dlp_policy = pp.DlpPolicy(
    "my-dlp-policy",
    name="Restrict Business Data Group",
    rule_sets=[
        {
            "id": "default-rule-set",
            "version": "1.0",
            "inputs": {
                "businessDataGroup": ["shared_office365"],
                "nonBusinessDataGroup": ["shared_twitter"],
            },
        }
    ],
)

pulumi.export("policyId", dlp_policy.id)
pulumi.export("policyName", dlp_policy.name)
