"""Tests for AdminManagementApplication resource handler — create, read, delete."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.admin_management_application import AdminManagementApplicationResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:AdminManagementApplication::my-app"
_APP_ID = "12345678-1234-1234-1234-123456789012"


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
    return AdminManagementApplicationResource(client=mock_client)


class TestAdminManagementApplicationCreate:
    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)
        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_posts_to_admin_applications_endpoint(self, handler, mock_client):
        mock_client.raw.request.return_value = {"applicationId": _APP_ID.upper()}

        request = CreateRequest(
            urn=_URN,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _APP_ID.lower()
        assert response.properties["applicationId"].value == _APP_ID.lower()

        call_args = mock_client.raw.request.call_args
        assert call_args[0][0] == "POST"
        assert _APP_ID in call_args[0][1]
        assert call_args[1]["api_version"] == "2022-03-01-preview"

    @pytest.mark.asyncio
    async def test_create_uses_input_id_when_response_is_empty(self, handler, mock_client):
        mock_client.raw.request.return_value = None

        request = CreateRequest(
            urn=_URN,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _APP_ID
        assert response.properties["applicationId"].value == _APP_ID

    @pytest.mark.asyncio
    async def test_create_uses_input_id_when_response_has_no_uuid(self, handler, mock_client):
        mock_client.raw.request.return_value = {"status": "Registered"}

        request = CreateRequest(
            urn=_URN,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _APP_ID


class TestAdminManagementApplicationRead:
    @pytest.mark.asyncio
    async def test_read_404_returns_empty(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = ReadRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}
        assert response.inputs == {}

    @pytest.mark.asyncio
    async def test_read_returns_application_id_from_response(self, handler, mock_client):
        mock_client.raw.request.return_value = {"applicationId": _APP_ID, "applicationName": "My App"}

        request = ReadRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == _APP_ID
        assert response.properties["applicationId"].value == _APP_ID
        assert response.inputs["applicationId"].value == _APP_ID

    @pytest.mark.asyncio
    async def test_read_falls_back_to_resource_id_when_response_has_no_uuid(self, handler, mock_client):
        mock_client.raw.request.return_value = {"status": "Registered"}

        request = ReadRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == _APP_ID
        assert response.properties["applicationId"].value == _APP_ID

    @pytest.mark.asyncio
    async def test_read_reraises_non_404_errors(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(500, "server error")

        request = ReadRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={},
            inputs={},
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.read(request)
        assert exc_info.value.status_code == 500


class TestAdminManagementApplicationDelete:
    @pytest.mark.asyncio
    async def test_delete_calls_delete_endpoint(self, handler, mock_client):
        mock_client.raw.request.return_value = None

        request = DeleteRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
        )
        await handler.delete(request)

        call_args = mock_client.raw.request.call_args
        assert call_args[0][0] == "DELETE"
        assert _APP_ID in call_args[0][1]
        assert call_args[1]["api_version"] == "2022-03-01-preview"

    @pytest.mark.asyncio
    async def test_delete_ignores_404(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
        )
        # Should not raise
        await handler.delete(request)

    @pytest.mark.asyncio
    async def test_delete_reraises_non_404_errors(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(403, "forbidden")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_APP_ID,
            properties={"applicationId": PropertyValue(_APP_ID)},
            timeout=300,
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.delete(request)
        assert exc_info.value.status_code == 403
