"""Power Platform ISV Contract resource."""

import pulumi
from typing import Optional


class IsvContract(pulumi.CustomResource):
    """Manages an ISV (Independent Software Vendor) contract for Power Platform licensing."""

    name: pulumi.Output[str]
    geo: pulumi.Output[str]
    status: pulumi.Output[Optional[str]]
    created_on: pulumi.Output[str]
    last_modified_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        name: str = None,
        geo: str = None,
        status: str = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "name": name,
            "geo": geo,
            "status": status,
            "createdOn": None,
            "lastModifiedOn": None,
        }
        super().__init__("powerplatform:index:IsvContract", resource_name, props, opts)
