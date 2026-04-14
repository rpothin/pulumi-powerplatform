"""Example: Create a Power Platform Billing Policy."""

import pulumi
import rpothin_powerplatform as pp

billing_policy = pp.BillingPolicy(
    "my-billing-policy",
    name="Production Billing",
    location="unitedstates",
    status="Enabled",
    billing_instrument={
        "id": "/subscriptions/00000000-0000-0000-0000-000000000000",
        "resourceGroup": "rg-powerplatform",
        "subscriptionId": "00000000-0000-0000-0000-000000000000",
    },
)

pulumi.export("billingPolicyId", billing_policy.id)
pulumi.export("billingPolicyName", billing_policy.name)
