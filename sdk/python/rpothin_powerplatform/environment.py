"""Power Platform Environment resource."""

import re
from typing import Optional

import pulumi


class Environment(pulumi.CustomResource):
    """Manages a Power Platform environment."""

    display_name: pulumi.Output[str]
    description: pulumi.Output[str]
    location: pulumi.Output[str]
    environment_type: pulumi.Output[str]
    domain_name: pulumi.Output[str]
    currency_code: pulumi.Output[str]
    language_code: pulumi.Output[str]
    state: pulumi.Output[str]
    url: pulumi.Output[str]
    created_time: pulumi.Output[str]
    last_modified_time: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        environment_type: Optional[str] = None,
        domain_name: Optional[str] = None,
        currency_code: Optional[str] = None,
        language_code: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "display_name": display_name,
            "description": description,
            "location": location,
            "environment_type": environment_type,
            "domain_name": domain_name,
            "currency_code": currency_code,
            "language_code": language_code,
            "state": None,
            "url": None,
            "created_time": None,
            "last_modified_time": None,
        }
        super().__init__("powerplatform:index:Environment", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
