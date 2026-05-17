"""EnvironmentSettings resource handler — manage settings on a Power Platform environment.

Settings are split across two API surfaces:
- Tier 1 (5 props): api.powerplatform.com /environmentmanagement/environments/{id}/settings
- Tier 2 (7 props): Dataverse OData /api/data/v9.2/organizations({orgId})
"""

from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlparse

import pulumi
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckFailure,
    CheckRequest,
    CheckResponse,
    CreateRequest,
    CreateResponse,
    DeleteRequest,
    DiffRequest,
    DiffResponse,
    PropertyDiff,
    PropertyDiffKind,
    ReadRequest,
    ReadResponse,
    UpdateRequest,
    UpdateResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import HttpError, pv_to_comparable, resolve_dataverse_url
from rpothin_powerplatform.utils import pv_str as _pv_str

logger = logging.getLogger(__name__)

# ---- Tier-1: Power Platform API settings ------------------------------------

_SETTINGS_PROPS = (
    "maxUploadFileSize",
    "pluginTraceLogSetting",
    "isAuditEnabled",
    "isUserAccessAuditEnabled",
    "isActivityLoggingEnabled",
)

_PP_API_VERSION = "2022-03-01-preview"

# ---- Tier-2: Dataverse organizations table settings -------------------------

# (pulumi_property_name, dataverse_column, python_type)
_DV_PROPS: tuple[tuple[str, str, type], ...] = (
    ("isReadAuditEnabled",                       "isreadauditenabled",                  bool),
    ("auditRetentionPeriodInDays",               "auditretentionperiodv2",              int),
    ("allowApplicationUserAccess",               "allowapplicationuseraccess",          bool),
    ("allowMicrosoftTrustedServiceTags",         "allowmicrosofttrustedservicetags",    bool),
    ("reverseProxyIpAddresses",                  "reverseproxyipaddresses",             str),
    ("powerAppsComponentFrameworkForCanvasApps", "iscustomcontrolsincanvasappsenabled",  bool),
    ("showDashboardCardsInExpandedState",         "bounddashboarddefaultcardexpanded",   bool),
)

_DV_PROP_NAMES: tuple[str, ...] = tuple(p for p, _, _ in _DV_PROPS)
# Comma-separated column list for Dataverse $select queries.
_DV_SELECT = ",".join(col for _, col, _ in _DV_PROPS)


class EnvironmentSettingsResource:
    """Handles CRUD operations for powerplatform:index:EnvironmentSettings."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    # ---- Public interface ---------------------------------------------------

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for environment settings."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        if not env_id:
            failures.append(
                CheckFailure(
                    property="environmentId",
                    reason="environmentId is required and cannot be empty.",
                )
            )

        # auditRetentionPeriodInDays must be -1 (forever) or in range 31–24855.
        retention_pv = inputs.get("auditRetentionPeriodInDays")
        if retention_pv is not None and retention_pv.value is not None:
            try:
                retention_val = int(retention_pv.value)
                if retention_val != -1 and not (31 <= retention_val <= 24855):
                    failures.append(
                        CheckFailure(
                            property="auditRetentionPeriodInDays",
                            reason=(
                                "auditRetentionPeriodInDays must be -1 (retain forever) "
                                "or between 31 and 24855 days."
                            ),
                        )
                    )
            except (TypeError, ValueError):
                failures.append(
                    CheckFailure(
                        property="auditRetentionPeriodInDays",
                        reason="auditRetentionPeriodInDays must be an integer.",
                    )
                )

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for environment settings."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}

        old = request.old_state
        new = request.new_inputs

        # environmentId is immutable — changes require resource replacement.
        if _pv_str(old.get("environmentId")) != _pv_str(new.get("environmentId")):
            diffs.append("environmentId")
            detailed["environmentId"] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)

        # Tier-1 (PP API) settings — string-typed.
        for prop in _SETTINGS_PROPS:
            if _pv_str(old.get(prop)) != _pv_str(new.get(prop)):
                diffs.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        # Tier-2 (Dataverse) settings — native bool/int/str types; use json-comparable.
        for pulumi_prop, _, _ in _DV_PROPS:
            if pv_to_comparable(old.get(pulumi_prop)) != pv_to_comparable(new.get(pulumi_prop)):
                diffs.append(pulumi_prop)
                detailed[pulumi_prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Apply settings to an environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties
        env_id = _pv_str(props.get("environmentId"))
        if not env_id:
            raise RuntimeError("environmentId is required.")

        # Preflight: resolve Dataverse before any writes to avoid partial state.
        dv_body = _build_dv_body(props)
        dv_client, org_id = await self._preflight_dv(env_id, dv_body)

        # Write Tier-1 settings.
        settings_body = _build_settings_body(props)
        if settings_body:
            await self._client.raw_pp.request(
                "PATCH",
                f"/environmentmanagement/environments/{env_id}/settings",
                body=settings_body,
                api_version=_PP_API_VERSION,
            )

        # Write Tier-2 settings.
        if dv_client and org_id and dv_body:
            await self._write_dv_settings(dv_client, org_id, dv_body)

        # Read back both tiers.
        current = await self._read_settings(env_id)
        dv_settings = await self._read_dv_settings(dv_client, org_id) if dv_client and org_id else {}

        return CreateResponse(
            resource_id=env_id,
            properties=_settings_to_outputs(env_id, current, dv_settings),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current settings of an environment."""
        env_id = request.resource_id

        try:
            current = await self._read_settings(env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        # Only read Dataverse if the user currently has DV props in their inputs.
        dv_settings: dict = {}
        if _has_dv_inputs(request.inputs):
            try:
                instance_url = await resolve_dataverse_url(self._client.raw, env_id)
                if instance_url:
                    dv_client = self._make_dataverse_client(instance_url)
                    org_id = await self._get_org_id(dv_client)
                    dv_settings = await self._read_dv_settings(dv_client, org_id)
                else:
                    pulumi.warn(
                        f"EnvironmentSettings: environment {env_id!r} has DV props configured "
                        "but no Dataverse instance was found — DV settings will not be refreshed."
                    )
            except HttpError:
                logger.warning(
                    "Failed to read Dataverse settings for environment %r during refresh; "
                    "DV properties will be omitted from state.",
                    env_id,
                )

        outputs = _settings_to_outputs(env_id, current, dv_settings)
        inputs = {k: v for k, v in outputs.items() if k in _INPUT_PROP_NAMES}
        return ReadResponse(resource_id=env_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update settings on an environment."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        env_id = request.resource_id
        props = request.news

        # Preflight: resolve Dataverse before any writes.
        dv_body = _build_dv_body(props)
        dv_client, org_id = await self._preflight_dv(env_id, dv_body)

        # Write Tier-1 settings.
        settings_body = _build_settings_body(props)
        if settings_body:
            await self._client.raw_pp.request(
                "PATCH",
                f"/environmentmanagement/environments/{env_id}/settings",
                body=settings_body,
                api_version=_PP_API_VERSION,
            )

        # Write Tier-2 settings.
        if dv_client and org_id and dv_body:
            await self._write_dv_settings(dv_client, org_id, dv_body)

        current = await self._read_settings(env_id)
        dv_settings = await self._read_dv_settings(dv_client, org_id) if dv_client and org_id else {}

        return UpdateResponse(properties=_settings_to_outputs(env_id, current, dv_settings))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete is a no-op for environment settings (cannot unset settings)."""
        pulumi.warn(
            f"EnvironmentSettings for environment {request.resource_id} cannot be deleted. "
            "Settings will be removed from Pulumi state only — they remain active on the environment."
        )

    # ---- Internal helpers --------------------------------------------------

    async def _preflight_dv(
        self,
        env_id: str,
        dv_body: dict,
    ) -> tuple[Optional[RawApiClient], Optional[str]]:
        """Resolve Dataverse client and org ID before any writes.

        Returns (None, None) when no DV props are being set.
        Raises RuntimeError if DV props are present but the environment has no Dataverse.
        """
        if not dv_body:
            return None, None

        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(
                f"Environment {env_id!r} has no Dataverse instance; "
                "cannot apply Dataverse settings."
            )

        dv_client = self._make_dataverse_client(instance_url)
        org_id = await self._get_org_id(dv_client)
        return dv_client, org_id

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        """Create a RawApiClient scoped to the given Dataverse instance URL."""
        parsed = urlparse(instance_url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Invalid Dataverse instance URL: {instance_url!r}")
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )

    async def _get_org_id(self, dv_client: RawApiClient) -> str:
        """Fetch the organization GUID from this Dataverse instance."""
        resp = await dv_client.request(
            "GET",
            "/api/data/v9.2/organizations?$select=organizationid",
            api_version=None,
        )
        orgs = (resp or {}).get("value", [])
        if not orgs:
            raise RuntimeError("No organizations found in this Dataverse instance.")
        return str(orgs[0]["organizationid"])

    async def _read_settings(self, env_id: str) -> Optional[dict]:
        """Read current Tier-1 settings from the Power Platform API."""
        return await self._client.raw_pp.request(
            "GET",
            f"/environmentmanagement/environments/{env_id}/settings",
            api_version=_PP_API_VERSION,
        )

    async def _read_dv_settings(self, dv_client: RawApiClient, org_id: str) -> dict:
        """Read current Tier-2 settings from the Dataverse organizations table."""
        resp = await dv_client.request(
            "GET",
            f"/api/data/v9.2/organizations({org_id})?$select={_DV_SELECT}",
            api_version=None,
        )
        return resp or {}

    async def _write_dv_settings(
        self, dv_client: RawApiClient, org_id: str, body: dict
    ) -> None:
        """PATCH Dataverse organization settings."""
        await dv_client.request(
            "PATCH",
            f"/api/data/v9.2/organizations({org_id})",
            body=body,
            api_version=None,
        )


# ---- Module-level helpers --------------------------------------------------

_INPUT_PROP_NAMES = {"environmentId"} | set(_SETTINGS_PROPS) | set(_DV_PROP_NAMES)


def _has_dv_inputs(inputs: dict) -> bool:
    """Return True if any Dataverse property is present in the inputs map."""
    return any(inputs.get(p) is not None for p in _DV_PROP_NAMES)


def _build_settings_body(props: dict[str, PropertyValue]) -> dict:
    """Build the PATCH body for Tier-1 (PP API) settings from input properties."""
    body: dict = {}
    for prop in _SETTINGS_PROPS:
        val = _pv_str(props.get(prop))
        if val is not None:
            if val.lower() in ("true", "false"):
                body[prop] = val.lower() == "true"
            else:
                try:
                    body[prop] = int(val)
                except ValueError:
                    body[prop] = val
    return body


def _build_dv_body(props: dict[str, PropertyValue]) -> dict:
    """Build the PATCH body for Tier-2 (Dataverse) settings from input properties."""
    body: dict = {}
    for pulumi_prop, dv_col, _type in _DV_PROPS:
        pv = props.get(pulumi_prop)
        if pv is None or pv.value is None:
            continue
        val = pv.value
        # Coerce to the expected Dataverse type regardless of how Pulumi delivered it.
        if _type is bool:
            body[dv_col] = bool(val)
        elif _type is int:
            body[dv_col] = int(val)
        else:
            body[dv_col] = str(val)
    return body


def _settings_to_outputs(
    env_id: str,
    settings: Optional[dict],
    dv_settings: Optional[dict] = None,
) -> dict[str, PropertyValue]:
    """Convert API responses to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {"environmentId": PropertyValue(env_id)}

    if settings:
        for prop in _SETTINGS_PROPS:
            val = settings.get(prop)
            if val is not None:
                outputs[prop] = PropertyValue(str(val).lower() if isinstance(val, bool) else str(val))

    if dv_settings:
        for pulumi_prop, dv_col, _type in _DV_PROPS:
            val = dv_settings.get(dv_col)
            if val is not None:
                # Preserve native types so schema (boolean/integer) round-trips correctly.
                if _type is bool:
                    outputs[pulumi_prop] = PropertyValue(bool(val))
                elif _type is int:
                    # PropertyValue accepts float for numbers (JSON-compatible)
                    outputs[pulumi_prop] = PropertyValue(float(val))
                else:
                    outputs[pulumi_prop] = PropertyValue(str(val))

    return outputs
