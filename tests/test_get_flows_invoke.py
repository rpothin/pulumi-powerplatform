"""Tests for the getFlows function handler — invoke with mocked Dataverse client."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import InvokeRequest
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.functions.get_flows import GetFlowsFunction
from rpothin_powerplatform.utils import HttpError

_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"

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


def _make_dv_mock() -> MagicMock:
    dv = MagicMock()
    dv.request = AsyncMock()
    return dv


def _make_handler(mock_client: MagicMock, dv_mock: MagicMock) -> GetFlowsFunction:
    handler = GetFlowsFunction(client=mock_client)
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


class TestGetFlowsInvoke:
    """Tests for the GetFlowsFunction Dataverse-based implementation."""

    @pytest.mark.asyncio
    async def test_invoke_returns_flows(self, handler, mock_client, dv_mock):
        """Happy path: two flows are returned with correct field mapping."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [
                {"workflowid": "flow-1", "name": "My First Flow", "statecode": 1},
                {"workflowid": "flow-2", "name": "My Second Flow", "statecode": 0},
            ],
            "@odata.count": 2,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler.invoke(request)

        flows_pv = response.return_value["flows"]
        flows = flows_pv.value
        assert len(flows) == 2

        f0 = flows[0].value
        assert f0["id"].value == "flow-1"
        assert f0["name"].value == "My First Flow"
        assert f0["displayName"].value == "My First Flow"
        assert f0["stateCode"].value == 1.0

        f1 = flows[1].value
        assert f1["id"].value == "flow-2"
        assert f1["stateCode"].value == 0.0

    @pytest.mark.asyncio
    async def test_invoke_empty_result(self, handler, mock_client, dv_mock):
        """Empty value list returns an empty flows array."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": [], "@odata.count": 0}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler.invoke(request)

        assert len(response.return_value["flows"].value) == 0
        assert response.return_value["totalRowsCount"].value == 0.0
        assert response.return_value["totalRowsCountLimitExceeded"].value is False

    @pytest.mark.asyncio
    async def test_invoke_total_rows_count_limit_exceeded(self, handler, mock_client, dv_mock):
        """totalRowsCountLimitExceeded is populated from the CRM annotation."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"workflowid": "f1", "name": "Flow", "statecode": 1}],
            "@odata.count": 5000,
            "@Microsoft.Dynamics.CRM.totalrecordcountlimitexceeded": True,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler.invoke(request)

        assert response.return_value["totalRowsCount"].value == 5000.0
        assert response.return_value["totalRowsCountLimitExceeded"].value is True

    @pytest.mark.asyncio
    async def test_invoke_query_includes_category_filter(self, handler, mock_client, dv_mock):
        """The OData query always includes category eq 5."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        await handler.invoke(request)

        call_url = dv_mock.request.call_args[0][1]
        assert "category eq 5" in call_url
        assert "$count=true" in call_url

    @pytest.mark.asyncio
    async def test_invoke_filter_appended_and_parenthesized(self, handler, mock_client, dv_mock):
        """Extra filter is appended with 'and' and parenthesized to preserve OData precedence."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "filter": PropertyValue("statecode eq 1"),
            },
        )
        await handler.invoke(request)

        call_url = dv_mock.request.call_args[0][1]
        assert "category eq 5 and (statecode eq 1)" in call_url

    @pytest.mark.asyncio
    async def test_invoke_top_included_in_query(self, handler, mock_client, dv_mock):
        """$top parameter is included in the OData query."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "top": PropertyValue(10.0),
            },
        )
        await handler.invoke(request)

        call_url = dv_mock.request.call_args[0][1]
        assert "$top=10" in call_url

    @pytest.mark.asyncio
    async def test_invoke_select_merged_with_required_columns(self, handler, mock_client, dv_mock):
        """Caller-supplied select is merged with required columns (workflowid, name, statecode)."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {"value": []}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={
                "environmentId": PropertyValue(_ENV_ID),
                "select": PropertyValue([PropertyValue("clientdata"), PropertyValue("description")]),
            },
        )
        await handler.invoke(request)

        call_url = dv_mock.request.call_args[0][1]
        # Required cols must be present
        assert "workflowid" in call_url
        assert "name" in call_url
        assert "statecode" in call_url
        # Caller cols must be present too
        assert "clientdata" in call_url
        assert "description" in call_url

    @pytest.mark.asyncio
    async def test_invoke_http_error_raises_runtime_error(self, handler, mock_client, dv_mock):
        """HTTP errors from Dataverse are wrapped as RuntimeError with status info."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = HttpError(500, "Internal Server Error")

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        with pytest.raises(RuntimeError, match="500"):
            await handler.invoke(request)

    @pytest.mark.asyncio
    async def test_invoke_403_org_member_error_raises_actionable_message(self, handler, mock_client, dv_mock):
        """HTTP 403 with 0x80072560 raises an actionable RuntimeError."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = HttpError(
            403,
            "GET /api/data/v9.2/workflows returned 403: "
            '{"error":{"code":"0x80072560","message":"The user is not a member of the organization."}}',
        )

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        with pytest.raises(RuntimeError, match="0x80072560") as exc_info:
            await handler.invoke(request)
        assert "Application User" in str(exc_info.value)
        assert "Dataverse" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_raises_when_no_dataverse_instance(self, handler, mock_client):
        """RuntimeError raised when environment has no Dataverse instance."""
        mock_client.raw.request.return_value = {"properties": {}}

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        with pytest.raises(RuntimeError, match="Dataverse"):
            await handler.invoke(request)

    @pytest.mark.asyncio
    async def test_invoke_raises_when_missing_env_id(self, handler):
        """ValueError raised when environmentId is missing."""
        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={},
        )
        with pytest.raises(ValueError, match="environmentId"):
            await handler.invoke(request)

    @pytest.mark.asyncio
    async def test_invoke_warns_on_next_link(self, handler, mock_client, dv_mock, caplog):
        """A warning is logged when @odata.nextLink is present in the response."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"workflowid": "f1", "name": "Flow", "statecode": 1}],
            "@odata.nextLink": "https://org-test.crm.dynamics.com/api/data/v9.2/workflows?$skiptoken=xyz",
        }

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        with caplog.at_level(logging.WARNING, logger="rpothin_powerplatform.functions.get_flows"):
            await handler.invoke(request)

        assert any("nextLink" in msg or "first page" in msg for msg in caplog.messages)

    @pytest.mark.asyncio
    async def test_invoke_statecode_2_suspended(self, handler, mock_client, dv_mock):
        """statecode=2 (Suspended) is mapped correctly to 2.0."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {
            "value": [{"workflowid": "f1", "name": "Suspended Flow", "statecode": 2}],
            "@odata.count": 1,
        }

        request = InvokeRequest(
            tok="powerplatform:index:getFlows",
            args={"environmentId": PropertyValue(_ENV_ID)},
        )
        response = await handler.invoke(request)

        flows = response.return_value["flows"].value
        assert flows[0].value["stateCode"].value == 2.0
