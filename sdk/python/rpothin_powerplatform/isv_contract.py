"""Power Platform ISV Contract resource."""

import re
from typing import Optional

import pulumi


class IsvContract(pulumi.CustomResource):
    """Manages an ISV (Independent Software Vendor) contract for Power Platform licensing."""

    name: pulumi.Output[str]
    geo: pulumi.Output[str]
    status: pulumi.Output[str]
    created_on: pulumi.Output[str]
    last_modified_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        name: Optional[str] = None,
        geo: Optional[str] = None,
        status: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "name": name,
            "geo": geo,
            "status": status,
            "createdOn": None,
            "lastModifiedOn": None,
        }
        super().__init__("powerplatform:index:IsvContract", resource_name, props, opts)

    def _translate_output_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)
