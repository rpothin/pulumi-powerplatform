"""Tests for TenantSettings resource handler — create, read, update, delete."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.tenant_settings import TenantSettingsResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:TenantSettings::tenant-settings"
_TENANT_ID = "tenant-123"


def _pv_to_python(value):
    if isinstance(value, PropertyValue):
        return _pv_to_python(value.value)
    if isinstance(value, (dict, MappingProxyType)):
        return {k: _pv_to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_pv_to_python(v) for v in value]
    return value


def _mock_client() -> MagicMock:
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    type(client).raw = PropertyMock(return_value=raw_mock)
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return TenantSettingsResource(client=mock_client)


class TestTenantSettingsCreate:
    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={"powerPlatform": PropertyValue({})},
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)
        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_real_fetches_tenant_and_captures_baseline(self, handler, mock_client):
        current_before = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": False,
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        current_after = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": True,
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        mock_client.raw.request.side_effect = [
            {"tenantId": _TENANT_ID},
            {"tenantSettings": current_before},
            None,
            {"tenantSettings": current_after},
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "disableEnvironmentCreationByNonAdminUsers": PropertyValue(True),
                            }
                        )
                    }
                )
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _TENANT_ID
        assert _pv_to_python(response.properties["powerPlatform"]) == {
            "governance": {"disableEnvironmentCreationByNonAdminUsers": True}
        }
        assert _pv_to_python(response.properties["_originalSettings"]) == {
            "powerPlatform": {"governance": {"disableEnvironmentCreationByNonAdminUsers": False}}
        }
        assert mock_client.raw.request.await_count == 4


class TestTenantSettingsRead:
    @pytest.mark.asyncio
    async def test_read_404_returns_empty(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")
        request = ReadRequest(
            urn=_URN,
            resource_id=_TENANT_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}
        assert response.inputs == {}

    @pytest.mark.asyncio
    async def test_read_returns_only_managed_keys(self, handler, mock_client):
        current = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": True,
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        mock_client.raw.request.return_value = {"tenantSettings": current}
        request = ReadRequest(
            urn=_URN,
            resource_id=_TENANT_ID,
            properties={
                "_originalSettings": PropertyValue(
                    {
                        "powerPlatform": PropertyValue(
                            {
                                "governance": PropertyValue(
                                    {
                                        "disableEnvironmentCreationByNonAdminUsers": PropertyValue(False),
                                    }
                                )
                            }
                        )
                    }
                )
            },
            inputs={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "disableEnvironmentCreationByNonAdminUsers": PropertyValue(False),
                            }
                        )
                    }
                ),
            },
        )
        response = await handler.read(request)
        assert response.resource_id == _TENANT_ID
        assert _pv_to_python(response.properties["powerPlatform"]) == {
            "governance": {"disableEnvironmentCreationByNonAdminUsers": True}
        }
        assert _pv_to_python(response.properties["_originalSettings"]) == {
            "powerPlatform": {"governance": {"disableEnvironmentCreationByNonAdminUsers": False}}
        }


class TestTenantSettingsUpdate:
    @pytest.mark.asyncio
    async def test_update_preserves_baseline_and_updates_managed_subset(self, handler, mock_client):
        current_before = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": False,
                    "newManagedFlag": "from-server",
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        current_after = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": True,
                    "newManagedFlag": "from-user",
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        mock_client.raw.request.side_effect = [
            {"tenantSettings": current_before},
            None,
            {"tenantSettings": current_after},
        ]

        request = UpdateRequest(
            urn=_URN,
            resource_id=_TENANT_ID,
            olds={
                "_originalSettings": PropertyValue(
                    {
                        "powerPlatform": PropertyValue(
                            {
                                "governance": PropertyValue(
                                    {
                                        "disableEnvironmentCreationByNonAdminUsers": PropertyValue(False),
                                    }
                                )
                            }
                        )
                    }
                )
            },
            news={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "disableEnvironmentCreationByNonAdminUsers": PropertyValue(True),
                                "newManagedFlag": PropertyValue("from-user"),
                            }
                        )
                    }
                ),
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)
        assert _pv_to_python(response.properties["powerPlatform"]) == {
            "governance": {
                "disableEnvironmentCreationByNonAdminUsers": True,
                "newManagedFlag": "from-user",
            }
        }
        assert _pv_to_python(response.properties["_originalSettings"]) == {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": False,
                    "newManagedFlag": "from-server",
                }
            }
        }

        update_call = mock_client.raw.request.call_args_list[1]
        assert update_call[0][0] == "POST"
        assert update_call[1]["body"]["tenantSettings"]["powerPlatform"]["governance"] == {
            "disableEnvironmentCreationByNonAdminUsers": True,
            "newManagedFlag": "from-user",
            "unmanagedServerFlag": "keep",
        }


class TestTenantSettingsDelete:
    @pytest.mark.asyncio
    async def test_delete_restores_only_managed_keys_from_baseline(self, handler, mock_client):
        current = {
            "powerPlatform": {
                "governance": {
                    "disableEnvironmentCreationByNonAdminUsers": True,
                    "newManagedFlag": "from-user",
                    "unmanagedServerFlag": "keep",
                }
            }
        }
        mock_client.raw.request.side_effect = [{"tenantSettings": current}, None]
        request = DeleteRequest(
            urn=_URN,
            resource_id=_TENANT_ID,
            properties={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "disableEnvironmentCreationByNonAdminUsers": PropertyValue(True),
                                "newManagedFlag": PropertyValue("from-user"),
                            }
                        )
                    }
                ),
                "_originalSettings": PropertyValue(
                    {
                        "powerPlatform": PropertyValue(
                            {
                                "governance": PropertyValue(
                                    {
                                        "disableEnvironmentCreationByNonAdminUsers": PropertyValue(False),
                                    }
                                )
                            }
                        )
                    }
                ),
            },
            timeout=300,
        )
        await handler.delete(request)

        assert mock_client.raw.request.await_count == 2
        update_call = mock_client.raw.request.call_args_list[1]
        assert update_call[1]["body"]["tenantSettings"]["powerPlatform"]["governance"] == {
            "disableEnvironmentCreationByNonAdminUsers": False,
            "newManagedFlag": "from-user",
            "unmanagedServerFlag": "keep",
        }
