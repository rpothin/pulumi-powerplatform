"""Tests for Environment resource handler — create, read, update, delete with mocked RawApiClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
    UpdateRequest,
)
from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.resources.environment import EnvironmentResource
from pulumi_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:Environment::my-env"
_FAKE_ID = "env-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _fake_env_response(
    *,
    display_name: str = "Test Env",
    description: str = "Test description",
    location: str = "unitedstates",
    env_sku: str = "Sandbox",
    provisioning_state: str = "Succeeded",
) -> dict:
    """Return a fake BAP API environment response."""
    return {
        "name": _FAKE_ID,
        "location": location,
        "properties": {
            "displayName": display_name,
            "description": description,
            "environmentSku": env_sku,
            "linkedEnvironmentMetadata": {
                "domainName": "testenv",
                "instanceUrl": "https://testenv.crm.dynamics.com",
                "currency": {"code": "USD"},
                "baseLanguage": 1033,
            },
            "states": {"runtime": {"runtimeReasonCode": "Ready"}},
            "provisioningState": provisioning_state,
            "createdTime": "2025-01-01T00:00:00Z",
            "lastModifiedTime": "2025-01-02T00:00:00Z",
        },
    }


def _mock_client() -> MagicMock:
    """Build a MagicMock that mimics PowerPlatformClient with a raw API client."""
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
    return EnvironmentResource(client=mock_client)


class TestEnvironmentCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_with_polling(self, handler, mock_client):
        """Create simulates the 202 async pattern: POST → poll → final GET."""
        # POST returns an async-provisioning response
        async_response = _fake_env_response(provisioning_state="Running")
        # Polling GET returns Succeeded
        poll_response = _fake_env_response(provisioning_state="Succeeded")
        # Final GET returns full env
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [async_response, poll_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "description": PropertyValue("Test description"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "domainName": PropertyValue("testenv"),
                "currencyCode": PropertyValue("USD"),
                "languageCode": PropertyValue("1033"),
            },
            timeout=300,
            preview=False,
        )
        with patch("pulumi_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        assert response.properties["location"].value == "unitedstates"
        assert response.properties["environmentType"].value == "Sandbox"
        assert response.properties["domainName"].value == "testenv"
        assert response.properties["currencyCode"].value == "USD"
        assert response.properties["languageCode"].value == "1033"
        assert response.properties["state"].value == "Ready"
        # 3 calls: POST, poll GET, final GET
        assert mock_client.raw.request.await_count == 3

    @pytest.mark.asyncio
    async def test_create_already_succeeded(self, handler, mock_client):
        """When POST immediately returns Succeeded, skip polling and do final GET."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [post_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "description": PropertyValue("Test description"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "domainName": PropertyValue("testenv"),
                "currencyCode": PropertyValue("USD"),
                "languageCode": PropertyValue("1033"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        # 2 calls: POST + final GET
        assert mock_client.raw.request.await_count == 2

    @pytest.mark.asyncio
    async def test_create_polling_failure_raises(self, handler, mock_client):
        """When the poll returns 'Failed', create should raise."""
        async_response = _fake_env_response(provisioning_state="Running")
        failed_response = _fake_env_response(provisioning_state="Failed")

        mock_client.raw.request.side_effect = [async_response, failed_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            preview=False,
        )
        with patch("pulumi_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="non-successful terminal state"):
                await handler.create(request)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("canceled_state", ["Canceled", "Cancelled"])
    async def test_create_polling_canceled_raises(self, handler, mock_client, canceled_state):
        """When the poll returns 'Canceled' or 'Cancelled', create should raise."""
        async_response = _fake_env_response(provisioning_state="Running")
        canceled_response = _fake_env_response(provisioning_state=canceled_state)

        mock_client.raw.request.side_effect = [async_response, canceled_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            preview=False,
        )
        with patch("pulumi_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="non-successful terminal state"):
                await handler.create(request)

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_minimal_properties(self, handler, mock_client):
        """Create with only required properties."""
        post_response = {
            "name": _FAKE_ID,
            "location": "unitedstates",
            "properties": {
                "displayName": "Minimal",
                "environmentSku": "Sandbox",
                "provisioningState": "Succeeded",
            },
        }
        final_response = {
            "name": _FAKE_ID,
            "location": "unitedstates",
            "properties": {
                "displayName": "Minimal",
                "environmentSku": "Sandbox",
                "provisioningState": "Succeeded",
            },
        }

        mock_client.raw.request.side_effect = [post_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Minimal"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Minimal"


class TestEnvironmentRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_properties(self, handler, mock_client):
        mock_client.raw.request.return_value = _fake_env_response()

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        assert response.properties["location"].value == "unitedstates"
        assert "displayName" in response.inputs
        assert "location" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = ReadRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestEnvironmentUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_returns_updated_properties(self, handler, mock_client):
        mock_client.raw.request.return_value = _fake_env_response(display_name="Updated")

        request = UpdateRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            olds={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            news={
                "displayName": PropertyValue("Updated"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)

        assert response.properties["displayName"].value == "Updated"
        mock_client.raw.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_preview_returns_news(self, handler, mock_client):
        request = UpdateRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            olds={},
            news={
                "displayName": PropertyValue("Updated"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            timeout=300,
            ignore_changes=[],
            preview=True,
        )
        response = await handler.update(request)

        assert response.properties["displayName"].value == "Updated"
        mock_client.raw.request.assert_not_awaited()


class TestEnvironmentDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_calls_api(self, handler, mock_client):
        mock_client.raw.request.return_value = None

        request = DeleteRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            properties={},
            timeout=300,
        )
        await handler.delete(request)

        mock_client.raw.request.assert_awaited_once()
        call_args = mock_client.raw.request.call_args
        assert call_args[0][0] == "DELETE"
        assert _FAKE_ID in call_args[0][1]
