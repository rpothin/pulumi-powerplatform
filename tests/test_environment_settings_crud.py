"""Tests for EnvironmentSettings resource handler — check, diff, and CRUD with mocked RawApiClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    CreateRequest,
    DeleteRequest,
    DiffRequest,
    PropertyDiffKind,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.environment_settings import EnvironmentSettingsResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:EnvironmentSettings::my-settings"
_ENV_ID = "env-aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


def _fake_settings_response() -> dict:
    """Return a fake API settings response."""
    return {
        "maxUploadFileSize": 52428800,
        "pluginTraceLogSetting": "Exception",
        "isAuditEnabled": True,
        "isUserAccessAuditEnabled": True,
        "isActivityLoggingEnabled": False,
    }


def _mock_client() -> MagicMock:
    """Build a MagicMock that mimics PowerPlatformClient with raw_pp API client."""
    client = MagicMock(spec=PowerPlatformClient)
    raw_pp_mock = MagicMock()
    raw_pp_mock.request = AsyncMock()
    type(client).raw_pp = PropertyMock(return_value=raw_pp_mock)
    return client


@pytest.fixture
def mock_client():
    return _mock_client()


@pytest.fixture
def handler(mock_client):
    return EnvironmentSettingsResource(client=mock_client)


class TestEnvironmentSettingsCheck:
    """Tests for the check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self):
        handler = EnvironmentSettingsResource(client=None)  # type: ignore[arg-type]
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("true"),
            },
        )
        response = await handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_missing_environment_id(self):
        handler = EnvironmentSettingsResource(client=None)  # type: ignore[arg-type]
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "isAuditEnabled": PropertyValue("true"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)


class TestEnvironmentSettingsDiff:
    """Tests for the diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self):
        handler = EnvironmentSettingsResource(client=None)  # type: ignore[arg-type]
        state = {
            "environmentId": PropertyValue(_ENV_ID),
            "isAuditEnabled": PropertyValue("true"),
        }
        request = DiffRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            old_state=state,
            new_inputs=dict(state),
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False

    @pytest.mark.asyncio
    async def test_diff_environment_id_triggers_replace(self):
        handler = EnvironmentSettingsResource(client=None)  # type: ignore[arg-type]
        request = DiffRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            old_state={"environmentId": PropertyValue(_ENV_ID)},
            new_inputs={"environmentId": PropertyValue("different-env-id")},
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_settings_are_update(self):
        handler = EnvironmentSettingsResource(client=None)  # type: ignore[arg-type]
        request = DiffRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("false"),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("true"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "isAuditEnabled" in response.diffs
        assert response.detailed_diff["isAuditEnabled"].kind == PropertyDiffKind.UPDATE


class TestEnvironmentSettingsCreate:
    """Tests for the create method."""

    @pytest.mark.asyncio
    async def test_create_applies_settings_and_returns_outputs(self, handler, mock_client):
        # First call: PATCH settings. Second call: GET settings.
        mock_client.raw_pp.request.side_effect = [None, _fake_settings_response()]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("true"),
                "maxUploadFileSize": PropertyValue("52428800"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _ENV_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["maxUploadFileSize"].value == "52428800"
        assert response.properties["isAuditEnabled"].value == "true"

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("true"),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)

        assert response.resource_id == "preview-id"
        mock_client.raw_pp.request.assert_not_awaited()


class TestEnvironmentSettingsRead:
    """Tests for the read method."""

    @pytest.mark.asyncio
    async def test_read_existing_returns_settings(self, handler, mock_client):
        mock_client.raw_pp.request.return_value = _fake_settings_response()

        request = ReadRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _ENV_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["maxUploadFileSize"].value == "52428800"
        assert response.properties["isAuditEnabled"].value == "true"
        assert response.properties["isActivityLoggingEnabled"].value == "false"
        assert "environmentId" in response.inputs

    @pytest.mark.asyncio
    async def test_read_missing_returns_empty(self, handler, mock_client):
        mock_client.raw_pp.request.side_effect = HttpError(404, "not found")

        request = ReadRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == ""
        assert response.properties == {}


class TestEnvironmentSettingsUpdate:
    """Tests for the update method."""

    @pytest.mark.asyncio
    async def test_update_patches_and_returns_settings(self, handler, mock_client):
        updated_settings = _fake_settings_response()
        updated_settings["isAuditEnabled"] = False
        # First call: PATCH. Second call: GET.
        mock_client.raw_pp.request.side_effect = [None, updated_settings]

        request = UpdateRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            olds={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("true"),
            },
            news={
                "environmentId": PropertyValue(_ENV_ID),
                "isAuditEnabled": PropertyValue("false"),
            },
            timeout=300,
            preview=False,
            ignore_changes=[],
        )
        response = await handler.update(request)

        assert response.properties["isAuditEnabled"].value == "false"


class TestEnvironmentSettingsDelete:
    """Tests for the delete method."""

    @pytest.mark.asyncio
    async def test_delete_is_noop_with_warning(self, handler, mock_client):
        request = DeleteRequest(
            urn=_URN,
            resource_id=_ENV_ID,
            properties={},
            timeout=300,
        )
        with patch("rpothin_powerplatform.resources.environment_settings.pulumi") as mock_pulumi:
            await handler.delete(request)
            mock_pulumi.warn.assert_called_once()
            warn_msg = mock_pulumi.warn.call_args[0][0]
            assert _ENV_ID in warn_msg
            assert "cannot be deleted" in warn_msg

        # Should NOT call the API — it's a no-op
        mock_client.raw_pp.request.assert_not_awaited()
