"""Tests for EnvironmentApplicationAdmin resource handler — create, read, delete."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.environment_application_admin import (
    EnvironmentApplicationAdminResource,
)
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:EnvironmentApplicationAdmin::my-admin"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_APP_ID = "cccccccc-4444-5555-6666-dddddddddddd"
_SYSTEM_USER_ID = "99999999-ffff-eeee-dddd-cccccccccccc"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"
_RESOURCE_ID = f"{_ENV_ID}/{_APP_ID}"

# BAP response for environment with Dataverse.
_ENV_RESPONSE = {
    "properties": {
        "linkedEnvironmentMetadata": {"instanceUrl": _INSTANCE_URL}
    }
}

# BAP response for environment without Dataverse.
_ENV_RESPONSE_NO_DV = {
    "properties": {}
}

# Dataverse response containing the systemuser record.
_DV_USERS_RESPONSE = {
    "value": [{"systemuserid": _SYSTEM_USER_ID}]
}

# Dataverse response with no systemuser records.
_DV_USERS_EMPTY = {"value": []}


def _make_mock_client() -> MagicMock:
    """Build a MagicMock PowerPlatformClient with async-capable raw.request."""
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    client.raw = raw_mock
    client.credential = MagicMock()
    return client


def _make_handler(mock_client: MagicMock, dv_mock: MagicMock) -> EnvironmentApplicationAdminResource:
    """Build a handler where _make_dataverse_client returns the given dv_mock."""
    handler = EnvironmentApplicationAdminResource(client=mock_client)
    handler._make_dataverse_client = MagicMock(return_value=dv_mock)
    return handler


@pytest.fixture
def mock_client():
    return _make_mock_client()


@pytest.fixture
def dv_mock():
    """Dataverse mock client with async request."""
    dv = MagicMock()
    dv.request = AsyncMock()
    return dv


@pytest.fixture
def handler(mock_client, dv_mock):
    return _make_handler(mock_client, dv_mock)


class TestEnvironmentApplicationAdminCreate:
    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)
        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_calls_add_app_user_endpoint(self, handler, mock_client, dv_mock):
        # BAP: POST addAppUser, then GET environment for instanceUrl.
        mock_client.raw.request.side_effect = [None, _ENV_RESPONSE]
        dv_mock.request.return_value = _DV_USERS_RESPONSE

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _RESOURCE_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["applicationId"].value == _APP_ID
        assert response.properties["systemUserId"].value == _SYSTEM_USER_ID

        # Verify addAppUser call.
        first_call = mock_client.raw.request.call_args_list[0]
        assert first_call[0][0] == "POST"
        assert _ENV_ID in first_call[0][1]
        assert "addAppUser" in first_call[0][1]
        assert first_call[1]["body"] == {"servicePrincipalAppId": _APP_ID}
        assert first_call[1]["api_version"] == "2020-10-01"

    @pytest.mark.asyncio
    async def test_create_resolves_dataverse_url(self, handler, mock_client, dv_mock):
        mock_client.raw.request.side_effect = [None, _ENV_RESPONSE]
        dv_mock.request.return_value = _DV_USERS_RESPONSE

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
            preview=False,
        )
        await handler.create(request)

        handler._make_dataverse_client.assert_called_once_with(_INSTANCE_URL)

    @pytest.mark.asyncio
    async def test_create_raises_when_no_dataverse_instance(self, handler, mock_client):
        mock_client.raw.request.side_effect = [None, _ENV_RESPONSE_NO_DV]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
            preview=False,
        )
        with pytest.raises(RuntimeError, match="Dataverse"):
            await handler.create(request)

    @pytest.mark.asyncio
    async def test_create_raises_when_system_user_not_found(self, handler, mock_client, dv_mock):
        mock_client.raw.request.side_effect = [None, _ENV_RESPONSE]
        dv_mock.request.return_value = _DV_USERS_EMPTY

        with patch("asyncio.sleep", new_callable=AsyncMock):
            request = CreateRequest(
                urn=_URN,
                properties={
                    "environmentId": PropertyValue(_ENV_ID),
                    "applicationId": PropertyValue(_APP_ID),
                },
                timeout=300,
                preview=False,
            )
            with pytest.raises(RuntimeError, match="not found in Dataverse"):
                await handler.create(request)

    @pytest.mark.asyncio
    async def test_create_queries_dataverse_for_system_user_id(self, handler, mock_client, dv_mock):
        mock_client.raw.request.side_effect = [None, _ENV_RESPONSE]
        dv_mock.request.return_value = _DV_USERS_RESPONSE

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        dv_call = dv_mock.request.call_args
        assert dv_call[0][0] == "GET"
        assert "systemusers" in dv_call[0][1]
        assert _APP_ID in dv_call[0][1]
        assert dv_call[1]["api_version"] is None
        assert response.properties["systemUserId"].value == _SYSTEM_USER_ID


class TestEnvironmentApplicationAdminRead:
    @pytest.mark.asyncio
    async def test_read_returns_empty_when_environment_404(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_reraises_non_404_bap_errors(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(500, "server error")

        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.read(request)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_no_dataverse_instance(self, handler, mock_client):
        mock_client.raw.request.return_value = _ENV_RESPONSE_NO_DV

        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_user_not_in_dataverse(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = _DV_USERS_EMPTY

        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}
        # With max_attempts=1, Dataverse should only be queried once.
        assert dv_mock.request.call_count == 1

    @pytest.mark.asyncio
    async def test_read_returns_correct_properties(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = _DV_USERS_RESPONSE

        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _RESOURCE_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["applicationId"].value == _APP_ID
        assert response.properties["systemUserId"].value == _SYSTEM_USER_ID
        assert response.inputs["environmentId"].value == _ENV_ID
        assert response.inputs["applicationId"].value == _APP_ID
        assert "systemUserId" not in response.inputs


class TestEnvironmentApplicationAdminDelete:
    @pytest.mark.asyncio
    async def test_delete_deactivates_and_removes_system_user(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = None

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        await handler.delete(request)

        calls = dv_mock.request.call_args_list
        assert len(calls) == 2

        patch_call = calls[0]
        assert patch_call[0][0] == "PATCH"
        assert _SYSTEM_USER_ID in patch_call[0][1]
        assert "v9.2" in patch_call[0][1]
        assert patch_call[1]["body"] == {"isdisabled": True}
        assert patch_call[1]["api_version"] is None

        delete_call = calls[1]
        assert delete_call[0][0] == "DELETE"
        assert _SYSTEM_USER_ID in delete_call[0][1]
        assert "v9.2" in delete_call[0][1]
        assert delete_call[1]["api_version"] is None

    @pytest.mark.asyncio
    async def test_delete_ignores_404_on_deactivate(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = HttpError(404, "not found")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        # Should not raise.
        await handler.delete(request)

    @pytest.mark.asyncio
    async def test_delete_ignores_404_on_final_delete(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        # PATCH succeeds, DELETE returns 404.
        dv_mock.request.side_effect = [None, HttpError(404, "not found")]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        await handler.delete(request)

    @pytest.mark.asyncio
    async def test_delete_noop_when_environment_404(self, handler, mock_client, dv_mock):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        await handler.delete(request)
        dv_mock.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_noop_when_no_dataverse_instance(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE_NO_DV

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        await handler.delete(request)
        dv_mock.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_looks_up_system_user_when_missing_from_state(
        self, handler, mock_client, dv_mock
    ):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        # First call: lookup by applicationId; then PATCH, then DELETE.
        dv_mock.request.side_effect = [_DV_USERS_RESPONSE, None, None]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                # systemUserId intentionally omitted to test fallback lookup.
            },
            timeout=300,
        )
        await handler.delete(request)

        calls = dv_mock.request.call_args_list
        assert len(calls) == 3
        assert calls[0][0][0] == "GET"
        assert "systemusers" in calls[0][0][1]
        assert calls[1][0][0] == "PATCH"
        assert calls[2][0][0] == "DELETE"

    @pytest.mark.asyncio
    async def test_delete_noop_when_user_not_found_in_dataverse(
        self, handler, mock_client, dv_mock
    ):
        """If no systemUserId in state and Dataverse query returns nothing, skip."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = _DV_USERS_EMPTY

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            timeout=300,
        )
        await handler.delete(request)
        # Only the lookup GET should have been called; no PATCH/DELETE.
        assert dv_mock.request.call_count == 1

    @pytest.mark.asyncio
    async def test_delete_reraises_non_404_deactivate_errors(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = HttpError(403, "forbidden")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue(_SYSTEM_USER_ID),
            },
            timeout=300,
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.delete(request)
        assert exc_info.value.status_code == 403
