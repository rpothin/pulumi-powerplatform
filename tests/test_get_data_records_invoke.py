"""Tests for the getDataRecords function handler — invoke with mocked clients."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_data_records import GetDataRecordsFunction

_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_COLLECTION = "accounts"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"

# BAP response for environments with Dataverse.
_ENV_RESPONSE = {
    "properties": {
        "linkedEnvironmentMetadata": {"instanceUrl": _INSTANCE_URL}
    }
}


def _make_mock_client() -> MagicMock:
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    client.raw = raw_mock
    client.credential = MagicMock()
    return client


def _make_dv_mock(records: list | None = None) -> MagicMock:
    dv = MagicMock()
    dv.request = AsyncMock()
    return dv


def _make_handler(mock_client: MagicMock, dv_mock: MagicMock) -> GetDataRecordsFunction:
    handler = GetDataRecordsFunction(client=mock_client)
    handler._make_dataverse_client = MagicMock(return_value=dv_mock)
    return handler


@pytest.fixture
def mock_client():
    return _make_mock_client()


@pytest.fixture
def dv_mock():
    return _make_dv_mock()


@pytest.fixture
def handler(mock_client, dv_mock):
    return _make_handler(mock_client, dv_mock)


class TestGetDataRecordsInvoke:
    @pytest.mark.asyncio
    async def test_invoke_returns_records(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"accountid": "r1", "name": "Acme"}, {"accountid": "r2", "name": "Contoso"}]
        }

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        response = await handler.invoke(request)

        assert dv_mock.request.call_count == 1
        records_pv = response.return_value["records"]
        records = records_pv.value
        assert len(records) == 2
        assert records[0].value["name"].value == "Acme"
        assert records[1].value["name"].value == "Contoso"

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        response = await handler.invoke(request)
        assert dv_mock.request.call_count == 1
        assert len(response.return_value["records"].value) == 0

    @pytest.mark.asyncio
    async def test_invoke_url_uses_entity_collection_directly(self, handler, mock_client, dv_mock):
        """entityCollection is used directly in the URL — no EntityDefinitions lookup."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        await handler.invoke(request)

        assert dv_mock.request.call_count == 1
        get_call = dv_mock.request.call_args_list[0]
        assert get_call[0][0] == "GET"
        assert f"/api/data/v9.2/{_COLLECTION}" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_always_includes_count(self, handler, mock_client, dv_mock):
        """$count=true is always added to the OData query."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": [], "@odata.count": 0}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        assert "$count=true" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_passes_filter(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": [{"accountid": "r1"}]}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "filter": PropertyValue("name eq 'Acme'"),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        assert "$filter=name eq 'Acme'" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_passes_select(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "select": PropertyValue([PropertyValue("name"), PropertyValue("revenue")]),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        assert "$select=name,revenue" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_passes_top(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "top": PropertyValue(5.0),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        assert "$top=5" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_passes_orderby(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "orderby": PropertyValue("createdon desc"),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        assert "$orderby=createdon desc" in get_call[0][1]

    @pytest.mark.asyncio
    async def test_invoke_passes_expand(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "expand": PropertyValue([
                    PropertyValue({
                        "navigationProperty": PropertyValue("contact_set"),
                        "select": PropertyValue("fullname,email"),
                    }),
                ]),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        url = get_call[0][1]
        assert "$expand=contact_set($select=fullname,email)" in url

    @pytest.mark.asyncio
    async def test_invoke_passes_apply(self, handler, mock_client, dv_mock):
        """$apply aggregation string is forwarded to the OData query."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"revenue_sum": 1000.0}],
            "@odata.count": 1,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
                "apply": PropertyValue("aggregate(revenue with sum as revenue_sum)"),
            },
        )
        await handler.invoke(request)

        get_call = dv_mock.request.call_args_list[0]
        url = get_call[0][1]
        assert "$apply=aggregate(revenue with sum as revenue_sum)" in url
        assert "$count=true" in url

    @pytest.mark.asyncio
    async def test_invoke_returns_total_rows_count(self, handler, mock_client, dv_mock):
        """totalRowsCount is populated from @odata.count in the response."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"accountid": "r1"}],
            "@odata.count": 42,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        response = await handler.invoke(request)

        assert response.return_value["totalRowsCount"].value == 42

    @pytest.mark.asyncio
    async def test_invoke_returns_total_rows_count_limit_exceeded(self, handler, mock_client, dv_mock):
        """totalRowsCountLimitExceeded is populated from the CRM annotation."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"accountid": "r1"}],
            "@odata.count": 5000,
            "@Microsoft.Dynamics.CRM.totalrecordcountlimitexceeded": True,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        response = await handler.invoke(request)

        assert response.return_value["totalRowsCount"].value == 5000
        assert response.return_value["totalRowsCountLimitExceeded"].value is True

    @pytest.mark.asyncio
    async def test_invoke_total_rows_count_defaults_to_zero(self, handler, mock_client, dv_mock):
        """totalRowsCount defaults to 0 when @odata.count is absent."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        response = await handler.invoke(request)

        assert response.return_value["totalRowsCount"].value == 0
        assert response.return_value["totalRowsCountLimitExceeded"].value is False

    @pytest.mark.asyncio
    async def test_invoke_raises_when_no_dataverse_instance(self, handler, mock_client):
        mock_client.raw.request.return_value = {"properties": {}}

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        with pytest.raises(RuntimeError, match="Dataverse"):
            await handler.invoke(request)

    @pytest.mark.asyncio
    async def test_invoke_raises_when_missing_required_args(self, handler):
        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        with pytest.raises(ValueError, match="entityCollection"):
            await handler.invoke(request)

    @pytest.mark.asyncio
    async def test_invoke_warns_on_next_link(self, handler, mock_client, dv_mock, caplog):
        """A warning should be logged when @odata.nextLink is present in the response."""
        import logging
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"accountid": "r1"}],
            "@odata.nextLink": "https://org.crm.dynamics.com/api/data/v9.2/accounts?$skiptoken=xyz",
        }

        request = InvokeRequest(
            tok="powerplatform:index:getDataRecords",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "entityCollection": PropertyValue(_COLLECTION),
            },
        )
        with caplog.at_level(logging.WARNING, logger="rpothin_powerplatform.functions.get_data_records"):
            await handler.invoke(request)

        assert any("nextLink" in msg or "next_link" in msg.lower() or "first page" in msg
                   for msg in caplog.messages)
