"""Tests for EnvironmentApplicationAdmin resource handler — check and diff behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import CheckRequest, DiffRequest, PropertyDiffKind
from rpothin_powerplatform.resources.environment_application_admin import (
    EnvironmentApplicationAdminResource,
)

_URN = "urn:pulumi:test::test::powerplatform:index:EnvironmentApplicationAdmin::my-admin"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_APP_ID = "cccccccc-4444-5555-6666-dddddddddddd"
_ENV_ID_2 = "eeeeeeee-7777-8888-9999-ffffffffffff"
_APP_ID_2 = "11111111-aaaa-bbbb-cccc-222222222222"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"


@pytest.fixture
def handler_no_client():
    """Handler without a live client — skips Dataverse validation in check()."""
    return EnvironmentApplicationAdminResource(client=None)  # type: ignore[arg-type]


@pytest.fixture
def handler_with_client():
    """Handler with a mocked client — enables Dataverse validation in check()."""
    client = MagicMock()
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    client.raw = raw_mock
    return EnvironmentApplicationAdminResource(client=client)


class TestEnvironmentApplicationAdminCheck:
    @pytest.mark.asyncio
    async def test_check_accepts_valid_inputs(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()
        assert response.inputs["applicationId"].value == _APP_ID.lower()

    @pytest.mark.asyncio
    async def test_check_normalizes_guids_to_lowercase(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID.upper()),
                "applicationId": PropertyValue(_APP_ID.upper()),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()
        assert response.inputs["applicationId"].value == _APP_ID.lower()

    @pytest.mark.asyncio
    async def test_check_rejects_missing_environment_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue(_APP_ID)},
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_empty_environment_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(""),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_invalid_environment_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("not-a-guid"),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_missing_application_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "applicationId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_empty_application_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(""),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "applicationId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_invalid_application_id(self, handler_no_client):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue("not-a-guid"),
            },
        )
        response = await handler_no_client.check(request)
        assert response.failures is not None
        assert any(f.property == "applicationId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_reports_failure_when_no_dataverse_instance(self, handler_with_client):
        """When the environment has no Dataverse, check() reports an environmentId failure."""
        env_response = {"properties": {"linkedEnvironmentMetadata": {"instanceUrl": ""}}}
        handler_with_client._client.raw.request.return_value = env_response

        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_with_client.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)
        assert any("Dataverse" in f.reason for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_skips_dataverse_check_when_api_errors(self, handler_with_client):
        """When the BAP API errors during check(), validation is skipped (no failure added)."""
        from rpothin_powerplatform.utils import HttpError

        handler_with_client._client.raw.request.side_effect = HttpError(503, "service unavailable")

        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_with_client.check(request)
        # Format checks pass; Dataverse check should be silently skipped.
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_accepts_valid_inputs_with_dataverse_present(self, handler_with_client):
        """check() passes when environment has a valid Dataverse instanceUrl."""
        env_response = {
            "properties": {
                "linkedEnvironmentMetadata": {"instanceUrl": _INSTANCE_URL}
            }
        }
        handler_with_client._client.raw.request.return_value = env_response

        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
        )
        response = await handler_with_client.check(request)
        assert response.failures is None


class TestEnvironmentApplicationAdminDiff:
    @pytest.mark.asyncio
    async def test_diff_same_inputs_no_changes(self, handler_no_client):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}/{_APP_ID}",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
                "systemUserId": PropertyValue("sys-user-id"),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            ignore_changes=[],
        )
        response = await handler_no_client.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_environment_id_changed_requires_replace(self, handler_no_client):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}/{_APP_ID}",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID_2),
                "applicationId": PropertyValue(_APP_ID),
            },
            ignore_changes=[],
        )
        response = await handler_no_client.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert "environmentId" in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_application_id_changed_requires_replace(self, handler_no_client):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}/{_APP_ID}",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID_2),
            },
            ignore_changes=[],
        )
        response = await handler_no_client.diff(request)
        assert response.changes is True
        assert "applicationId" in response.diffs
        assert "applicationId" in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["applicationId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_both_changed_requires_replace(self, handler_no_client):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}/{_APP_ID}",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "applicationId": PropertyValue(_APP_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID_2),
                "applicationId": PropertyValue(_APP_ID_2),
            },
            ignore_changes=[],
        )
        response = await handler_no_client.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert "applicationId" in response.diffs
        assert len(response.diffs) == 2
        assert response.detailed_diff is not None
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE
        assert response.detailed_diff["applicationId"].kind == PropertyDiffKind.UPDATE_REPLACE
