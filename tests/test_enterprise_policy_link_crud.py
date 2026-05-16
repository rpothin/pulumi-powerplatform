"""Tests for EnterprisePolicyLink resource handler — create, read, delete (async lifecycle)."""

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
from rpothin_powerplatform.resources.enterprise_policy_link import EnterprisePolicyLinkResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:EnterprisePolicyLink::my-link"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_POLICY_TYPE = "NetworkInjection"
_POLICY_KEY = "vnets"
_SYSTEM_ID = (
    "/regions/unitedstates/providers/Microsoft.PowerPlatform"
    "/enterprisePolicies/cccccccc-4444-5555-6666-dddddddddddd"
)
_RESOURCE_ID = f"{_ENV_ID}_networkinjection"
_POLL_URL = "https://api.bap.microsoft.com/operations/some-op-id"

_PROPS = {
    "environmentId": PropertyValue(_ENV_ID),
    "policyType": PropertyValue(_POLICY_TYPE),
    "systemId": PropertyValue(_SYSTEM_ID),
}

# Polling response shapes.
_STATE_SUCCEEDED = {"State": {"Id": "Succeeded"}}
_STATE_FAILED = {"State": {"Id": "Failed"}}
_STATE_RUNNING = {"State": {"Id": "Running"}}

# Environment read response with policy linked.
_ENV_WITH_POLICY = {
    "properties": {
        "enterprisePolicies": {
            _POLICY_KEY: {"systemId": _SYSTEM_ID, "status": "Linked"}
        }
    }
}

# Environment read response with no enterprise policies.
_ENV_NO_POLICY = {"properties": {}}


def _make_mock_client() -> MagicMock:
    """Build a MagicMock PowerPlatformClient with an async-capable raw.request."""
    client = MagicMock(spec=PowerPlatformClient)
    raw_mock = MagicMock()
    raw_mock.request = AsyncMock()
    type(client).raw = PropertyMock(return_value=raw_mock)
    return client


@pytest.fixture
def mock_client():
    return _make_mock_client()


@pytest.fixture
def handler(mock_client):
    return EnterprisePolicyLinkResource(client=mock_client)


@pytest.fixture
def mock_sleep():
    return AsyncMock()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------

class TestEnterprisePolicyLinkCreate:
    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id_without_api_calls(self, handler, mock_client):
        request = CreateRequest(
            urn=_URN,
            properties=_PROPS,
            timeout=300,
            preview=True,
        )
        response = await handler.create(request)
        assert response.resource_id == "preview-id"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_polls_location_header_until_succeeded(self, handler, mock_client, mock_sleep):
        # POST returns 202 + Location; poll returns Succeeded.
        mock_client.raw.request.side_effect = [
            (None, {"location": _POLL_URL}),
            _STATE_SUCCEEDED,
        ]
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)

        assert response.resource_id == _RESOURCE_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["policyType"].value == _POLICY_TYPE
        assert response.properties["systemId"].value == _SYSTEM_ID
        # sleep called once for poll interval
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_polls_operation_location_header(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = [
            (None, {"Operation-Location": _POLL_URL}),
            _STATE_SUCCEEDED,
        ]
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)
        assert response.resource_id == _RESOURCE_ID

    @pytest.mark.asyncio
    async def test_create_treats_409_as_already_linked_success(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = HttpError(409, "Conflict")
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)
        assert response.resource_id == _RESOURCE_ID
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_sync_success_when_no_location_header(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.return_value = (None, {})
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)
        assert response.resource_id == _RESOURCE_ID
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_polls_multiple_times_before_success(self, handler, mock_client, mock_sleep):
        # POST → Running → Running → Succeeded
        mock_client.raw.request.side_effect = [
            (None, {"location": _POLL_URL}),
            _STATE_RUNNING,
            _STATE_RUNNING,
            _STATE_SUCCEEDED,
        ]
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)
        assert response.resource_id == _RESOURCE_ID
        # sleep called twice while running
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_create_retries_on_failed_operation(self, handler, mock_client, mock_sleep):
        # Attempt 1: POST → Failed; sleep 15s; Attempt 2: POST → Succeeded
        mock_client.raw.request.side_effect = [
            (None, {"location": _POLL_URL}),  # POST attempt 1
            _STATE_FAILED,                     # poll attempt 1
            (None, {"location": _POLL_URL}),  # POST attempt 2
            _STATE_SUCCEEDED,                  # poll attempt 2
        ]
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        response = await handler.create(request, _sleep=mock_sleep)
        assert response.resource_id == _RESOURCE_ID
        # sleep called once for retry delay
        mock_sleep.assert_called_once_with(15.0)

    @pytest.mark.asyncio
    async def test_create_raises_after_all_attempts_fail(self, handler, mock_client, mock_sleep):
        from rpothin_powerplatform.resources.enterprise_policy_link import _MAX_LINK_ATTEMPTS

        # All _MAX_LINK_ATTEMPTS POST + poll pairs return Failed.
        side_effects = []
        for _ in range(_MAX_LINK_ATTEMPTS):
            side_effects.append((None, {"location": _POLL_URL}))
            side_effects.append(_STATE_FAILED)
        mock_client.raw.request.side_effect = side_effects

        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        with pytest.raises(RuntimeError, match="after .* attempts"):
            await handler.create(request, _sleep=mock_sleep)

    @pytest.mark.asyncio
    async def test_create_resource_id_is_env_id_underscore_policy_type_lower(
        self, handler, mock_client, mock_sleep
    ):
        mock_client.raw.request.return_value = (None, {})
        for policy_type, expected_suffix in [
            ("NetworkInjection", "networkinjection"),
            ("Encryption", "encryption"),
            ("Identity", "identity"),
        ]:
            props = {
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(policy_type),
                "systemId": PropertyValue(_SYSTEM_ID),
            }
            request = CreateRequest(urn=_URN, properties=props, timeout=300, preview=False)
            response = await handler.create(request, _sleep=mock_sleep)
            assert response.resource_id == f"{_ENV_ID}_{expected_suffix}"

    @pytest.mark.asyncio
    async def test_create_raises_non_409_http_errors(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = HttpError(403, "Forbidden")
        request = CreateRequest(urn=_URN, properties=_PROPS, timeout=300, preview=False)
        with pytest.raises(HttpError) as exc_info:
            await handler.create(request, _sleep=mock_sleep)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

class TestEnterprisePolicyLinkRead:
    @pytest.mark.asyncio
    async def test_read_returns_state_when_policy_linked(self, handler, mock_client):
        mock_client.raw.request.return_value = _ENV_WITH_POLICY
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        response = await handler.read(request)
        assert response.resource_id == _RESOURCE_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["policyType"].value == _POLICY_TYPE
        assert response.properties["systemId"].value == _SYSTEM_ID
        assert response.inputs["systemId"].value == _SYSTEM_ID

    @pytest.mark.asyncio
    async def test_read_returns_empty_on_404(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(404, "not found")
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        response = await handler.read(request)
        assert response.resource_id == ""
        assert response.properties == {}

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_no_enterprise_policies(self, handler, mock_client):
        mock_client.raw.request.return_value = _ENV_NO_POLICY
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        response = await handler.read(request)
        assert response.resource_id == ""

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_policy_key_has_no_system_id(self, handler, mock_client):
        mock_client.raw.request.return_value = {
            "properties": {"enterprisePolicies": {_POLICY_KEY: {"status": "NotLinked"}}}
        }
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        response = await handler.read(request)
        assert response.resource_id == ""

    @pytest.mark.asyncio
    async def test_read_returns_empty_when_system_id_drifted(self, handler, mock_client):
        """Drift detection: live systemId differs from state → signal removal."""
        different_system_id = (
            "/regions/europe/providers/Microsoft.PowerPlatform"
            "/enterprisePolicies/eeeeeeee-7777-8888-9999-ffffffffffff"
        )
        mock_client.raw.request.return_value = {
            "properties": {
                "enterprisePolicies": {_POLICY_KEY: {"systemId": different_system_id}}
            }
        }
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        response = await handler.read(request)
        assert response.resource_id == ""

    @pytest.mark.asyncio
    async def test_read_accepts_when_no_system_id_in_inputs(self, handler, mock_client):
        """When inputs has no systemId (e.g. import), any live systemId is accepted."""
        mock_client.raw.request.return_value = _ENV_WITH_POLICY
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={},
            inputs={},
        )
        response = await handler.read(request)
        assert response.resource_id == _RESOURCE_ID
        assert response.properties["systemId"].value == _SYSTEM_ID

    @pytest.mark.asyncio
    async def test_read_reraises_non_404_http_errors(self, handler, mock_client):
        mock_client.raw.request.side_effect = HttpError(500, "server error")
        request = ReadRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            inputs=_PROPS,
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.read(request)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_read_encryption_policy(self, handler, mock_client):
        """Verify the correct key is used for Encryption policy type."""
        env_id = _ENV_ID
        resource_id = f"{env_id}_encryption"
        mock_client.raw.request.return_value = {
            "properties": {
                "enterprisePolicies": {
                    "customerManagedKeys": {"systemId": _SYSTEM_ID}
                }
            }
        }
        props = {
            "environmentId": PropertyValue(env_id),
            "policyType": PropertyValue("Encryption"),
            "systemId": PropertyValue(_SYSTEM_ID),
        }
        request = ReadRequest(
            urn=_URN, resource_id=resource_id, properties=props, inputs=props
        )
        response = await handler.read(request)
        assert response.resource_id == resource_id
        assert response.properties["policyType"].value == "Encryption"

    @pytest.mark.asyncio
    async def test_read_identity_policy(self, handler, mock_client):
        """Verify the correct key is used for Identity policy type."""
        env_id = _ENV_ID
        resource_id = f"{env_id}_identity"
        mock_client.raw.request.return_value = {
            "properties": {
                "enterprisePolicies": {
                    "identity": {"systemId": _SYSTEM_ID}
                }
            }
        }
        props = {
            "environmentId": PropertyValue(env_id),
            "policyType": PropertyValue("Identity"),
            "systemId": PropertyValue(_SYSTEM_ID),
        }
        request = ReadRequest(
            urn=_URN, resource_id=resource_id, properties=props, inputs=props
        )
        response = await handler.read(request)
        assert response.resource_id == resource_id
        assert response.properties["policyType"].value == "Identity"


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

class TestEnterprisePolicyLinkDelete:
    @pytest.mark.asyncio
    async def test_delete_posts_unlink_and_polls_to_success(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = [
            (None, {"location": _POLL_URL}),
            _STATE_SUCCEEDED,
        ]
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        await handler.delete(request, _sleep=mock_sleep)
        assert mock_client.raw.request.call_count == 2
        # First call: POST unlink
        post_call = mock_client.raw.request.call_args_list[0]
        assert post_call[0][0] == "POST"
        assert "unlink" in post_call[0][1]

    @pytest.mark.asyncio
    async def test_delete_sync_unlink_when_no_location_header(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.return_value = (None, {})
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        await handler.delete(request, _sleep=mock_sleep)
        mock_client.raw.request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_ignores_404(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = HttpError(404, "not found")
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        # Should not raise.
        await handler.delete(request, _sleep=mock_sleep)

    @pytest.mark.asyncio
    async def test_delete_skips_unlink_when_system_id_missing(self, handler, mock_client, mock_sleep):
        """If systemId is missing from state, skip the unlink call (log a warning)."""
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
            },
            timeout=300,
        )
        await handler.delete(request, _sleep=mock_sleep)
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_reraises_non_404_errors(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = HttpError(500, "server error")
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        with pytest.raises(HttpError) as exc_info:
            await handler.delete(request, _sleep=mock_sleep)
        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_delete_raises_when_unlink_operation_fails(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.side_effect = [
            (None, {"location": _POLL_URL}),
            _STATE_FAILED,
        ]
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        with pytest.raises(RuntimeError, match="Unlink operation"):
            await handler.delete(request, _sleep=mock_sleep)

    @pytest.mark.asyncio
    async def test_delete_uses_correct_api_version_and_body(self, handler, mock_client, mock_sleep):
        mock_client.raw.request.return_value = (None, {})
        request = DeleteRequest(
            urn=_URN,
            resource_id=_RESOURCE_ID,
            properties=_PROPS,
            timeout=300,
        )
        await handler.delete(request, _sleep=mock_sleep)
        call_args = mock_client.raw.request.call_args
        assert call_args[1]["api_version"] == "2019-10-01"
        assert call_args[1]["body"] == {"systemId": _SYSTEM_ID}
        assert call_args[1]["return_headers"] is True
