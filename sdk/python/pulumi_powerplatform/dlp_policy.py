"""Power Platform DLP Policy resource."""

import pulumi
from typing import Any, Optional, Sequence


class DlpPolicy(pulumi.CustomResource):
    """Manages a Power Platform Data Loss Prevention (DLP) policy."""

    name: pulumi.Output[str]
    rule_sets: pulumi.Output[Optional[Sequence[Any]]]
    tenant_id: pulumi.Output[str]
    last_modified: pulumi.Output[str]
    rule_set_count: pulumi.Output[int]

    def __init__(
        self,
        resource_name: str,
        name: Optional[str] = None,
        rule_sets: Optional[Sequence[Any]] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "name": name,
            "ruleSets": rule_sets,
            "tenantId": None,
            "lastModified": None,
            "ruleSetCount": None,
        }
        super().__init__("powerplatform:index:DlpPolicy", resource_name, props, opts)
