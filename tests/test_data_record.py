"""Tests for DataRecord resource handler — check and diff behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import CheckRequest, DiffRequest, PropertyDiffKind
from rpothin_powerplatform.resources.data_record import DataRecordResource

_URN = "urn:pulumi:test::test::powerplatform:index:DataRecord::my-record"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_ENV_ID_2 = "bbbbbbbb-2222-3333-4444-cccccccccccc"
_TABLE = "account"
_TABLE_2 = "contact"
_RECORD_ID = "dddddddd-5555-6666-7777-eeeeeeeeeeee"

_SIMPLE_COLS = PropertyValue({"name": PropertyValue("Acme"), "revenue": PropertyValue(1000.0)})


@pytest.fixture
def handler():
    return DataRecordResource(client=None)  # type: ignore[arg-type]


@pytest.fixture
def handler_with_client():
    client = MagicMock()
    return DataRecordResource(client=client)


# ---- check() ---------------------------------------------------------------


class TestDataRecordCheck:
    @pytest.mark.asyncio
    async def test_check_accepts_valid_inputs(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()

    @pytest.mark.asyncio
    async def test_check_normalizes_env_id_to_lowercase(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID.upper()),
                "tableLogicalName": PropertyValue(_TABLE),
            },
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()

    @pytest.mark.asyncio
    async def test_check_rejects_missing_environment_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"tableLogicalName": PropertyValue(_TABLE)},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_empty_environment_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(""),
                "tableLogicalName": PropertyValue(_TABLE),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_invalid_environment_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("not-a-guid"),
                "tableLogicalName": PropertyValue(_TABLE),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_missing_table_logical_name(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "tableLogicalName" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_empty_table_logical_name(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(""),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "tableLogicalName" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_invalid_table_logical_name(self, handler):
        """Table names starting with uppercase are rejected."""
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue("Account"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "tableLogicalName" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_reports_both_failures_simultaneously(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue("bad-id"),
                "tableLogicalName": PropertyValue("BadTable"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        props = [f.property for f in response.failures]
        assert "environmentId" in props
        assert "tableLogicalName" in props

    @pytest.mark.asyncio
    async def test_check_accepts_table_name_with_underscore(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue("custom_table_name"),
            },
        )
        response = await handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_rejects_preexportsteprequired_on_non_root_stage(self, handler):
        """preexportsteprequired=True on a deploymentstage without pipelineid is rejected."""
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue("deploymentstage"),
                "columns": PropertyValue({
                    "preexportsteprequired": PropertyValue(True),
                }),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "columns" for f in response.failures)
        assert any("root stage" in f.reason for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_accepts_preexportsteprequired_on_root_stage(self, handler):
        """preexportsteprequired=True is allowed when pipelineid is present (root stage)."""
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue("deploymentstage"),
                "columns": PropertyValue({
                    "preexportsteprequired": PropertyValue(True),
                    "pipelineid": PropertyValue("dddddddd-5555-6666-7777-eeeeeeeeeeee"),
                }),
            },
        )
        response = await handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_accepts_preexportsteprequired_false_without_pipelineid(self, handler):
        """preexportsteprequired=False is always allowed regardless of pipelineid."""
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue("deploymentstage"),
                "columns": PropertyValue({
                    "preexportsteprequired": PropertyValue(False),
                }),
            },
        )
        response = await handler.check(request)
        assert response.failures is None


# ---- diff() ----------------------------------------------------------------


class TestDataRecordDiff:
    @pytest.mark.asyncio
    async def test_diff_no_changes(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": _SIMPLE_COLS,
                "dataRecordId": PropertyValue(_RECORD_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": _SIMPLE_COLS,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_environment_id_triggers_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            old_state={"environmentId": PropertyValue(_ENV_ID), "tableLogicalName": PropertyValue(_TABLE)},
            new_inputs={"environmentId": PropertyValue(_ENV_ID_2), "tableLogicalName": PropertyValue(_TABLE)},
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert "environmentId" in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_table_name_triggers_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            old_state={"environmentId": PropertyValue(_ENV_ID), "tableLogicalName": PropertyValue(_TABLE)},
            new_inputs={"environmentId": PropertyValue(_ENV_ID), "tableLogicalName": PropertyValue(_TABLE_2)},
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "tableLogicalName" in response.diffs
        assert "tableLogicalName" in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["tableLogicalName"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_columns_change_triggers_update_not_replace(self, handler):
        old_cols = PropertyValue({"name": PropertyValue("Acme")})
        new_cols = PropertyValue({"name": PropertyValue("AcmeCorp")})
        request = DiffRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": old_cols,
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": new_cols,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "columns" in response.diffs
        assert "columns" not in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["columns"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_disable_on_destroy_change_triggers_update(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(False),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(True),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "disableOnDestroy" in response.diffs
        assert "disableOnDestroy" not in (response.replaces or [])
        assert response.detailed_diff is not None
        assert response.detailed_diff["disableOnDestroy"].kind == PropertyDiffKind.UPDATE
