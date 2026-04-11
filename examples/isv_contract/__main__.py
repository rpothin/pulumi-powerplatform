"""Example: Create a Power Platform ISV Contract."""

import pulumi

# Create an ISV contract for Power Platform licensing.
isv_contract = pulumi.CustomResource(
    "my-isv-contract",
    "powerplatform:index:IsvContract",
    {
        "name": "Contoso ISV Contract",
        "geo": "unitedstates",
        "status": "Enabled",
    },
)

# Export the ISV contract details
pulumi.export("isvContractId", isv_contract.id)
pulumi.export("isvContractName", isv_contract["name"])
