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
            "displayName": display_name,
            "description": description,
            "location": location,
            "environmentType": environment_type,
            "domainName": domain_name,
            "currencyCode": currency_code,
            "languageCode": language_code,
            "state": None,
            "url": None,
            "createdTime": None,
            "lastModifiedTime": None,
        }
        super().__init__("powerplatform:index:Environment", resource_name, props, opts)

    def _translate_output_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)
