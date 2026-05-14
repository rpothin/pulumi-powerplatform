"""Tests for TenantSettings resource handler — check and diff behavior."""

from __future__ import annotations

from types import MappingProxyType

import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import CheckRequest, DiffRequest, PropertyDiffKind
from rpothin_powerplatform.resources.tenant_settings import TenantSettingsResource

_URN = "urn:pulumi:test::test::powerplatform:index:TenantSettings::tenant-settings"
_ZERO_UUID = "00000000-0000-0000-0000-000000000000"


def _pv_to_python(value):
    if isinstance(value, PropertyValue):
        return _pv_to_python(value.value)
    if isinstance(value, (dict, MappingProxyType)):
        return {k: _pv_to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_pv_to_python(v) for v in value]
    return value


@pytest.fixture
def handler():
    return TenantSettingsResource(client=None)  # type: ignore[arg-type]


class TestTenantSettingsCheck:
    @pytest.mark.asyncio
    async def test_check_accepts_top_level_settings(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={
                "disableEnvironmentCreationByNonAdminUsers": PropertyValue(True),
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "disableAdminDigest": PropertyValue(True),
                            }
                        )
                    }
                ),
            },
        )
        response = await handler.check(request)
        assert response.failures is None
        assert _pv_to_python(response.inputs["disableEnvironmentCreationByNonAdminUsers"]) is True
        assert _pv_to_python(response.inputs["powerPlatform"]) == {
            "governance": {"disableAdminDigest": True}
        }

    @pytest.mark.asyncio
    async def test_check_rejects_non_object_power_platform(self, handler):
        request = CheckRequest(
            urn=_URN,
            random_seed=b"",
            old_inputs={},
            new_inputs={"powerPlatform": PropertyValue([PropertyValue("not-a-map")])},
        )
        response = await handler.check(request)
        assert response.failures is not None
        assert response.failures[0].property == "powerPlatform"


class TestTenantSettingsDiff:
    @pytest.mark.asyncio
    async def test_diff_only_managed_settings_participate(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id="tenant-1",
            old_state={
                "tenantId": PropertyValue("tenant-1"),
                "_originalSettings": PropertyValue({"serverOnlyFlag": PropertyValue(True)}),
                "powerPlatform": PropertyValue(
                    {"governance": PropertyValue({"managedFlag": PropertyValue(True)})}
                ),
            },
            new_inputs={
                "tenantId": PropertyValue("tenant-2"),
                "powerPlatform": PropertyValue(
                    {"governance": PropertyValue({"managedFlag": PropertyValue(True)})}
                ),
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_normalizes_zero_uuid_to_avoid_perpetual_drift(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id="tenant-1",
            old_state={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "environmentRoutingTargetEnvironmentGroupId": PropertyValue(None),
                            }
                        )
                    }
                )
            },
            new_inputs={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {
                                "environmentRoutingTargetEnvironmentGroupId": PropertyValue(_ZERO_UUID),
                            }
                        )
                    }
                )
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is False
        assert response.diffs == []

    @pytest.mark.asyncio
    async def test_diff_detects_managed_setting_change(self, handler):
        request = DiffRequest(
            urn=_URN,
            resource_id="tenant-1",
            old_state={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {"disableEnvironmentCreationByNonAdminUsers": PropertyValue(False)}
                        )
                    }
                )
            },
            new_inputs={
                "powerPlatform": PropertyValue(
                    {
                        "governance": PropertyValue(
                            {"disableEnvironmentCreationByNonAdminUsers": PropertyValue(True)}
                        )
                    }
                )
            },
            ignore_changes=[],
        )
        response = await handler.diff(request)
        assert response.changes is True
        assert response.diffs == ["powerPlatform.governance.disableEnvironmentCreationByNonAdminUsers"]
        assert response.detailed_diff is not None
        assert (
            response.detailed_diff["powerPlatform.governance.disableEnvironmentCreationByNonAdminUsers"].kind
            == PropertyDiffKind.UPDATE
        )
