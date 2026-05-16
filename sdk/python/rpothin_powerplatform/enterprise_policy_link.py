"""Power Platform EnterprisePolicyLink resource."""

import re
from typing import Optional

import pulumi


class EnterprisePolicyLink(pulumi.CustomResource):
    """Links an Azure enterprise policy to a Power Platform environment.

    Uses an async POST/poll lifecycle to establish the link.  All properties
    are immutable — any change triggers a full replacement (delete-then-create).

    Supported ``policy_type`` values: ``NetworkInjection``, ``Encryption``, ``Identity``.
    """

    environment_id: pulumi.Output[str]
    policy_type: pulumi.Output[str]
    system_id: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        policy_type: Optional[str] = None,
        system_id: Optional[str] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environment_id": environment_id,
            "policy_type": policy_type,
            "system_id": system_id,
        }
        super().__init__("powerplatform:index:EnterprisePolicyLink", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
