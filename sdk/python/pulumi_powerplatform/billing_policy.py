"""Power Platform Billing Policy resource."""

import pulumi
from typing import Any, Optional


class BillingPolicy(pulumi.CustomResource):
    """Manages a Power Platform billing policy."""

    name: pulumi.Output[str]
    location: pulumi.Output[str]
    status: pulumi.Output[Optional[str]]
    billing_instrument: pulumi.Output[Optional[Any]]
    created_on: pulumi.Output[str]
    last_modified_on: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        name: str = None,
        location: str = None,
        status: str = None,
        billing_instrument: Any = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "name": name,
            "location": location,
            "status": status,
            "billingInstrument": billing_instrument,
            "createdOn": None,
            "lastModifiedOn": None,
        }
        super().__init__("powerplatform:index:BillingPolicy", resource_name, props, opts)
