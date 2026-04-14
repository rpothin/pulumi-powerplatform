"""Tests for IsvContract resource handler — create, read, update, delete with mocked SDK."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.isv_contract import IsvContractResource

_URN = "urn:pulumi:test::test::powerplatform:index:IsvContract::my-contract"
_FAKE_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
_FAKE_TIME = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _fake_contract(*, name: str = "Test ISV", geo: str = "unitedstates"):
    """Return a fake IsvContractResponseModel-like SDK object."""
    contract = MagicMock()
    contract.id = _FAKE_ID
    contract.name = name
    contract.geo = geo
    contract.status = MagicMock(value="Enabled")
    contract.created_on = _FAKE_TIME
    contract.last_modified_on = _FAKE_TIME
    return contract


def _mock_client():
    """Build a MagicMock that mimics the SDK call chain for ISV contracts."""
    client = MagicMock(spec=PowerPlatformClient)
    client.sdk.licensing.isv_contracts = MagicMock()
    client.sdk.licensing.isv_contracts.post = AsyncMock()
    client.sdk.licensing.isv_contracts.by_isv_contract_id = MagicMock()
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return IsvContractResource(client=mock_client)


class TestIsvContractCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_returns_id_and_properties(self, handler, mock_client):
        mock_client.sdk.licensing.isv_contracts.post.return_value = _fake_contract()

        request = CreateRequest(
            urn=_URN,
            properties={
                "name": PropertyValue("Test ISV"),
                "geo": PropertyValue("unitedstates"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["name"].value == "Test ISV"
        assert response.properties["geo"].value == "unitedstates"
        mock_client.sdk.licensing.isv_contracts.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "name": PropertyValue("Test ISV"),
                "geo": PropertyValue("unitedstates"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.sdk.licensing.isv_contracts.post.assert_not_awaited()


class TestIsvContractRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.isv_contracts.by_isv_contract_id.return_value
        by_id.get = AsyncMock(return_value=_fake_contract())

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == str(_FAKE_ID)
        assert response.properties["name"].value == "Test ISV"
        assert response.properties["geo"].value == "unitedstates"
        assert "name" in response.inputs
        assert "geo" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.isv_contracts.by_isv_contract_id.return_value
        by_id.get = AsyncMock(return_value=None)

        request = ReadRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestIsvContractUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_returns_updated_properties(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.isv_contracts.by_isv_contract_id.return_value
        by_id.put = AsyncMock(return_value=_fake_contract(name="Updated ISV"))

        request = UpdateRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            olds={"name": PropertyValue("Test ISV"), "geo": PropertyValue("unitedstates")},
            news={"name": PropertyValue("Updated ISV"), "geo": PropertyValue("unitedstates")},
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)

        assert response.properties["name"].value == "Updated ISV"
        by_id.put.assert_awaited_once()


class TestIsvContractDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_sdk(self, handler, mock_client):
        by_id = mock_client.sdk.licensing.isv_contracts.by_isv_contract_id.return_value
        by_id.delete = AsyncMock(return_value=None)

        request = DeleteRequest(
            urn=_URN,
            resource_id=str(_FAKE_ID),
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        by_id.delete.assert_awaited_once()
