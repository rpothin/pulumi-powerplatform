"""Tests for the Power Platform provider — schema, check, and diff operations."""

from __future__ import annotations

import json

import pytest
from pulumi.provider.experimental.provider import (
    GetSchemaRequest,
)
from rpothin_powerplatform.provider import PowerPlatformProvider


@pytest.fixture
def provider():
    """Create a provider instance for testing (not configured with live credentials)."""
    return PowerPlatformProvider()


class TestSchema:
    """Tests for the provider schema."""

    @pytest.mark.asyncio
    async def test_get_schema_returns_valid_json(self, provider):
        """get_schema should return a valid JSON string matching schema.json."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        assert response.schema is not None
        schema = json.loads(response.schema)
        assert schema["name"] == "powerplatform"
        assert schema["version"] == "0.1.0"

    @pytest.mark.asyncio
    async def test_schema_contains_environment_group(self, provider):
        """Schema should define the EnvironmentGroup resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:EnvironmentGroup" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_dlp_policy(self, provider):
        """Schema should define the DlpPolicy resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:DlpPolicy" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_get_environments(self, provider):
        """Schema should define the getEnvironments function."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:getEnvironments" in schema["functions"]

    @pytest.mark.asyncio
    async def test_schema_contains_billing_policy(self, provider):
        """Schema should define the BillingPolicy resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:BillingPolicy" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_managed_environment(self, provider):
        """Schema should define the ManagedEnvironment resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:ManagedEnvironment" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_environment_backup(self, provider):
        """Schema should define the EnvironmentBackup resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:EnvironmentBackup" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_role_assignment(self, provider):
        """Schema should define the RoleAssignment resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:RoleAssignment" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_isv_contract(self, provider):
        """Schema should define the IsvContract resource."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:IsvContract" in schema["resources"]

    @pytest.mark.asyncio
    async def test_schema_contains_get_connectors(self, provider):
        """Schema should define the getConnectors function."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:getConnectors" in schema["functions"]

    @pytest.mark.asyncio
    async def test_schema_contains_get_apps(self, provider):
        """Schema should define the getApps function."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:getApps" in schema["functions"]

    @pytest.mark.asyncio
    async def test_schema_contains_get_flows(self, provider):
        """Schema should define the getFlows function."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        assert "powerplatform:index:getFlows" in schema["functions"]

    @pytest.mark.asyncio
    async def test_schema_config_has_credentials(self, provider):
        """Schema should define tenantId, clientId, clientSecret config vars."""
        response = await provider.get_schema(GetSchemaRequest(version=0))
        schema = json.loads(response.schema)
        config_vars = schema["config"]["variables"]
        assert "tenantId" in config_vars
        assert "clientId" in config_vars
        assert "clientSecret" in config_vars
        assert config_vars["clientSecret"].get("secret") is True
