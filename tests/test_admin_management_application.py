"""Tests for AdminManagementApplication resource handler — check and diff behavior."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import CheckRequest, DiffRequest, PropertyDiffKind
from rpothin_powerplatform.resources.admin_management_application import AdminManagementApplicationResource

_URN = "urn:pulumi:test::test::powerplatform:index:AdminManagementApplication::my-app"
_APP_ID = "12345678-1234-1234-1234-123456789012"
_APP_ID_2 = "87654321-4321-4321-4321-210987654321"


@pytest.fixture
def handler():
    return AdminManagementApplicationResource(client=None)  # type: ignore[arg-type]


class TestAdminManagementApplicationCheck:
    @pytest.mark.asyncio
    async def test_check_accepts_valid_application_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue(_APP_ID)},
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["applicationId"].value == _APP_ID

    @pytest.mark.asyncio
    async def test_check_normalizes_uppercase_uuid_to_lowercase(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue(_APP_ID.upper())},
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["applicationId"].value == _APP_ID.lower()

    @pytest.mark.asyncio
    async def test_check_rejects_missing_application_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert len(response.failures) == 1
        assert response.failures[0].property == "applicationId"

    @pytest.mark.asyncio
    async def test_check_rejects_empty_application_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue("")},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert response.failures[0].property == "applicationId"

    @pytest.mark.asyncio
    async def test_check_rejects_non_uuid_application_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue("not-a-guid")},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert response.failures[0].property == "applicationId"
        assert "UUID" in response.failures[0].reason or "GUID" in response.failures[0].reason

    @pytest.mark.asyncio
    async def test_check_rejects_null_application_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"applicationId": PropertyValue(None)},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert response.failures[0].property == "applicationId"


class TestAdminManagementApplicationDiff:
    @pytest.mark.asyncio
    async def test_diff_same_application_id_no_changes(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_APP_ID,
            old_state={"applicationId": PropertyValue(_APP_ID)},
            new_inputs={"applicationId": PropertyValue(_APP_ID)},
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_different_application_id_requires_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_APP_ID,
            old_state={"applicationId": PropertyValue(_APP_ID)},
            new_inputs={"applicationId": PropertyValue(_APP_ID_2)},
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "applicationId" in response.diffs
        assert response.replaces is not None
        assert "applicationId" in response.replaces
        assert response.detailed_diff is not None
        assert response.detailed_diff["applicationId"].kind == PropertyDiffKind.UPDATE_REPLACE
