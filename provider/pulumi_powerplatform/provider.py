"""Power Platform Pulumi provider — dispatches CRUD and invoke operations to resource/function handlers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pulumi.provider.experimental.provider import (
    CheckRequest,
    CheckResponse,
    ConfigureRequest,
    ConfigureResponse,
    CreateRequest,
    CreateResponse,
    DeleteRequest,
    DiffRequest,
    DiffResponse,
    GetSchemaRequest,
    GetSchemaResponse,
    InvokeRequest,
    InvokeResponse,
    Provider,
    ReadRequest,
    ReadResponse,
    UpdateRequest,
    UpdateResponse,
)

from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.config import resolve_client
from pulumi_powerplatform.functions.get_apps import GetAppsFunction
from pulumi_powerplatform.functions.get_connectors import GetConnectorsFunction
from pulumi_powerplatform.functions.get_environments import GetEnvironmentsFunction
from pulumi_powerplatform.functions.get_flows import GetFlowsFunction
from pulumi_powerplatform.resources.billing_policy import BillingPolicyResource
from pulumi_powerplatform.resources.dlp_policy import DlpPolicyResource
from pulumi_powerplatform.resources.environment_backup import EnvironmentBackupResource
from pulumi_powerplatform.resources.environment_group import EnvironmentGroupResource
from pulumi_powerplatform.resources.isv_contract import IsvContractResource
from pulumi_powerplatform.resources.managed_environment import ManagedEnvironmentResource
from pulumi_powerplatform.resources.role_assignment import RoleAssignmentResource

# Resource type tokens.
_ENVIRONMENT_GROUP = "powerplatform:index:EnvironmentGroup"
_DLP_POLICY = "powerplatform:index:DlpPolicy"
_BILLING_POLICY = "powerplatform:index:BillingPolicy"
_MANAGED_ENVIRONMENT = "powerplatform:index:ManagedEnvironment"
_ENVIRONMENT_BACKUP = "powerplatform:index:EnvironmentBackup"
_ROLE_ASSIGNMENT = "powerplatform:index:RoleAssignment"
_ISV_CONTRACT = "powerplatform:index:IsvContract"

# Function tokens.
_GET_ENVIRONMENTS = "powerplatform:index:getEnvironments"
_GET_CONNECTORS = "powerplatform:index:getConnectors"
_GET_APPS = "powerplatform:index:getApps"
_GET_FLOWS = "powerplatform:index:getFlows"

# Locate the schema file relative to this module (repo root / schema.json).
_SCHEMA_PATH = str(Path(__file__).resolve().parents[2] / "schema.json")


def _load_schema() -> str:
    """Read the Pulumi Package Schema JSON file once."""
    # Try the path relative to the provider package first, then fall back to
    # the repository root (useful during development).
    for candidate in [_SCHEMA_PATH, os.path.join(os.getcwd(), "schema.json")]:
        if os.path.isfile(candidate):
            with open(candidate, encoding="utf-8") as f:
                return f.read()
    raise FileNotFoundError("schema.json not found. Ensure it is present alongside the provider package.")


class PowerPlatformProvider(Provider):
    """Pulumi custom provider for Microsoft Power Platform.

    Uses the ``powerplatform-management`` SDK for API interactions and falls back
    to raw REST calls for operations not exposed by the SDK.
    """

    _client: Optional[PowerPlatformClient] = None

    # Lazy-loaded resource/function handlers (created after configure).
    _env_group: Optional[EnvironmentGroupResource] = None
    _dlp_policy: Optional[DlpPolicyResource] = None
    _billing_policy: Optional[BillingPolicyResource] = None
    _managed_env: Optional[ManagedEnvironmentResource] = None
    _env_backup: Optional[EnvironmentBackupResource] = None
    _role_assignment: Optional[RoleAssignmentResource] = None
    _isv_contract: Optional[IsvContractResource] = None
    _get_envs: Optional[GetEnvironmentsFunction] = None
    _get_connectors: Optional[GetConnectorsFunction] = None
    _get_apps: Optional[GetAppsFunction] = None
    _get_flows: Optional[GetFlowsFunction] = None

    # ---- Schema ----

    async def get_schema(self, request: GetSchemaRequest) -> GetSchemaResponse:
        return GetSchemaResponse(schema=_load_schema())

    # ---- Configuration ----

    async def configure(self, request: ConfigureRequest) -> ConfigureResponse:
        self._client = resolve_client(request.args)

        # Initialize resource/function handlers with the configured client.
        self._env_group = EnvironmentGroupResource(self._client)
        self._dlp_policy = DlpPolicyResource(self._client)
        self._billing_policy = BillingPolicyResource(self._client)
        self._managed_env = ManagedEnvironmentResource(self._client)
        self._env_backup = EnvironmentBackupResource(self._client)
        self._role_assignment = RoleAssignmentResource(self._client)
        self._isv_contract = IsvContractResource(self._client)
        self._get_envs = GetEnvironmentsFunction(self._client)
        self._get_connectors = GetConnectorsFunction(self._client)
        self._get_apps = GetAppsFunction(self._client)
        self._get_flows = GetFlowsFunction(self._client)

        return ConfigureResponse(
            accept_secrets=True,
            supports_preview=True,
            accept_resources=True,
            accept_outputs=True,
        )

    # ---- Check ----

    async def check(self, request: CheckRequest) -> CheckResponse:
        handler = self._handler_for_type(request.type)
        if handler and hasattr(handler, "check"):
            return await handler.check(request)
        return CheckResponse(inputs=request.new_inputs)

    # ---- Diff ----

    async def diff(self, request: DiffRequest) -> DiffResponse:
        handler = self._handler_for_type(request.type)
        if handler and hasattr(handler, "diff"):
            return await handler.diff(request)
        return DiffResponse()

    # ---- Create ----

    async def create(self, request: CreateRequest) -> CreateResponse:
        handler = self._handler_for_type(request.type)
        if handler is None:
            raise NotImplementedError(f"Create not implemented for resource type: {request.type}")
        return await handler.create(request)

    # ---- Read ----

    async def read(self, request: ReadRequest) -> ReadResponse:
        handler = self._handler_for_type(request.type)
        if handler is None:
            return ReadResponse(
                resource_id=request.resource_id,
                properties=request.properties,
                inputs=request.inputs,
            )
        return await handler.read(request)

    # ---- Update ----

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        handler = self._handler_for_type(request.type)
        if handler is None:
            raise NotImplementedError(f"Update not implemented for resource type: {request.type}")
        return await handler.update(request)

    # ---- Delete ----

    async def delete(self, request: DeleteRequest) -> None:
        handler = self._handler_for_type(request.type)
        if handler is None:
            raise NotImplementedError(f"Delete not implemented for resource type: {request.type}")
        return await handler.delete(request)

    # ---- Invoke (functions / data sources) ----

    async def invoke(self, request: InvokeRequest) -> InvokeResponse:
        if request.tok == _GET_ENVIRONMENTS and self._get_envs:
            return await self._get_envs.invoke(request)
        if request.tok == _GET_CONNECTORS and self._get_connectors:
            return await self._get_connectors.invoke(request)
        if request.tok == _GET_APPS and self._get_apps:
            return await self._get_apps.invoke(request)
        if request.tok == _GET_FLOWS and self._get_flows:
            return await self._get_flows.invoke(request)
        raise NotImplementedError(f"Unknown function: {request.tok}")

    # ---- Internal helpers ----

    def _handler_for_type(self, resource_type: str):
        """Return the appropriate resource handler for the given type token."""
        handlers = {
            _ENVIRONMENT_GROUP: self._env_group,
            _DLP_POLICY: self._dlp_policy,
            _BILLING_POLICY: self._billing_policy,
            _MANAGED_ENVIRONMENT: self._managed_env,
            _ENVIRONMENT_BACKUP: self._env_backup,
            _ROLE_ASSIGNMENT: self._role_assignment,
            _ISV_CONTRACT: self._isv_contract,
        }
        return handlers.get(resource_type)
