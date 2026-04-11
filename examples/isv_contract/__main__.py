"""Example: Create a Power Platform ISV Contract."""

import pulumi
import pulumi_powerplatform as pp

isv_contract = pp.IsvContract(
    "my-isv-contract",
    name="Contoso ISV Contract",
    geo="unitedstates",
    status="Enabled",
)

pulumi.export("isvContractId", isv_contract.id)
pulumi.export("isvContractName", isv_contract.name)
