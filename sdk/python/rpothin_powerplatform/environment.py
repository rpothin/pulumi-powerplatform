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
    azure_region: pulumi.Output[str]
    owner_id: pulumi.Output[str]
    cadence: pulumi.Output[str]
    billing_policy_id: pulumi.Output[str]
    environment_group_id: pulumi.Output[str]
    allow_bing_search: pulumi.Output[bool]
    allow_moving_data_across_regions: pulumi.Output[bool]
    linked_app_type: pulumi.Output[str]
    linked_app_id: pulumi.Output[str]
    enterprise_policies: pulumi.Output[list]
    dataverse: pulumi.Output[dict]
    state: pulumi.Output[str]
    linked_app_url: pulumi.Output[str]
    created_time: pulumi.Output[str]
    last_modified_time: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        location: Optional[str] = None,
        environment_type: Optional[str] = None,
        azure_region: Optional[str] = None,
        owner_id: Optional[str] = None,
        cadence: Optional[str] = None,
        billing_policy_id: Optional[str] = None,
        environment_group_id: Optional[str] = None,
        allow_bing_search: Optional[bool] = None,
        allow_moving_data_across_regions: Optional[bool] = None,
        linked_app_type: Optional[str] = None,
        linked_app_id: Optional[str] = None,
        enterprise_policies: Optional[list] = None,
        dataverse: Optional[dict] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "display_name": display_name,
            "description": description,
            "location": location,
            "environment_type": environment_type,
            "azure_region": azure_region,
            "owner_id": owner_id,
            "cadence": cadence,
            "billing_policy_id": billing_policy_id,
            "environment_group_id": environment_group_id,
            "allow_bing_search": allow_bing_search,
            "allow_moving_data_across_regions": allow_moving_data_across_regions,
            "linked_app_type": linked_app_type,
            "linked_app_id": linked_app_id,
            "enterprise_policies": enterprise_policies,
            "dataverse": dataverse,
            # Computed outputs
            "state": None,
            "linked_app_url": None,
            "created_time": None,
            "last_modified_time": None,
        }
        super().__init__("powerplatform:index:Environment", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)
