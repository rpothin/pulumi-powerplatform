"""Tests for the getSecurityRoles function handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_security_roles import GetSecurityRolesFunction

_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_BUSINESS_UNIT_ID = "bbbbbbbb-2222-3333-4444-cccccccccccc"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"
_ENV_RESPONSE = {
    "properties": {
        "linkedEnvironmentMetadata": {"instanceUrl": _INSTANCE_URL}
    }
}


def _make_mock_client() -> MagicMock:
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    client.raw = raw_mock
    client.credential = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _make_mock_client()


@pytest.fixture
def dv_mock():
    dv = MagicMock()
    dv.request = AsyncMock()
    return dv


@pytest.fixture
def handler(mock_client, dv_mock):
    func = GetSecurityRolesFunction(client=mock_client)
    func._make_dataverse_client = MagicMock(return_value=dv_mock)
    return func


class TestGetSecurityRolesInvoke:
    @pytest.mark.asyncio
    async def test_invoke_returns_security_roles(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [
                {
                    "roleid": "role-1",
                    "name": "Deployment Pipeline User",
                    "_businessunitid_value": _BUSINESS_UNIT_ID,
                }
            ]
        }

        response = await handler.invoke(
            InvokeRequest(
                tok="powerplatform:index:getSecurityRoles",
                args={"environmentId": PropertyValue(_ENV_ID)},
            )
        )

        roles = response.return_value["securityRoles"].value
        assert len(roles) == 1
        assert roles[0].value["roleId"].value == "role-1"
        assert roles[0].value["name"].value == "Deployment Pipeline User"
        assert roles[0].value["businessUnitId"].value == _BUSINESS_UNIT_ID
        dv_mock.request.assert_awaited_once_with(
            "GET",
            "/api/data/v9.2/roles?$select=roleid,name,_businessunitid_value",
            api_version=None,
        )

    @pytest.mark.asyncio
    async def test_invoke_applies_optional_business_unit_filter(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        await handler.invoke(
            InvokeRequest(
                tok="powerplatform:index:getSecurityRoles",
                args={
                    "environmentId": PropertyValue(_ENV_ID),
                    "businessUnitId": PropertyValue(_BUSINESS_UNIT_ID),
                },
            )
        )

        dv_mock.request.assert_awaited_once_with(
            "GET",
            "/api/data/v9.2/roles?$select=roleid,name,_businessunitid_value"
            f"&$filter=_businessunitid_value eq '{_BUSINESS_UNIT_ID}'",
            api_version=None,
        )

    @pytest.mark.asyncio
    async def test_invoke_requires_environment_id(self, handler):
        with pytest.raises(ValueError, match="environmentId is required"):
            await handler.invoke(
                InvokeRequest(
                    tok="powerplatform:index:getSecurityRoles",
                    args={},
                )
            )

    @pytest.mark.asyncio
    async def test_invoke_raises_when_dataverse_url_missing(self, handler, mock_client):
        mock_client.raw.request.return_value = {
            "properties": {"linkedEnvironmentMetadata": {"instanceUrl": ""}}
        }

        with pytest.raises(RuntimeError, match="has no Dataverse instance"):
            await handler.invoke(
                InvokeRequest(
                    tok="powerplatform:index:getSecurityRoles",
                    args={"environmentId": PropertyValue(_ENV_ID)},
                )
            )
