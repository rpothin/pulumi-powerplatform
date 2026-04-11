"""Example: Create a Power Platform Billing Policy."""

import pulumi

# Create a billing policy for pay-as-you-go billing.
billing_policy = pulumi.CustomResource(
    "my-billing-policy",
    "powerplatform:index:BillingPolicy",
    {
        "name": "Production Billing",
        "location": "unitedstates",
        "status": "Enabled",
        "billingInstrument": {
            "id": "/subscriptions/00000000-0000-0000-0000-000000000000",
            "resourceGroup": "rg-powerplatform",
            "subscriptionId": "00000000-0000-0000-0000-000000000000",
        },
    },
)

# Export the billing policy ID
pulumi.export("billingPolicyId", billing_policy.id)
pulumi.export("billingPolicyName", billing_policy["name"])
