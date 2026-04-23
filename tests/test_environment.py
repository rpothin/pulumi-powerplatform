"""Tests for Environment resource handler — check and diff."""

from __future__ import annotations

import pytest
from pulumi._types import input_type_to_dict, output_type_from_dict
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckRequest,
    DiffRequest,
    PropertyDiffKind,
)
from rpothin_powerplatform.environment import EnvironmentDataverse, EnvironmentDataverseArgs
from rpothin_powerplatform.resources.environment import EnvironmentResource

_URN = "urn:pulumi:test::test::powerplatform:index:Environment::my-env"


def _make_handler():
    """Create a handler with a None client (only check/diff need no client)."""
    return EnvironmentResource(client=None)  # type: ignore[arg-type]


class TestEnvironmentCheck:
    """Tests for the check method."""

    @pytest.mark.asyncio
    async def test_check_valid_inputs(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is None

    @pytest.mark.asyncio
    async def test_check_missing_display_name(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "displayName" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_missing_location(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "environmentType": PropertyValue("Sandbox"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "location" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_missing_environment_type(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_invalid_environment_type(self):
        handler = _make_handler()
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("InvalidType"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_all_valid_environment_types(self):
        handler = _make_handler()
        for env_type in ("Sandbox", "Production", "Trial", "Developer", "Default"):
            request = CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={
                    "displayName": PropertyValue("My Env"),
                    "location": PropertyValue("unitedstates"),
                    "environmentType": PropertyValue(env_type),
                },
            )
            response = await handler.check(request)
            assert response.failures is None, f"Expected no failures for type {env_type}"


class TestEnvironmentDiff:
    """Tests for the diff method."""

    @pytest.mark.asyncio
    async def test_diff_no_changes(self):
        handler = _make_handler()
        state = {
            "displayName": PropertyValue("My Env"),
            "location": PropertyValue("unitedstates"),
            "environmentType": PropertyValue("Sandbox"),
        }
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state=state,
            new_inputs=dict(state),
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert not response.diffs

    @pytest.mark.asyncio
    async def test_diff_display_name_is_update(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("Old Name"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("New Name"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "displayName" in response.diffs
        assert response.detailed_diff["displayName"].kind == PropertyDiffKind.UPDATE

    @pytest.mark.asyncio
    async def test_diff_location_triggers_replace(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("europe"),
                "environmentType": PropertyValue("Sandbox"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "location" in response.diffs
        assert response.detailed_diff["location"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_environment_type_triggers_replace(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Production"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "environmentType" in response.diffs
        assert response.detailed_diff["environmentType"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_description_is_update(self):
        handler = _make_handler()
        request = DiffRequest(
            urn=_URN,
            resource_id="env-123",
            old_state={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "description": PropertyValue("old"),
            },
            new_inputs={
                "displayName": PropertyValue("My Env"),
                "location": PropertyValue("unitedstates"),
                "environmentType": PropertyValue("Sandbox"),
                "description": PropertyValue("new"),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "description" in response.diffs
        assert response.detailed_diff["description"].kind == PropertyDiffKind.UPDATE


class TestEnvironmentDataverseArgs:
    """Tests for EnvironmentDataverseArgs input class."""

    def test_input_type_to_dict_produces_camel_case_keys(self):
        args = EnvironmentDataverseArgs(
            currency_code="USD",
            language_code="1033",
            domain_name="myenv",
            security_group_id="sg-123",
            administration_mode_enabled=True,
            background_operation_enabled=False,
        )
        wire = input_type_to_dict(args)
        assert wire["currencyCode"] == "USD"
        assert wire["languageCode"] == "1033"
        assert wire["domainName"] == "myenv"
        assert wire["securityGroupId"] == "sg-123"
        assert wire["administrationModeEnabled"] is True
        assert wire["backgroundOperationEnabled"] is False

    def test_none_fields_absent_from_wire_dict(self):
        args = EnvironmentDataverseArgs(currency_code="EUR")
        wire = input_type_to_dict(args)
        assert "currencyCode" in wire
        assert "domainName" not in wire
        assert "securityGroupId" not in wire

    def test_empty_constructor_produces_empty_wire_dict(self):
        args = EnvironmentDataverseArgs()
        wire = input_type_to_dict(args)
        assert wire == {}

    def test_templates_and_template_metadata(self):
        args = EnvironmentDataverseArgs(
            templates=["template-guid-1"],
            template_metadata='{"version":"1.0"}',
        )
        wire = input_type_to_dict(args)
        assert wire["templates"] == ["template-guid-1"]
        assert wire["templateMetadata"] == '{"version":"1.0"}'

    def test_setter_updates_property(self):
        args = EnvironmentDataverseArgs(currency_code="USD")
        args.currency_code = "GBP"
        assert args.currency_code == "GBP"
        assert input_type_to_dict(args)["currencyCode"] == "GBP"


class TestEnvironmentDataverse:
    """Tests for EnvironmentDataverse output class."""

    def _provider_dict(self) -> dict:
        """Simulates what the provider emits (camelCase keys)."""
        return {
            "domainName": "myenv",
            "currencyCode": "USD",
            "languageCode": 1033.0,
            "securityGroupId": "sg-123",
            "organizationId": "org-456",
            "uniqueName": "myenv_org456",
            "version": "9.2.0",
            "url": "https://myenv.crm.dynamics.com",
            "templates": ["template-guid-1"],
            "templateMetadata": '{"version":"1.0"}',
            "administrationModeEnabled": False,
            "backgroundOperationEnabled": True,
        }

    def test_output_type_from_dict_maps_camel_case_to_snake_case(self):
        obj = output_type_from_dict(EnvironmentDataverse, self._provider_dict())
        assert obj.domain_name == "myenv"
        assert obj.currency_code == "USD"
        assert obj.language_code == 1033.0
        assert obj.security_group_id == "sg-123"
        assert obj.organization_id == "org-456"
        assert obj.unique_name == "myenv_org456"
        assert obj.version == "9.2.0"
        assert obj.url == "https://myenv.crm.dynamics.com"
        assert obj.templates == ["template-guid-1"]
        assert obj.template_metadata == '{"version":"1.0"}'
        assert obj.administration_mode_enabled is False
        assert obj.background_operation_enabled is True

    def test_direct_construction_via_snake_case_kwargs(self):
        obj = EnvironmentDataverse(domain_name="testenv", currency_code="EUR", language_code=1036.0)
        assert obj.domain_name == "testenv"
        assert obj.currency_code == "EUR"
        assert obj.language_code == 1036.0

    def test_absent_fields_are_none(self):
        obj = output_type_from_dict(EnvironmentDataverse, {"domainName": "testenv"})
        assert obj.domain_name == "testenv"
        assert obj.currency_code is None
        assert obj.organization_id is None
        assert obj.url is None

    def test_all_none_construction(self):
        obj = EnvironmentDataverse()
        assert obj.domain_name is None
        assert obj.security_group_id is None
        assert obj.background_operation_enabled is None

