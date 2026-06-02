"""Tests for the PipelineSharing resource handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pulumi.provider.experimental.property_value import Computed, PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    CreateRequest,
    DeleteRequest,
    DiffRequest,
    PropertyDiffKind,
    ReadRequest,
)
from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.resources.pipeline_sharing import PipelineSharingResource
from rpothin_powerplatform.utils import HttpError

_URN = "urn:pulumi:test::test::powerplatform:index:PipelineSharing::my-sharing"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_PIPELINE_ID = "bbbbbbbb-2222-3333-4444-cccccccccccc"
_TEAM_ID = "cccccccc-3333-4444-5555-dddddddddddd"
_INSTANCE_URL = "https://org-test.crm.dynamics.com/"
_RESOURCE_ID = f"{_ENV_ID}/{_PIPELINE_ID}/{_TEAM_ID}"

_PROPS = {
    "environmentId": PropertyValue(_ENV_ID),
    "pipelineId": PropertyValue(_PIPELINE_ID),
    "teamId": PropertyValue(_TEAM_ID),
}

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
    resource = PipelineSharingResource(client=mock_client)
    resource._make_dataverse_client = MagicMock(return_value=dv_mock)
    return resource


class TestPipelineSharingCheck:
    @pytest.mark.asyncio
    async def test_check_applies_default_access_mask(self, handler):
        response = await handler.check(
            CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs=dict(_PROPS),
            )
        )

        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID
        assert response.inputs["pipelineId"].value == _PIPELINE_ID
        assert response.inputs["teamId"].value == _TEAM_ID
        assert response.inputs["accessMask"].value == "ReadAccess"

    @pytest.mark.asyncio
    async def test_check_passes_computed_pipeline_and_team_ids(self, handler):
        """check() must not fail when pipelineId/teamId are Computed (unknown during preview)."""
        response = await handler.check(
            CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={
                    "environmentId": PropertyValue(_ENV_ID),
                    "pipelineId": PropertyValue(Computed()),
                    "teamId": PropertyValue(Computed()),
                },
            )
        )

        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_preserves_computed_access_mask(self, handler):
        """check() must preserve a Computed accessMask rather than replacing it with the default."""
        response = await handler.check(
            CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={
                    **_PROPS,
                    "accessMask": PropertyValue(Computed()),
                },
            )
        )

        assert response.failures is None
        assert isinstance(response.inputs["accessMask"].value, Computed)
        response = await handler.check(
            CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={},
            )
        )

        assert response.failures is not None
        assert {failure.property for failure in response.failures} == {
            "environmentId",
            "pipelineId",
            "teamId",
        }


    @pytest.mark.asyncio
    async def test_diff_skips_replace_when_new_ids_are_computed(self, handler):
        """diff() must not force a replace when new pipelineId/teamId are Computed (preview)."""
        response = await handler.diff(
            DiffRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                old_state={**_PROPS, "accessMask": PropertyValue("ReadAccess")},
                new_inputs={
                    "environmentId": PropertyValue(_ENV_ID),
                    "pipelineId": PropertyValue(Computed()),
                    "teamId": PropertyValue(Computed()),
                    "accessMask": PropertyValue("ReadAccess"),
                },
                ignore_changes=[],
            )
        )

        assert response.changes is False
        assert not response.replaces

    @pytest.mark.asyncio
    async def test_diff_marks_all_inputs_replace_only(self, handler):
        response = await handler.diff(
            DiffRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                old_state={**_PROPS, "accessMask": PropertyValue("ReadAccess")},
                new_inputs={**_PROPS, "accessMask": PropertyValue("AppendAccess")},
                ignore_changes=[],
            )
        )

        assert response.changes is True
        assert response.delete_before_replace is True
        assert "accessMask" in response.replaces
        assert response.detailed_diff["accessMask"].kind == PropertyDiffKind.UPDATE_REPLACE


    @pytest.mark.asyncio
    async def test_create_preview_preserves_computed_pipeline_and_team_ids(self, handler, mock_client):
        """create(preview=True) must pass Computed values through to outputs, not stringify them."""
        response = await handler.create(
            CreateRequest(
                urn=_URN,
                properties={
                    "environmentId": PropertyValue(_ENV_ID),
                    "pipelineId": PropertyValue(Computed()),
                    "teamId": PropertyValue(Computed()),
                    "accessMask": PropertyValue("ReadAccess"),
                },
                timeout=300,
                preview=True,
            )
        )

        assert response.resource_id == "preview-id"
        assert isinstance(response.properties["pipelineId"].value, Computed)
        assert isinstance(response.properties["teamId"].value, Computed)
        assert response.properties["grantedAccessMask"].value == "ReadAccess"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_preview_returns_preview_id(self, handler, mock_client):
        response = await handler.create(
            CreateRequest(
                urn=_URN,
                properties=dict(_PROPS),
                timeout=300,
                preview=True,
            )
        )

        assert response.resource_id == "preview-id"
        assert response.properties["grantedAccessMask"].value == "ReadAccess"
        mock_client.raw.request.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_grants_access(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {}

        response = await handler.create(
            CreateRequest(
                urn=_URN,
                properties={**_PROPS, "accessMask": PropertyValue("ReadAccess")},
                timeout=300,
                preview=False,
            )
        )

        assert response.resource_id == _RESOURCE_ID
        assert response.properties["grantedAccessMask"].value == "ReadAccess"
        dv_mock.request.assert_awaited_once_with(
            "POST",
            "/api/data/v9.0/GrantAccess",
            body={
                "Target": {
                    "deploymentpipelineid": _PIPELINE_ID,
                    "@odata.type": "Microsoft.Dynamics.CRM.deploymentpipeline",
                },
                "PrincipalAccess": {
                    "Principal": {
                        "teamid": _TEAM_ID,
                        "@odata.type": "Microsoft.Dynamics.CRM.team",
                    },
                    "AccessMask": "ReadAccess",
                },
            },
            api_version=None,
        )


class TestPipelineSharingRead:
    @pytest.mark.asyncio
    async def test_read_returns_stored_state_without_api_call(self, handler, mock_client):
        response = await handler.read(
            ReadRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                properties={**_PROPS, "grantedAccessMask": PropertyValue("ReadAccess")},
                inputs={**_PROPS, "accessMask": PropertyValue("ReadAccess")},
            )
        )

        assert response.resource_id == _RESOURCE_ID
        assert response.properties["environmentId"].value == _ENV_ID
        assert response.properties["pipelineId"].value == _PIPELINE_ID
        assert response.properties["teamId"].value == _TEAM_ID
        assert response.properties["grantedAccessMask"].value == "ReadAccess"
        mock_client.raw.request.assert_not_awaited()


class TestPipelineSharingDelete:
    @pytest.mark.asyncio
    async def test_delete_revokes_access(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {}

        await handler.delete(
            DeleteRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                properties=dict(_PROPS),
                timeout=300,
            )
        )

        dv_mock.request.assert_awaited_once_with(
            "POST",
            "/api/data/v9.0/RevokeAccess",
            body={
                "Target": {
                    "deploymentpipelineid": _PIPELINE_ID,
                    "@odata.type": "Microsoft.Dynamics.CRM.deploymentpipeline",
                },
                "Revokee": {
                    "teamid": _TEAM_ID,
                    "@odata.type": "Microsoft.Dynamics.CRM.team",
                },
            },
            api_version=None,
        )

    @pytest.mark.asyncio
    async def test_delete_ignores_404(self, handler, mock_client, dv_mock):
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.side_effect = HttpError(404, "not found")

        await handler.delete(
            DeleteRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                properties=dict(_PROPS),
                timeout=300,
            )
        )

    @pytest.mark.asyncio
    async def test_delete_falls_back_to_resource_id_when_properties_empty(self, handler, mock_client, dv_mock):
        """_resolve_ids must not raise AttributeError on DeleteRequest (no .inputs field)."""
        mock_client.raw.request.return_value = _ENV_RESPONSE
        dv_mock.request.return_value = {}

        await handler.delete(
            DeleteRequest(
                urn=_URN,
                resource_id=_RESOURCE_ID,
                properties={},  # empty — forces fallback to resource_id split
                timeout=300,
            )
        )

        dv_mock.request.assert_awaited_once()
        call_body = dv_mock.request.call_args.kwargs["body"]
        assert call_body["Target"]["deploymentpipelineid"] == _PIPELINE_ID
