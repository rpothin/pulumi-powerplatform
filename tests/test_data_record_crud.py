"""Tests for DataRecord resource handler — create, read, update, delete."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CreateRequest,
    DeleteRequest,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.data_record import DataRecordResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:DataRecord::my-record"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_TABLE = "account"
_RECORD_ID = "dddddddd-5555-6666-7777-eeeeeeeeeeee"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"
_COLLECTION = "accounts"
_PRIMARY_ID = "accountid"

# Standard BAP response carrying Dataverse instance URL.
_ENV_RESPONSE = {
    "properties": {
        "linkedEnvironmentMetadata": {"instanceUrl": _INSTANCE_URL}
    }
}

_ENV_RESPONSE_NO_DV = {"properties": {}}

# EntityDefinitions metadata for the 'account' table.
_ENTITY_META = {
    "PrimaryIdAttribute": _PRIMARY_ID,
    "LogicalCollectionName": _COLLECTION,
}


def _make_mock_client() -> MagicMock:
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    client.raw = raw_mock
    client.credential = MagicMock()
    return client


def _make_handler(mock_client: MagicMock, dv_mock: MagicMock) -> DataRecordResource:
    handler = DataRecordResource(client=mock_client)
    handler._make_dataverse_client = MagicMock(return_value=dv_mock)
    return handler


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
    return _make_handler(mock_client, dv_mock)


# ---- create() --------------------------------------------------------------


class TestDataRecordCreate:
    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)
        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_posts_to_dataverse_collection(self, handler, mock_client, dv_mock):
        """create() POSTs to the correct Dataverse collection URL."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        # Sequence: entity metadata GET, then POST (returning tuple)
        dv_mock.request.side_effect = [
            _ENTITY_META,
            ({"accountid": _RECORD_ID}, {}),
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _RECORD_ID.lower()
        assert response.properties["dataRecordId"].value == _RECORD_ID.lower()
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["tableLogicalName"].value == _TABLE

        post_call = dv_mock.request.call_args_list[1]
        assert post_call[0][0] == "POST"
        assert _COLLECTION in post_call[0][1]
        assert post_call[1]["body"] == {"name": "Acme"}

    @pytest.mark.asyncio
    async def test_create_extracts_id_from_odata_entity_id_header(self, handler, mock_client, dv_mock):
        """create() can extract GUID from the OData-EntityId response header (204 case)."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        entity_id_url = f"https://org-test.crm.dynamics.com/api/data/v9.2/accounts({_RECORD_ID})"
        dv_mock.request.side_effect = [
            _ENTITY_META,
            (None, {"odata-entityid": entity_id_url}),
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)
        assert response.resource_id == _RECORD_ID.lower()

    @pytest.mark.asyncio
    async def test_create_raises_when_no_dataverse_instance(self, handler, mock_client):
        mock_client.raw.request.return_value = _ENV_RESPONSE_NO_DV

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            timeout=300,
            preview=False,
        )
        with pytest.raises(RuntimeError, match="Dataverse"):
            await handler.create(request)

    @pytest.mark.asyncio
    async def test_create_raises_when_record_id_not_determinable(self, handler, mock_client, dv_mock):
        """create() raises when neither body nor header provides a GUID."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            (None, {}),  # No entity ID in body or headers
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            timeout=300,
            preview=False,
        )
        with pytest.raises(RuntimeError, match="record ID"):
            await handler.create(request)

    @pytest.mark.asyncio
    async def test_create_encodes_lookup_with_odata_bind(self, handler, mock_client, dv_mock):
        """Lookup columns are encoded as @odata.bind in the POST body."""
        rel_meta = {"PrimaryIdAttribute": "contactid", "LogicalCollectionName": "contacts"}
        related_id = "cccccccc-9999-8888-7777-aaaaaaaaaaaa"
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            rel_meta,  # related entity meta for lookup
            ({_PRIMARY_ID: _RECORD_ID}, {}),
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({
                    "primarycontactid": PropertyValue({
                        "tableLogicalName": PropertyValue("contact"),
                        "dataRecordId": PropertyValue(related_id),
                    }),
                }),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)
        assert response.resource_id == _RECORD_ID.lower()

        post_call = dv_mock.request.call_args_list[2]
        body = post_call[1]["body"]
        assert "primarycontactid@odata.bind" in body
        assert related_id in body["primarycontactid@odata.bind"]

    @pytest.mark.asyncio
    async def test_create_wires_m2m_ref(self, handler, mock_client, dv_mock):
        """M2M (list) columns are wired via $ref POST after record creation."""
        related_meta = {"PrimaryIdAttribute": "systemuserid", "LogicalCollectionName": "systemusers"}
        related_id = "eeeeeeee-1111-2222-3333-ffffffffffff"
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            ({_PRIMARY_ID: _RECORD_ID}, {}),  # POST record
            related_meta,                      # M2M related entity meta
            None,                              # $ref POST
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({
                    "account_systemuser": PropertyValue([
                        PropertyValue({
                            "tableLogicalName": PropertyValue("systemuser"),
                            "dataRecordId": PropertyValue(related_id),
                        }),
                    ]),
                }),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)
        assert response.resource_id == _RECORD_ID.lower()

        # The $ref POST should have been made
        ref_call = dv_mock.request.call_args_list[-1]
        assert ref_call[0][0] == "POST"
        assert "$ref" in ref_call[0][1]


# ---- read() ----------------------------------------------------------------


class TestDataRecordRead:
    @pytest.mark.asyncio
    async def test_read_returns_empty_when_env_404(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")

        request = ReadRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_no_dataverse_instance(self, handler, mock_client):
        mock_client.raw.request.return_value = _ENV_RESPONSE_NO_DV

        request = ReadRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_record_404(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            HttpError(404, "not found"),
        ]

        request = ReadRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_returns_correct_properties(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            {_PRIMARY_ID: _RECORD_ID, "name": "Acme Corp"},
        ]

        request = ReadRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            inputs={},
        )
        response = await handler.read(request)

        assert response.resource_id == _RECORD_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["tableLogicalName"].value == _TABLE
        assert response.properties["dataRecordId"].value == _RECORD_ID
        # columns should be reconstructed with the refreshed value
        assert response.properties["columns"].value["name"].value == "Acme Corp"
        # dataRecordId should not be in inputs
        assert "dataRecordId" not in response.inputs

    @pytest.mark.asyncio
    async def test_read_reraises_non_404_http_errors(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(500, "server error")

        request = ReadRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            inputs={},
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.read(request)
        assert exc_info.value.status_code == 500


# ---- update() --------------------------------------------------------------


class TestDataRecordUpdate:
    @pytest.mark.asyncio
    async def test_update_patches_changed_columns(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            None,  # PATCH response
        ]

        request = UpdateRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            olds={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            news={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme Corp")}),
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        response = await handler.update(request)
        assert response.properties["tableLogicalName"].value == _TABLE

        patch_call = dv_mock.request.call_args_list[1]
        assert patch_call[0][0] == "PATCH"
        assert _RECORD_ID in patch_call[0][1]
        assert patch_call[1]["body"] == {"name": "Acme Corp"}

    @pytest.mark.asyncio
    async def test_update_skips_patch_when_no_scalar_changes(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            # No PATCH call should be made
        ]

        request = UpdateRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            olds={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            news={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        await handler.update(request)
        # Only the entity metadata GET should have been called
        assert dv_mock.request.call_count == 1

    @pytest.mark.asyncio
    async def test_update_nulls_removed_columns(self, handler, mock_client, dv_mock):
        """Columns present in old_state but absent from new_inputs are set to null."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            None,  # PATCH
        ]

        request = UpdateRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            olds={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({
                    "name": PropertyValue("Acme"),
                    "revenue": PropertyValue(1000.0),
                }),
            },
            news={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "columns": PropertyValue({"name": PropertyValue("Acme")}),  # revenue removed
            },
            timeout=300,
            ignore_changes=[],
            preview=False,
        )
        await handler.update(request)

        patch_body = dv_mock.request.call_args_list[1][1]["body"]
        assert patch_body.get("revenue") is None


# ---- delete() --------------------------------------------------------------


class TestDataRecordDelete:
    @pytest.mark.asyncio
    async def test_delete_calls_dataverse_delete(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            None,  # DELETE
        ]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(False),
            },
            timeout=300,
        )
        await handler.delete(request)

        delete_call = dv_mock.request.call_args_list[1]
        assert delete_call[0][0] == "DELETE"
        assert _RECORD_ID in delete_call[0][1]

    @pytest.mark.asyncio
    async def test_delete_deactivates_before_deleting_when_disable_on_destroy(
        self, handler, mock_client, dv_mock
    ):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            None,  # PATCH deactivate
            None,  # DELETE
        ]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(True),
            },
            timeout=300,
        )
        await handler.delete(request)

        calls = dv_mock.request.call_args_list
        assert calls[1][0][0] == "PATCH"
        assert calls[1][1]["body"] == {"statecode": 1}
        assert calls[2][0][0] == "DELETE"

    @pytest.mark.asyncio
    async def test_delete_ignores_404_on_deactivate(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            HttpError(404, "not found"),  # PATCH deactivate: record already gone
        ]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(True),
            },
            timeout=300,
        )
        await handler.delete(request)

    @pytest.mark.asyncio
    async def test_delete_ignores_404_on_final_delete(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            HttpError(404, "not found"),  # DELETE: already gone
        ]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(False),
            },
            timeout=300,
        )
        await handler.delete(request)

    @pytest.mark.asyncio
    async def test_delete_noop_when_env_404(self, handler, mock_client, dv_mock):
        mock_client.raw.request.side_effect = HttpError(404, "env not found")

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
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
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
            },
            timeout=300,
        )
        await handler.delete(request)
        dv_mock.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_reraises_non_404_deactivate_errors(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = [
            _ENTITY_META,
            HttpError(403, "forbidden"),
        ]

        request = DeleteRequest(
            urn=_URN,
            resource_id=_RECORD_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "tableLogicalName": PropertyValue(_TABLE),
                "disableOnDestroy": PropertyValue(True),
            },
            timeout=300,
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.delete(request)
        assert exc_info.value.status_code == 403
