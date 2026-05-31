"""AVM-aligned ``ResEnvironment`` component resource.

Mirrors the ``rpothin/terraform-powerplatform-res-environment`` AVM module:
composes ``Environment`` (required), ``ManagedEnvironment`` (optional, when
``managed_environment_enabled=True``), and ``EnvironmentSettings`` (optional,
when any settings field is provided).

Dependency order (matches TF module ``depends_on``)::

    Environment → (if managed) ManagedEnvironment → (if settings) EnvironmentSettings

No ``from __future__ import annotations`` — the Pulumi Analyzer needs runtime
type objects, not lazy string annotations.
"""

from dataclasses import dataclass
from typing import Optional

import pulumi

from ._base import COMPONENT_TOKEN_PREFIX, ComponentArgs, register_component, register_construct

#: Pulumi type token for this component.
COMPONENT_TYPE = f"{COMPONENT_TOKEN_PREFIX}ResEnvironment"


# ---------------------------------------------------------------------------
# Nested config types
# ---------------------------------------------------------------------------


@dataclass(kw_only=True)
class DataverseConfig:
    """Dataverse provisioning configuration.

    Mirrors the ``var.dataverse`` object in the AVM ``res-environment`` module.
    Passing a :class:`DataverseConfig` instance triggers Dataverse provisioning
    on the underlying ``Environment`` resource.

    Field names follow the AVM variable names (snake_case).  The component maps
    them to the camelCase wire names expected by the Pulumi provider.
    """

    currency_code: Optional[str] = None
    """Currency code for the Dataverse database (e.g. ``"USD"``).  Immutable."""

    language_code: Optional[int] = None
    """Base language LCID (e.g. ``1033`` for English).  Immutable."""

    security_group_id: Optional[str] = None
    """AAD security-group GUID restricting environment access."""

    domain: Optional[str] = None
    """Domain prefix for the Dataverse instance URL.  Maps to ``domainName`` on the wire."""

    administration_mode_enabled: Optional[bool] = None
    """Whether the Dataverse instance is in administration mode."""

    background_operation_enabled: Optional[bool] = None
    """Whether background operations run during administration mode.
    Mutually exclusive with ``administration_mode_enabled``."""

    template_metadata: Optional[str] = None
    """JSON metadata for provisioning templates.  Immutable."""

    templates: Optional[list[str]] = None
    """Provisioning templates (e.g. ``["D365_Sales"]``).  Immutable."""


# ---------------------------------------------------------------------------
# Component args
# ---------------------------------------------------------------------------


@dataclass(kw_only=True)
class ResEnvironmentArgs(ComponentArgs):
    """Input arguments for :class:`ResEnvironment`.

    Mirrors the variables of the AVM ``rpothin/terraform-powerplatform-res-environment``
    module.  Required fields match the AVM ``var.environment`` required attributes;
    optional fields provide AVM-parity without being mandatory.
    """

    # ------------------------------------------------------------------
    # Required
    # ------------------------------------------------------------------

    display_name: str
    """Display name of the environment.  Required."""

    location: str
    """Geographic region (e.g. ``"unitedstates"``).  Immutable.  Required."""

    # ------------------------------------------------------------------
    # Environment optional
    # ------------------------------------------------------------------

    environment_type: Optional[str] = None
    """SKU: ``Sandbox``, ``Production``, ``Trial``, ``Developer``, or ``Default``.
    Defaults to ``Sandbox`` when omitted.  Immutable."""

    description: Optional[str] = None
    """Human-readable description of the environment."""

    azure_region: Optional[str] = None
    """Specific Azure region within the location geo (e.g. ``"westus2"``).  Immutable."""

    billing_policy_id: Optional[str] = None
    """ID of the billing policy to associate with this environment."""

    cadence: Optional[str] = None
    """Release wave cadence: ``Frequent`` or ``Moderate``.  Immutable."""

    environment_group_id: Optional[str] = None
    """ID of the environment group this environment belongs to.
    Requires ``dataverse`` to be set."""

    allow_bing_search: Optional[bool] = None
    """Allow Bing Search integration (AI generative features)."""

    allow_moving_data_across_regions: Optional[bool] = None
    """Allow data to move across geographic boundaries for Copilot features."""

    # ------------------------------------------------------------------
    # Dataverse
    # ------------------------------------------------------------------

    dataverse: Optional[DataverseConfig] = None
    """Dataverse provisioning configuration.  Omit to skip Dataverse provisioning."""

    # ------------------------------------------------------------------
    # Managed environment
    # ------------------------------------------------------------------

    managed_environment_enabled: Optional[bool] = None
    """Enable Managed Environment features.  Requires ``dataverse`` to be set."""

    # ------------------------------------------------------------------
    # Environment settings (→ EnvironmentSettings child resource)
    # ------------------------------------------------------------------

    is_audit_enabled: Optional[bool] = None
    """Enable audit logging."""

    is_read_audit_enabled: Optional[bool] = None
    """Enable read-operation audit logging."""

    is_user_access_audit_enabled: Optional[bool] = None
    """Enable user-access audit logging."""

    audit_retention_period_in_days: Optional[int] = None
    """Audit log retention period in days."""

    plugin_trace_log_setting: Optional[str] = None
    """Plug-in trace log setting (``Off``, ``Exception``, or ``All``)."""

    max_upload_file_size: Optional[str] = None
    """Maximum upload file size string (e.g. ``"5242880"`` for 5 MB)."""

    show_dashboard_cards_in_expanded_state: Optional[bool] = None
    """Show dashboard cards in expanded state by default."""


# ---------------------------------------------------------------------------
# Component resource
# ---------------------------------------------------------------------------


@register_component
class ResEnvironment(pulumi.ComponentResource):
    """AVM-aligned component that manages a Power Platform environment lifecycle.

    Composes:

    * :class:`~rpothin_powerplatform.Environment` — always created.
    * :class:`~rpothin_powerplatform.ManagedEnvironment` — when
      ``args.managed_environment_enabled`` is ``True``.
    * :class:`~rpothin_powerplatform.EnvironmentSettings` — when any settings
      field is provided.

    All child resources inherit the parent component's provider configuration
    through ``opts.providers`` / ``opts.provider`` so callers can supply an
    explicit provider without repeating it for every child.
    """

    resource_id: pulumi.Output[str]
    """AVM-standard primary output: the environment resource ID."""

    environment_display_name: pulumi.Output[str]
    """Display name of the provisioned environment."""

    environment_url: pulumi.Output[str]
    """URL of the Dataverse instance.  Empty string when no Dataverse is provisioned."""

    dataverse_organization_id: pulumi.Output[str]
    """Dataverse organisation GUID.  Empty string when no Dataverse is provisioned."""

    managed_environment_id: pulumi.Output[str]
    """Resource ID of the Managed Environment.  Empty string when not enabled."""

    def __init__(
        self,
        name: str,
        args: ResEnvironmentArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(COMPONENT_TYPE, name, {}, opts)

        # Lazy import — avoids pulling provider side-effects at schema-gen time.
        from ._resource_wrappers import (  # noqa: PLC0415
            _EnvironmentSettingsWrap,
            _EnvironmentWrap,
            _ManagedEnvironmentWrap,
        )

        # Build child ResourceOptions: parent=self + propagate provider config.
        # We explicitly propagate providers/provider rather than doing a full merge
        # to avoid inadvertently carrying component-level depends_on or protect
        # flags down into children.
        child_opts = pulumi.ResourceOptions(
            parent=self,
            providers=(opts.providers if opts else None),
            provider=(opts.provider if opts else None),
        )

        # ------------------------------------------------------------------
        # Build dataverse dict (camelCase wire names for the provider).
        # ------------------------------------------------------------------
        dv_dict: Optional[dict] = None
        if args.dataverse is not None:
            dv = args.dataverse
            dv_dict = {
                k: v
                for k, v in {
                    "currencyCode": dv.currency_code,
                    "languageCode": dv.language_code,
                    "securityGroupId": dv.security_group_id,
                    "domainName": dv.domain,
                    "administrationModeEnabled": dv.administration_mode_enabled,
                    "backgroundOperationEnabled": dv.background_operation_enabled,
                    "templateMetadata": dv.template_metadata,
                    "templates": dv.templates,
                }.items()
                if v is not None
            }

        # ------------------------------------------------------------------
        # Environment (required child)
        # ------------------------------------------------------------------
        env = _EnvironmentWrap(
            f"{name}-environment",
            display_name=args.display_name,
            location=args.location,
            environment_type=args.environment_type,
            allow_bing_search=args.allow_bing_search,
            allow_moving_data_across_regions=args.allow_moving_data_across_regions,
            azure_region=args.azure_region,
            billing_policy_id=args.billing_policy_id,
            cadence=args.cadence,
            dataverse=dv_dict,
            description=args.description,
            environment_group_id=args.environment_group_id,
            opts=child_opts,
        )

        # ------------------------------------------------------------------
        # ManagedEnvironment (optional — concrete bool from factory).
        # ------------------------------------------------------------------
        managed_env: Optional[_ManagedEnvironmentWrap] = None
        if args.managed_environment_enabled:
            managed_env = _ManagedEnvironmentWrap(
                f"{name}-managed",
                environment_id=env.id,
                opts=pulumi.ResourceOptions(
                    parent=self,
                    providers=(opts.providers if opts else None),
                    provider=(opts.provider if opts else None),
                    depends_on=[env],
                ),
            )

        # ------------------------------------------------------------------
        # EnvironmentSettings (optional — created when any settings field set).
        # ------------------------------------------------------------------
        has_settings = any(
            v is not None
            for v in [
                args.is_audit_enabled,
                args.is_read_audit_enabled,
                args.is_user_access_audit_enabled,
                args.audit_retention_period_in_days,
                args.plugin_trace_log_setting,
                args.max_upload_file_size,
                args.show_dashboard_cards_in_expanded_state,
            ]
        )
        if has_settings:
            settings_deps: list[pulumi.Resource] = [env]
            if managed_env is not None:
                settings_deps.append(managed_env)
            _EnvironmentSettingsWrap(
                f"{name}-settings",
                environment_id=env.id,
                is_audit_enabled=args.is_audit_enabled,
                is_read_audit_enabled=args.is_read_audit_enabled,
                is_user_access_audit_enabled=args.is_user_access_audit_enabled,
                audit_retention_period_in_days=args.audit_retention_period_in_days,
                plugin_trace_log_setting=args.plugin_trace_log_setting,
                max_upload_file_size=args.max_upload_file_size,
                show_dashboard_cards_in_expanded_state=args.show_dashboard_cards_in_expanded_state,
                opts=pulumi.ResourceOptions(
                    parent=self,
                    providers=(opts.providers if opts else None),
                    provider=(opts.provider if opts else None),
                    depends_on=settings_deps,
                ),
            )

        # ------------------------------------------------------------------
        # Component outputs
        # ------------------------------------------------------------------
        self.resource_id = env.id
        self.environment_display_name = env.display_name
        self.environment_url = env.environment_url.apply(lambda v: v or "")
        self.dataverse_organization_id = env.dataverse_organization_id.apply(lambda v: v or "")
        self.managed_environment_id = (
            managed_env.id if managed_env is not None else pulumi.Output.from_input("")
        )
        self.register_outputs(
            {
                "resourceId": self.resource_id,
                "environmentDisplayName": self.environment_display_name,
                "environmentUrl": self.environment_url,
                "dataverseOrganizationId": self.dataverse_organization_id,
                "managedEnvironmentId": self.managed_environment_id,
            }
        )


# ---------------------------------------------------------------------------
# Construct factory (called by the provider's construct dispatch)
# ---------------------------------------------------------------------------


@register_construct(COMPONENT_TYPE)
async def _construct_res_environment(
    name: str,
    inputs: dict,
    opts: Optional[pulumi.ResourceOptions],
) -> object:
    """Async factory for :class:`ResEnvironment` — called by the provider's ``construct`` dispatch.

    All value inputs are converted via :func:`~construct_bridge.pv_to_input` so
    that secret, unknown, and dependency metadata is preserved for the Pulumi
    engine.  Boolean *control-flow* inputs (``managedEnvironmentEnabled``,
    ``dataverse`` presence) are extracted from the raw
    :class:`~pulumi.provider.experimental.property_value.PropertyValue` value to
    keep Python ``if``/``bool()`` semantics correct during preview.
    """
    # Lazy imports — keeps this module safe to load in isolation by merge-schema.py.
    from pulumi.provider.experimental.property_value import (  # noqa: PLC0415
        Computed,
        PropertyValue,
    )
    from pulumi.provider.experimental.provider import ConstructResponse  # noqa: PLC0415

    from ..construct_bridge import pv_to_input, resolve_outputs  # noqa: PLC0415

    def _pv(key: str, default=None):
        """Convert a named input to a Python value / Output, preserving metadata."""
        return pv_to_input(inputs.get(key, PropertyValue(default)))

    def _pv_bool(key: str) -> Optional[bool]:
        """Return the concrete bool value of a PV, or None if unknown/absent."""
        pv = inputs.get(key)
        if pv is None:
            return None
        v = pv.value
        return v if isinstance(v, bool) else None

    # ------------------------------------------------------------------
    # Reconstruct DataverseConfig from the nested PropertyValue dict.
    # Each inner value is itself a PropertyValue; skip Computed (unknown) ones.
    # ------------------------------------------------------------------
    dv_pv = inputs.get("dataverse")
    dv_config: Optional[DataverseConfig] = None
    if dv_pv is not None and hasattr(dv_pv.value, "get"):
        d = dv_pv.value  # mappingproxy or dict, both support .get()

        def _dvscalar(k: str, coerce=None):
            inner = d.get(k)
            if inner is None:
                return None
            v = inner.value
            if v is None or isinstance(v, Computed):
                return None
            return coerce(v) if coerce is not None else v

        def _dvscalar_list(k: str) -> Optional[list]:
            """Unwrap a PropertyValue list/tuple into a Python list of plain values.

            If any element is Computed (unknown during preview), the whole list
            is returned as ``None`` so control-flow using the list stays safe.
            """
            inner = d.get(k)
            if inner is None:
                return None
            lst = inner.value
            # Pulumi may represent lists as tuple in PropertyValue
            if lst is None or isinstance(lst, Computed) or not isinstance(lst, (list, tuple)):
                return None
            result = []
            for item in lst:
                item_v = item.value if isinstance(item, PropertyValue) else item
                if isinstance(item_v, Computed):
                    return None  # unknown element → skip whole list
                result.append(item_v)
            return result or None

        raw_lang = _dvscalar("languageCode")
        dv_config = DataverseConfig(
            currency_code=_dvscalar("currencyCode"),
            language_code=int(raw_lang) if raw_lang is not None else None,
            security_group_id=_dvscalar("securityGroupId"),
            domain=_dvscalar("domainName"),
            administration_mode_enabled=_dvscalar("administrationModeEnabled"),
            background_operation_enabled=_dvscalar("backgroundOperationEnabled"),
            template_metadata=_dvscalar("templateMetadata"),
            templates=_dvscalar_list("templates"),
        )

    args = ResEnvironmentArgs(
        # Required
        display_name=_pv("displayName"),
        location=_pv("location"),
        # Environment optional
        environment_type=_pv("environmentType"),
        description=_pv("description"),
        azure_region=_pv("azureRegion"),
        billing_policy_id=_pv("billingPolicyId"),
        cadence=_pv("cadence"),
        environment_group_id=_pv("environmentGroupId"),
        allow_bing_search=_pv("allowBingSearch"),
        allow_moving_data_across_regions=_pv("allowMovingDataAcrossRegions"),
        # Dataverse (concrete DataverseConfig or None — safe for control flow)
        dataverse=dv_config,
        # Managed environment (concrete bool — safe for `if` check)
        managed_environment_enabled=_pv_bool("managedEnvironmentEnabled"),
        # Settings (concrete values — safe for `any()` check)
        is_audit_enabled=_pv_bool("isAuditEnabled"),
        is_read_audit_enabled=_pv_bool("isReadAuditEnabled"),
        is_user_access_audit_enabled=_pv_bool("isUserAccessAuditEnabled"),
        audit_retention_period_in_days=_pv("auditRetentionPeriodInDays"),
        plugin_trace_log_setting=_pv("pluginTraceLogSetting"),
        max_upload_file_size=_pv("maxUploadFileSize"),
        show_dashboard_cards_in_expanded_state=_pv_bool("showDashboardCardsInExpandedState"),
        enable_telemetry=_pv_bool("enableTelemetry"),
    )

    comp = ResEnvironment(name, args=args, opts=opts)
    urn = await comp.urn.future()
    state = await resolve_outputs(
        {
            "resourceId": comp.resource_id,
            "environmentDisplayName": comp.environment_display_name,
            "environmentUrl": comp.environment_url,
            "dataverseOrganizationId": comp.dataverse_organization_id,
            "managedEnvironmentId": comp.managed_environment_id,
        }
    )
    return ConstructResponse(urn=urn, state=state, state_dependencies={})
