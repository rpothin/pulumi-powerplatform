"""Power Platform Environment resource."""

import re
from typing import Optional

import pulumi


@pulumi.input_type
class EnvironmentDataverseArgs:
    """Input arguments for provisioning a Dataverse database on an environment."""

    def __init__(
        self,
        *,
        currency_code: Optional[pulumi.Input[str]] = None,
        language_code: Optional[pulumi.Input[str]] = None,
        domain_name: Optional[pulumi.Input[str]] = None,
        security_group_id: Optional[pulumi.Input[str]] = None,
        templates: Optional[pulumi.Input[list]] = None,
        template_metadata: Optional[pulumi.Input[str]] = None,
        administration_mode_enabled: Optional[pulumi.Input[bool]] = None,
        background_operation_enabled: Optional[pulumi.Input[bool]] = None,
    ):
        if currency_code is not None:
            pulumi.set(self, "currency_code", currency_code)
        if language_code is not None:
            pulumi.set(self, "language_code", language_code)
        if domain_name is not None:
            pulumi.set(self, "domain_name", domain_name)
        if security_group_id is not None:
            pulumi.set(self, "security_group_id", security_group_id)
        if templates is not None:
            pulumi.set(self, "templates", templates)
        if template_metadata is not None:
            pulumi.set(self, "template_metadata", template_metadata)
        if administration_mode_enabled is not None:
            pulumi.set(self, "administration_mode_enabled", administration_mode_enabled)
        if background_operation_enabled is not None:
            pulumi.set(self, "background_operation_enabled", background_operation_enabled)

    @property
    @pulumi.getter(name="currencyCode")
    def currency_code(self) -> Optional[pulumi.Input[str]]:
        return pulumi.get(self, "currency_code")

    @currency_code.setter
    def currency_code(self, value: Optional[pulumi.Input[str]]):
        pulumi.set(self, "currency_code", value)

    @property
    @pulumi.getter(name="languageCode")
    def language_code(self) -> Optional[pulumi.Input[str]]:
        return pulumi.get(self, "language_code")

    @language_code.setter
    def language_code(self, value: Optional[pulumi.Input[str]]):
        pulumi.set(self, "language_code", value)

    @property
    @pulumi.getter(name="domainName")
    def domain_name(self) -> Optional[pulumi.Input[str]]:
        return pulumi.get(self, "domain_name")

    @domain_name.setter
    def domain_name(self, value: Optional[pulumi.Input[str]]):
        pulumi.set(self, "domain_name", value)

    @property
    @pulumi.getter(name="securityGroupId")
    def security_group_id(self) -> Optional[pulumi.Input[str]]:
        return pulumi.get(self, "security_group_id")

    @security_group_id.setter
    def security_group_id(self, value: Optional[pulumi.Input[str]]):
        pulumi.set(self, "security_group_id", value)

    @property
    @pulumi.getter(name="templates")
    def templates(self) -> Optional[pulumi.Input[list]]:
        return pulumi.get(self, "templates")

    @templates.setter
    def templates(self, value: Optional[pulumi.Input[list]]):
        pulumi.set(self, "templates", value)

    @property
    @pulumi.getter(name="templateMetadata")
    def template_metadata(self) -> Optional[pulumi.Input[str]]:
        return pulumi.get(self, "template_metadata")

    @template_metadata.setter
    def template_metadata(self, value: Optional[pulumi.Input[str]]):
        pulumi.set(self, "template_metadata", value)

    @property
    @pulumi.getter(name="administrationModeEnabled")
    def administration_mode_enabled(self) -> Optional[pulumi.Input[bool]]:
        return pulumi.get(self, "administration_mode_enabled")

    @administration_mode_enabled.setter
    def administration_mode_enabled(self, value: Optional[pulumi.Input[bool]]):
        pulumi.set(self, "administration_mode_enabled", value)

    @property
    @pulumi.getter(name="backgroundOperationEnabled")
    def background_operation_enabled(self) -> Optional[pulumi.Input[bool]]:
        return pulumi.get(self, "background_operation_enabled")

    @background_operation_enabled.setter
    def background_operation_enabled(self, value: Optional[pulumi.Input[bool]]):
        pulumi.set(self, "background_operation_enabled", value)


@pulumi.output_type
class EnvironmentDataverse:
    """Dataverse database properties returned for a provisioned environment."""

    def __init__(
        self,
        *,
        domain_name: Optional[str] = None,
        currency_code: Optional[str] = None,
        language_code: Optional[float] = None,
        security_group_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        unique_name: Optional[str] = None,
        version: Optional[str] = None,
        url: Optional[str] = None,
        templates: Optional[list] = None,
        template_metadata: Optional[str] = None,
        administration_mode_enabled: Optional[bool] = None,
        background_operation_enabled: Optional[bool] = None,
    ):
        pulumi.set(self, "domain_name", domain_name)
        pulumi.set(self, "currency_code", currency_code)
        pulumi.set(self, "language_code", language_code)
        pulumi.set(self, "security_group_id", security_group_id)
        pulumi.set(self, "organization_id", organization_id)
        pulumi.set(self, "unique_name", unique_name)
        pulumi.set(self, "version", version)
        pulumi.set(self, "url", url)
        pulumi.set(self, "templates", templates)
        pulumi.set(self, "template_metadata", template_metadata)
        pulumi.set(self, "administration_mode_enabled", administration_mode_enabled)
        pulumi.set(self, "background_operation_enabled", background_operation_enabled)

    @property
    @pulumi.getter(name="domainName")
    def domain_name(self) -> Optional[str]:
        return pulumi.get(self, "domain_name")

    @property
    @pulumi.getter(name="currencyCode")
    def currency_code(self) -> Optional[str]:
        return pulumi.get(self, "currency_code")

    @property
    @pulumi.getter(name="languageCode")
    def language_code(self) -> Optional[float]:
        return pulumi.get(self, "language_code")

    @property
    @pulumi.getter(name="securityGroupId")
    def security_group_id(self) -> Optional[str]:
        return pulumi.get(self, "security_group_id")

    @property
    @pulumi.getter(name="organizationId")
    def organization_id(self) -> Optional[str]:
        return pulumi.get(self, "organization_id")

    @property
    @pulumi.getter(name="uniqueName")
    def unique_name(self) -> Optional[str]:
        return pulumi.get(self, "unique_name")

    @property
    @pulumi.getter(name="version")
    def version(self) -> Optional[str]:
        return pulumi.get(self, "version")

    @property
    @pulumi.getter(name="url")
    def url(self) -> Optional[str]:
        return pulumi.get(self, "url")

    @property
    @pulumi.getter(name="templates")
    def templates(self) -> Optional[list]:
        return pulumi.get(self, "templates")

    @property
    @pulumi.getter(name="templateMetadata")
    def template_metadata(self) -> Optional[str]:
        return pulumi.get(self, "template_metadata")

    @property
    @pulumi.getter(name="administrationModeEnabled")
    def administration_mode_enabled(self) -> Optional[bool]:
        return pulumi.get(self, "administration_mode_enabled")

    @property
    @pulumi.getter(name="backgroundOperationEnabled")
    def background_operation_enabled(self) -> Optional[bool]:
        return pulumi.get(self, "background_operation_enabled")


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
    dataverse: pulumi.Output['EnvironmentDataverse']
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
        dataverse: Optional[pulumi.InputType['EnvironmentDataverseArgs']] = None,
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
