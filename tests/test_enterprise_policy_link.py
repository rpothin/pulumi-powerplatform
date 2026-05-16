"""Tests for EnterprisePolicyLink resource handler — check and diff behavior."""

from __future__ import annotations

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import CheckRequest, DiffRequest, PropertyDiffKind
from rpothin_powerplatform.resources.enterprise_policy_link import EnterprisePolicyLinkResource

_URN = "urn:pulumi:test::test::powerplatform:index:EnterprisePolicyLink::my-link"
_ENV_ID = "aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb"
_ENV_ID_2 = "bbbbbbbb-2222-3333-4444-cccccccccccc"
_POLICY_TYPE = "NetworkInjection"
_POLICY_TYPE_2 = "Encryption"
_SYSTEM_ID = (
    "/regions/unitedstates/providers/Microsoft.PowerPlatform"
    "/enterprisePolicies/cccccccc-4444-5555-6666-dddddddddddd"
)
_SYSTEM_ID_2 = (
    "/regions/europe/providers/Microsoft.PowerPlatform"
    "/enterprisePolicies/eeeeeeee-7777-8888-9999-ffffffffffff"
)


@pytest.fixture
def handler():
    return EnterprisePolicyLinkResource(client=None)  # type: ignore[arg-type]


class TestEnterprisePolicyLinkCheck:
    @pytest.mark.asyncio
    async def test_check_accepts_valid_inputs(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()
        assert response.inputs["policyType"].value == _POLICY_TYPE
        assert response.inputs["systemId"].value == _SYSTEM_ID

    @pytest.mark.asyncio
    async def test_check_normalizes_environment_id_to_lowercase(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID.upper()),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
        )
        response = await handler.check(request)
        assert response.failures is None
        assert response.inputs["environmentId"].value == _ENV_ID.lower()

    @pytest.mark.asyncio
    async def test_check_accepts_all_valid_policy_types(self, handler):
        for policy_type in ("NetworkInjection", "Encryption", "Identity"):
            request = CheckRequest(
                urn=_URN,
                random_seed=b"",
                old_inputs={},
                new_inputs={
                    "environmentId": PropertyValue(_ENV_ID),
                    "policyType": PropertyValue(policy_type),
                    "systemId": PropertyValue(_SYSTEM_ID),
                },
            )
            response = await handler.check(request)
            assert response.failures is None, f"Expected no failures for policyType={policy_type!r}"

    @pytest.mark.asyncio
    async def test_check_rejects_missing_environment_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
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
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
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
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "environmentId" for f in response.failures)
        assert any("UUID" in f.reason or "GUID" in f.reason for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_missing_policy_type(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "policyType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_invalid_policy_type(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue("UnknownType"),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "policyType" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_missing_system_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "systemId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_malformed_system_id(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue("not-an-arm-path"),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "systemId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_rejects_system_id_missing_region_prefix(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(
                    "/providers/Microsoft.PowerPlatform/enterprisePolicies/cccccccc-4444-5555-6666-dddddddddddd"
                ),
            },
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert any(f.property == "systemId" for f in response.failures)

    @pytest.mark.asyncio
    async def test_check_reports_multiple_failures(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={},
        )
        response = await handler.check(request)
        assert response.failures is not None
        props = {f.property for f in response.failures}
        assert "environmentId" in props
        assert "policyType" in props
        assert "systemId" in props


class TestEnterprisePolicyLinkDiff:
    @pytest.mark.asyncio
    async def test_diff_same_inputs_no_changes(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}_networkinjection",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_environment_id_changed_requires_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}_networkinjection",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID_2),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "environmentId" in response.diffs
        assert response.replaces is not None
        assert "environmentId" in response.replaces
        assert response.detailed_diff is not None
        assert response.detailed_diff["environmentId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_policy_type_changed_requires_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}_networkinjection",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE_2),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "policyType" in response.diffs
        assert response.replaces is not None
        assert "policyType" in response.replaces
        assert response.detailed_diff is not None
        assert response.detailed_diff["policyType"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_system_id_changed_requires_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}_networkinjection",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID_2),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert "systemId" in response.diffs
        assert response.replaces is not None
        assert "systemId" in response.replaces
        assert response.detailed_diff is not None
        assert response.detailed_diff["systemId"].kind == PropertyDiffKind.UPDATE_REPLACE

    @pytest.mark.asyncio
    async def test_diff_all_changed_all_require_replace(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id=f"{_ENV_ID}_networkinjection",
            old_state={
                "environmentId": PropertyValue(_ENV_ID),
                "policyType": PropertyValue(_POLICY_TYPE),
                "systemId": PropertyValue(_SYSTEM_ID),
            },
            new_inputs={
                "environmentId": PropertyValue(_ENV_ID_2),
                "policyType": PropertyValue(_POLICY_TYPE_2),
                "systemId": PropertyValue(_SYSTEM_ID_2),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert len(response.diffs) == 3
        assert response.replaces is not None
        assert len(response.replaces) == 3
        assert response.detailed_diff is not None
        for field in ("environmentId", "policyType", "systemId"):
            assert response.detailed_diff[field].kind == PropertyDiffKind.UPDATE_REPLACE
