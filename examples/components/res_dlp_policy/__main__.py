"""Example: manage a DLP policy using ResDlpPolicy component."""

import pulumi
import rpothin_powerplatform as pp

dlp_policy = pp.components.ResDlpPolicy(
    "demo-dlp-policy",
    args=pp.components.ResDlpPolicyArgs(
        display_name="Demo DLP Policy",
        rule_sets=[
            {
                "classification": "Business",
                "connectors": [
                    {"id": "/providers/Microsoft.PowerApps/apis/shared_office365"},
                ],
            },
            {
                "classification": "Blocked",
                "connectors": [
                    {"id": "/providers/Microsoft.PowerApps/apis/shared_twitter"},
                ],
            },
        ],
    ),
)

pulumi.export("dlp_policy_id", dlp_policy.resource_id)
