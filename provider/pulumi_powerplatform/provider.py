"""Power Platform Pulumi provider — dispatches CRUD and invoke operations to resource/function handlers."""

from __future__ import annotations

import os
from typing import Optional

from pulumi.provider.experimental.property_value import PropertyValue
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
from pulumi_powerplatform.functions.get_environments import GetEnvironmentsFunction
from pulumi_powerplatform.resources.dlp_policy import DlpPolicyResource
from pulumi_powerplatform.resources.environment_group import EnvironmentGroupResource

# Resource type tokens.
_ENVIRONMENT_GROUP = "powerplatform:index:EnvironmentGroup"
_DLP_POLICY = "powerplatform:index:DlpPolicy"

# Function tokens.
_GET_ENVIRONMENTS = "powerplatform:index:getEnvironments"

# Locate the schema file relative to this module.
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "schema.json")


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
    _get_envs: Optional[GetEnvironmentsFunction] = None

    # ---- Schema ----

    async def get_schema(self, request: GetSchemaRequest) -> GetSchemaResponse:
        return GetSchemaResponse(schema=_load_schema())

    # ---- Configuration ----

    async def configure(self, request: ConfigureRequest) -> ConfigureResponse:
        args = request.args

        tenant_id = _extract_str(args.get("tenantId"))
        client_id = _extract_str(args.get("clientId"))
        client_secret = _extract_str(args.get("clientSecret"))

        self._client = PowerPlatformClient(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        # Initialize resource/function handlers with the configured client.
        self._env_group = EnvironmentGroupResource(self._client)
        self._dlp_policy = DlpPolicyResource(self._client)
        self._get_envs = GetEnvironmentsFunction(self._client)

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
        raise NotImplementedError(f"Unknown function: {request.tok}")

    # ---- Internal helpers ----

    def _handler_for_type(self, resource_type: str):
        """Return the appropriate resource handler for the given type token."""
        handlers = {
            _ENVIRONMENT_GROUP: self._env_group,
            _DLP_POLICY: self._dlp_policy,
        }
        return handlers.get(resource_type)


def _extract_str(pv: Optional[PropertyValue]) -> Optional[str]:
    """Safely extract a string from a PropertyValue."""
    if pv is None or pv.value is None:
        return None
    return str(pv.value)
