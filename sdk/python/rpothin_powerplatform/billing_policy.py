"""Power Platform Billing Policy resource."""

import re
from typing import Any, Optional

import pulumi


class BillingPolicy(pulumi.CustomResource):
    """Manages a Power Platform billing policy."""

    name: pulumi.Output[str]
    location: pulumi.Output[str]
    status: pulumi.Output[str]
    billing_instrument: pulumi.Output[Any]
    created_on: pulumi.Output[str]
    last_modified_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        name: Optional[str] = None,
        location: Optional[str] = None,
        status: Optional[str] = None,
        billing_instrument: Optional[Any] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "name": name,
            "location": location,
            "status": status,
            "billing_instrument": billing_instrument,
            "created_on": None,
            "last_modified_on": None,
        }
        super().__init__("powerplatform:index:BillingPolicy", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
