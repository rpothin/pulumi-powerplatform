"""Tests for Environment resource handler — create, read, update, delete with mocked RawApiClient."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    CreateRequest,
    DeleteRequest,
    DiffRequest,
    ReadRequest,
    UpdateRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.environment import EnvironmentResource
from rpothin_powerplatform.utils import HttpError

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
            "azureRegion": "westus2",
            "updateCadence": {"id": "Frequent"},
            "billingPolicy": {"id": "billing-policy-id"},
            "parentEnvironmentGroup": {"id": "env-group-id"},
            "usedBy": {"id": "owner-guid", "type": "1"},
            "bingChatEnabled": True,
            "copilotPolicies": {"crossGeoCopilotDataMovementEnabled": True},
            "states": {
                "runtime": {"id": "Enabled", "runtimeReasonCode": "Ready"},
                "management": {"id": "NotSpecified"},
            },
            "linkedEnvironmentMetadata": {
                "domainName": "testenv",
                "instanceUrl": "https://testenv.crm.dynamics.com",
                "currency": {"code": "USD"},
                "baseLanguage": 1033,
                "securityGroupId": "sg-guid",
                "resourceId": "org-resource-id",
                "uniqueName": "testenv",
                "version": "9.2.24124.00182",
                "backgroundOperationsState": "Enabled",
                "template": ["D365_Sales"],
            },
            "linkedAppMetadata": {
                "type": "ModelDriven",
                "id": "app-guid",
                "url": "https://testenv.crm.dynamics.com/apps/app-guid",
            },
            "enterprisePolicies": {
                "identity": {
                    "id": "ep-id",
                    "location": "westus2",
                    "systemId": "sys-id",
                    "linkStatus": "Linked",
                }
            },
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
        """Create simulates the 202 async pattern: POST → poll → provisionInstance → final GET."""
        # POST returns an async-provisioning response
        async_response = _fake_env_response(provisioning_state="Running")
        # Polling GET returns Succeeded
        poll_response = _fake_env_response(provisioning_state="Succeeded")
        # _wait_for_visibility GET
        visibility_response = _fake_env_response()
        # provisionInstance POST returns None
        provision_result = None
        # _poll_dataverse_provisioning GET
        poll_dv_response = _fake_env_response()
        # Final GET
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [
            async_response, poll_response, visibility_response,
            provision_result, poll_dv_response, final_response,
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "description": PropertyValue("Test description"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("testenv"),
                }),
            },
            timeout=300,
            preview=False,
        )
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        assert response.properties["location"].value == "unitedstates"
        assert response.properties["environmentType"].value == "Sandbox"
        dv = response.properties["dataverse"].value
        assert dv["domainName"].value == "testenv"
        assert dv["currencyCode"].value == "USD"
        assert dv["languageCode"].value == 1033
        assert response.properties["state"].value == "Ready"
        # 6 calls: POST, poll GET, visibility GET, provisionInstance POST, poll_dv GET, final GET
        assert mock_client.raw.request.await_count == 6

    @pytest.mark.asyncio
    async def test_create_already_succeeded(self, handler, mock_client):
        """When POST immediately returns Succeeded, skip polling; still call provisionInstance."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        visibility_response = _fake_env_response()
        provision_result = None
        poll_dv_response = _fake_env_response()
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [
            post_response, visibility_response, provision_result, poll_dv_response, final_response,
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "description": PropertyValue("Test description"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("testenv"),
                }),
            },
            timeout=300,
            preview=False,
        )
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        # 5 calls: POST + visibility GET + provisionInstance POST + poll_dv GET + final GET
        assert mock_client.raw.request.await_count == 5

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
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
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
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
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

    @pytest.mark.asyncio
    async def test_create_final_get_retries_on_404(self, handler, mock_client):
        """POST returns Succeeded immediately; first final GET returns 404, second succeeds."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [
            post_response,
            HttpError(404, "not found"),
            final_response,
        ]

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
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        # 3 calls: POST + 404 final GET + success final GET
        assert mock_client.raw.request.await_count == 3

    @pytest.mark.asyncio
    async def test_create_poll_handles_404(self, handler, mock_client):
        """POST returns Running; poll GET returns 404, next poll returns Succeeded; final GET succeeds."""
        post_response = _fake_env_response(provisioning_state="Running")
        succeeded_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [
            post_response,
            HttpError(404, "not found"),
            succeeded_response,
            final_response,
        ]

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
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        assert response.properties["displayName"].value == "Test Env"
        # 4 calls: POST + 404 poll GET + succeeded poll GET + final GET
        assert mock_client.raw.request.await_count == 4

    @pytest.mark.asyncio
    async def test_create_with_security_group_id(self, handler, mock_client):
        """Create with securityGroupId inside dataverse — verify it is sent in the provisionInstance body."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        visibility_response = _fake_env_response()
        provision_result = None
        poll_dv_response = _fake_env_response()
        final_response = _fake_env_response()
        mock_client.raw.request.side_effect = [
            post_response, visibility_response, provision_result, poll_dv_response, final_response,
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "securityGroupId": PropertyValue("sg-guid-123"),
                }),
            },
            timeout=300,
            preview=False,
        )
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        # provisionInstance is the 3rd call (index 2)
        provision_call = mock_client.raw.request.call_args_list[2]
        assert "provisionInstance" in provision_call[0][1]
        provision_body = provision_call[1]["body"]
        assert provision_body["securityGroupId"] == "sg-guid-123"

    @pytest.mark.asyncio
    async def test_create_with_azure_region(self, handler, mock_client):
        """Create with azureRegion — verify it is sent at properties.azureRegion."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()
        mock_client.raw.request.side_effect = [post_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "azureRegion": PropertyValue("westus2"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        call_body = mock_client.raw.request.call_args_list[0][1]["body"]
        assert call_body["properties"]["azureRegion"] == "westus2"

    @pytest.mark.asyncio
    async def test_create_with_cadence(self, handler, mock_client):
        """Create with cadence — verify it is sent at properties.updateCadence.id."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()
        mock_client.raw.request.side_effect = [post_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "cadence": PropertyValue("Frequent"),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        call_body = mock_client.raw.request.call_args_list[0][1]["body"]
        assert call_body["properties"]["updateCadence"]["id"] == "Frequent"

    @pytest.mark.asyncio
    async def test_create_with_enterprise_policies(self, handler, mock_client):
        """Create with enterprisePolicies — verify they are sent under properties.enterprisePolicies."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        final_response = _fake_env_response()
        mock_client.raw.request.side_effect = [post_response, final_response]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "enterprisePolicies": PropertyValue([
                    PropertyValue({
                        "type": PropertyValue("Identity"),
                        "id": PropertyValue("ep-id"),
                        "location": PropertyValue("westus2"),
                        "systemId": PropertyValue("sys-id"),
                        "status": PropertyValue("Linked"),
                    })
                ]),
            },
            timeout=300,
            preview=False,
        )
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        call_body = mock_client.raw.request.call_args_list[0][1]["body"]
        ep = call_body["properties"]["enterprisePolicies"]
        assert "identity" in ep
        assert ep["identity"]["id"] == "ep-id"
        assert ep["identity"]["location"] == "westus2"
        assert ep["identity"]["linkStatus"] == "Linked"


class TestEnvironmentCheck:
    """Tests for the check method."""

    @pytest.mark.asyncio
    async def test_check_invalid_cadence(self, handler):
        """check() should reject cadence values outside Frequent/Moderate."""
        request = CheckRequest(
            urn=_URN,
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "cadence": PropertyValue("Weekly"),
            },
            random_seed=b"",
        )
        response = await handler.check(request)
        assert response.failures is not None
        failure_props = [f.property for f in response.failures]
        assert "cadence" in failure_props

    @pytest.mark.asyncio
    async def test_check_valid_cadence(self, handler):
        """check() should accept Frequent and Moderate cadence values."""
        for cadence in ("Frequent", "Moderate"):
            request = CheckRequest(
                urn=_URN,
                old_inputs={},
                new_inputs={
                    "displayName": PropertyValue("Test"),
                    "location": PropertyValue("unitedstates"),
                    "environmentType": PropertyValue("Sandbox"),
                    "cadence": PropertyValue(cadence),
                },
                random_seed=b"",
            )
            response = await handler.check(request)
            failure_props = [f.property for f in (response.failures or [])]
            assert "cadence" not in failure_props


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
        # New fields should appear in outputs
        assert response.properties["azureRegion"].value == "westus2"
        assert response.properties["cadence"].value == "Frequent"
        assert response.properties["allowBingSearch"].value is True
        assert response.properties["linkedAppType"].value == "ModelDriven"
        assert response.properties["linkedAppUrl"].value == "https://testenv.crm.dynamics.com/apps/app-guid"
        # Dataverse fields are nested inside the dataverse block
        dv = response.properties["dataverse"].value
        assert dv["organizationId"].value == "org-resource-id"
        assert dv["uniqueName"].value == "testenv"
        assert dv["version"].value == "9.2.24124.00182"
        assert dv["securityGroupId"].value == "sg-guid"
        assert dv["backgroundOperationEnabled"].value is True
        # administrationModeEnabled is only emitted when admin mode is active (True),
        # so it should be absent from state when the API returns "Enabled" runtime state.
        assert "administrationModeEnabled" not in dv

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


class TestEnvironmentDiff:
    """Tests for the diff method."""

    @pytest.mark.asyncio
    async def test_diff_enterprise_policies_changed(self, handler):
        """diff() should detect enterprise policy changes by JSON comparison."""
        old_policies = PropertyValue([
            PropertyValue({
                "type": PropertyValue("Identity"),
                "id": PropertyValue("ep-id-old"),
                "location": PropertyValue("westus2"),
                "systemId": PropertyValue("sys-id"),
                "status": PropertyValue("Linked"),
            })
        ])
        new_policies = PropertyValue([
            PropertyValue({
                "type": PropertyValue("Identity"),
                "id": PropertyValue("ep-id-new"),
                "location": PropertyValue("westus2"),
                "systemId": PropertyValue("sys-id"),
                "status": PropertyValue("Linked"),
            })
        ])

        request = DiffRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            old_state={
                "displayName": PropertyValue("Test Env"),
                "enterprisePolicies": old_policies,
            },
            new_inputs={
                "displayName": PropertyValue("Test Env"),
                "enterprisePolicies": new_policies,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert response.changes is True
        assert "enterprisePolicies" in response.diffs

    @pytest.mark.asyncio
    async def test_diff_enterprise_policies_unchanged(self, handler):
        """diff() should not flag enterprise policies if unchanged."""
        policies = PropertyValue([
            PropertyValue({
                "type": PropertyValue("Identity"),
                "id": PropertyValue("ep-id"),
                "location": PropertyValue("westus2"),
                "systemId": PropertyValue("sys-id"),
                "status": PropertyValue("Linked"),
            })
        ])

        request = DiffRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            old_state={
                "displayName": PropertyValue("Test Env"),
                "enterprisePolicies": policies,
            },
            new_inputs={
                "displayName": PropertyValue("Test Env"),
                "enterprisePolicies": policies,
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert "enterprisePolicies" not in response.diffs


class TestDataverseProvisioning:
    """Tests for the two-step Dataverse provisioning flow."""

    @pytest.mark.asyncio
    async def test_create_with_dataverse_calls_provision_instance(self, handler, mock_client):
        """When dataverse is provided, a second POST to /provisionInstance must be made."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        visibility_response = _fake_env_response()
        provision_result = None
        poll_dv_response = _fake_env_response()
        final_response = _fake_env_response()

        mock_client.raw.request.side_effect = [
            post_response, visibility_response, provision_result, poll_dv_response, final_response,
        ]

        request = CreateRequest(
            urn=_URN,
            properties={
                "displayName": PropertyValue("Test Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                }),
            },
            timeout=300,
            preview=False,
        )
        with patch("rpothin_powerplatform.resources.environment.asyncio.sleep", new_callable=AsyncMock):
            response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        # 5 calls: POST + visibility GET + provisionInstance POST + poll_dv GET + final GET
        assert mock_client.raw.request.await_count == 5
        # The 3rd call (index 2) must be the provisionInstance POST
        provision_call = mock_client.raw.request.call_args_list[2]
        assert provision_call[0][0] == "POST"
        assert "provisionInstance" in provision_call[0][1]
        provision_body = provision_call[1]["body"]
        assert provision_body["currency"]["code"] == "USD"
        assert provision_body["baseLanguage"] == 1033

    @pytest.mark.asyncio
    async def test_create_without_dataverse_skips_provision_instance(self, handler, mock_client):
        """When no dataverse block is provided, /provisionInstance must NOT be called."""
        post_response = _fake_env_response(provisioning_state="Succeeded")
        visibility_response = _fake_env_response()

        mock_client.raw.request.side_effect = [post_response, visibility_response]

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
        response = await handler.create(request)

        assert response.resource_id == _FAKE_ID
        # 2 calls: POST + visibility GET (no provisionInstance)
        assert mock_client.raw.request.await_count == 2
        for call in mock_client.raw.request.call_args_list:
            assert "provisionInstance" not in call[0][1]


class TestDataverseCheck:
    """Tests for dataverse block validation in check()."""

    @pytest.mark.asyncio
    async def test_check_dataverse_requires_currency_and_language(self, handler):
        """check() should fail when dataverse block is missing currencyCode or languageCode."""
        request = CheckRequest(
            urn=_URN,
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({"domainName": PropertyValue("myenv")}),
            },
            random_seed=b"",
        )
        response = await handler.check(request)
        assert response.failures is not None
        failure_props = [f.property for f in response.failures]
        assert "dataverse" in failure_props

    @pytest.mark.asyncio
    async def test_check_dataverse_valid_when_currency_and_language_present(self, handler):
        """check() should not fail when currencyCode and languageCode are both provided."""
        request = CheckRequest(
            urn=_URN,
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                }),
            },
            random_seed=b"",
        )
        response = await handler.check(request)
        failure_props = [f.property for f in (response.failures or [])]
        assert "dataverse" not in failure_props

    @pytest.mark.asyncio
    async def test_check_owner_id_invalid_for_non_developer(self, handler):
        """check() should fail if ownerId is set for a non-Developer environment."""
        request = CheckRequest(
            urn=_URN,
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "ownerId": PropertyValue("user-guid"),
            },
            random_seed=b"",
        )
        response = await handler.check(request)
        failure_props = [f.property for f in (response.failures or [])]
        assert "ownerId" in failure_props

    @pytest.mark.asyncio
    async def test_check_dataverse_invalid_for_developer_environment(self, handler):
        """check() should fail if the dataverse block is set for a Developer environment."""
        request = CheckRequest(
            urn=_URN,
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("Test"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Developer"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                }),
            },
            random_seed=b"",
        )
        response = await handler.check(request)
        failure_props = [f.property for f in (response.failures or [])]
        assert "dataverse" in failure_props
    """Tests for diff() behavior with the dataverse nested block."""

    @pytest.mark.asyncio
    async def test_diff_dataverse_immutable_field_triggers_replace(self, handler):
        """Changing an immutable field inside dataverse should trigger UPDATE_REPLACE."""
        from pulumi.provider.experimental.provider import PropertyDiffKind

        request = DiffRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            old_state={
                "displayName": PropertyValue("Test Env"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("myenv"),
                }),
            },
            new_inputs={
                "displayName": PropertyValue("Test Env"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("EUR"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("myenv"),
                }),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert response.changes is True
        assert "dataverse" in response.diffs
        assert response.detailed_diff["dataverse"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_dataverse_updatable_field_triggers_update(self, handler):
        """Changing a non-immutable field inside dataverse should trigger UPDATE (not replace)."""
        from pulumi.provider.experimental.provider import PropertyDiffKind

        request = DiffRequest(
            urn=_URN,
            resource_id=_FAKE_ID,
            old_state={
                "displayName": PropertyValue("Test Env"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("myenv"),
                }),
            },
            new_inputs={
                "displayName": PropertyValue("Test Env"),
                "dataverse": PropertyValue({
                    "currencyCode": PropertyValue("USD"),
                    "languageCode": PropertyValue(1033.0),
                    "domainName": PropertyValue("myenv-updated"),
                }),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)

        assert response.changes is True
        assert "dataverse" in response.diffs
        assert response.detailed_diff["dataverse"].kind == PropertyDiffKind.UPDATE

