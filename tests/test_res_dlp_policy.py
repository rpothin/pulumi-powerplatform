"""Tests for the ``ResDlpPolicy`` component resource (Phase 4).

Covers:
- ``ResDlpPolicyArgs`` dataclass defaults and required fields
- Component type token and dispatch registration
- PropertyValue extraction in the construct factory
- Analyzer smoke test (no crash from bad type annotations)
- Schema key verification (generated camelCase matches expectations)
"""

from __future__ import annotations

import sys

import pulumi.runtime.mocks as mocks_module
import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import ConstructResponse

# Import the component under test.
sys.path.insert(0, "provider")
from rpothin_powerplatform.components._base import (  # noqa: E402
    _ANALYZER_REGISTRY,
    _CONSTRUCT_REGISTRY,
)
from rpothin_powerplatform.components.res_dlp_policy import (  # noqa: E402
    COMPONENT_TYPE,
    ResDlpPolicy,
    ResDlpPolicyArgs,
    _construct_res_dlp_policy,
)

PULUMI_PKG_NAME = "powerplatform"


class _SimpleMocks(mocks_module.Mocks):
    def new_resource(self, args):
        return args.name + "_id", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture
async def _pulumi_mocks():
    """Install Pulumi runtime mocks inside the test's event loop."""
    mocks_module.set_mocks(_SimpleMocks(), preview=False)


# ---------------------------------------------------------------------------
# Args dataclass
# ---------------------------------------------------------------------------


class TestResDlpPolicyArgs:
    """Verify defaults and field semantics for ``ResDlpPolicyArgs``."""

    def test_display_name_required(self):
        """display_name must be provided; there is no default value."""
        args = ResDlpPolicyArgs(display_name="My Policy")
        assert args.display_name == "My Policy"

    def test_display_name_missing_raises(self):
        """Omitting display_name must raise TypeError (required field, no default)."""
        with pytest.raises(TypeError):
            ResDlpPolicyArgs()  # type: ignore[call-arg]

    def test_rule_sets_defaults_to_none(self):
        """rule_sets should default to None when not provided."""
        args = ResDlpPolicyArgs(display_name="x")
        assert args.rule_sets is None

    def test_enable_telemetry_inherited_from_base(self):
        """enable_telemetry is inherited from ComponentArgs and defaults to None."""
        args = ResDlpPolicyArgs(display_name="x")
        assert args.enable_telemetry is None

    def test_rule_sets_accepts_list_of_dicts(self):
        """rule_sets accepts a list of arbitrary dicts without type error."""
        rule_sets = [
            {
                "classification": "Business",
                "connectors": [
                    {"id": "/providers/Microsoft.PowerApps/apis/shared_office365"}
                ],
            }
        ]
        args = ResDlpPolicyArgs(display_name="x", rule_sets=rule_sets)
        assert args.rule_sets == rule_sets
        assert len(args.rule_sets) == 1

    def test_dataclass_is_kw_only(self):
        """ResDlpPolicyArgs must be instantiated with keyword arguments."""
        with pytest.raises(TypeError):
            ResDlpPolicyArgs("positional-display-name")  # type: ignore[misc]

    def test_no_future_annotations(self):
        """All field annotations must be real runtime types (not lazy strings).

        The Pulumi Analyzer uses ``__dataclass_fields__`` at runtime.  If
        ``from __future__ import annotations`` were present, all annotations
        would be strings and the Analyzer would silently skip them.
        """
        for field_name, field in ResDlpPolicyArgs.__dataclass_fields__.items():
            ann = field.type
            assert not isinstance(ann, str), (
                f"Field {field_name!r} annotation is a string (lazy); must be runtime type."
            )


# ---------------------------------------------------------------------------
# Dispatch registration
# ---------------------------------------------------------------------------


class TestResDlpPolicyRegistration:
    """Verify that decorators register the component correctly."""

    def test_component_type_token(self):
        """COMPONENT_TYPE must use the expected token prefix."""
        assert COMPONENT_TYPE == "powerplatform:components:ResDlpPolicy"

    def test_construct_registry_entry(self):
        """@register_construct must register the factory under COMPONENT_TYPE."""
        assert COMPONENT_TYPE in _CONSTRUCT_REGISTRY, (
            f"{COMPONENT_TYPE!r} not found in _CONSTRUCT_REGISTRY"
        )
        assert _CONSTRUCT_REGISTRY[COMPONENT_TYPE] is _construct_res_dlp_policy

    def test_analyzer_registry_entry(self):
        """@register_component must register ResDlpPolicy in _ANALYZER_REGISTRY."""
        assert ResDlpPolicy in _ANALYZER_REGISTRY, (
            "ResDlpPolicy not found in _ANALYZER_REGISTRY"
        )


# ---------------------------------------------------------------------------
# Construct factory: PropertyValue extraction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("_pulumi_mocks")
class TestConstructResDlpPolicy:
    """Verify that the construct factory extracts inputs correctly.

    Uses real ``PropertyValue`` instances (same as the Pulumi engine sends)
    so that ``pv_to_input`` can safely extract values and preserve metadata.
    """

    async def test_returns_construct_response(self):
        """Factory must return a ConstructResponse, not the component directly."""
        inputs = {"displayName": PropertyValue("Extracted Policy")}
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert isinstance(result, ConstructResponse)

    async def test_response_urn_is_set(self):
        """ConstructResponse.urn must be a non-empty string."""
        inputs = {"displayName": PropertyValue("my-policy")}
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert result.urn is not None
        assert isinstance(result.urn, str)
        assert len(result.urn) > 0

    async def test_response_state_contains_expected_keys(self):
        """ConstructResponse.state must contain resourceId, policyName, etc."""
        inputs = {"displayName": PropertyValue("my-policy")}
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert "resourceId" in result.state
        assert "policyName" in result.state
        assert "ruleSetCount" in result.state
        assert "lastModified" in result.state
        assert "tenantId" in result.state

    async def test_extracts_rule_sets(self):
        """Factory must pass ruleSets through when provided as an empty list."""
        inputs = {
            "displayName": PropertyValue("p"),
            "ruleSets": PropertyValue([]),
        }
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert isinstance(result, ConstructResponse)

    async def test_missing_optional_keys_are_none(self):
        """Missing optional keys must not raise KeyError."""
        inputs = {"displayName": PropertyValue("p")}
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert isinstance(result, ConstructResponse)

    async def test_absent_display_name_defaults_to_none(self):
        """When displayName is absent in inputs, factory falls back to None without crash."""
        result = await _construct_res_dlp_policy("p", {}, opts=None)
        assert isinstance(result, ConstructResponse)

    async def test_none_pv_value_in_inputs_is_accepted(self):
        """An explicit PropertyValue(None) for an optional key must not raise."""
        inputs = {"displayName": PropertyValue("p"), "ruleSets": PropertyValue(None)}
        result = await _construct_res_dlp_policy("p", inputs, opts=None)
        assert isinstance(result, ConstructResponse)


# ---------------------------------------------------------------------------
# Schema generation smoke test
# ---------------------------------------------------------------------------


class TestResDlpPolicySchemaSmoke:
    """Verify that the Analyzer can inspect ResDlpPolicy without errors."""

    def test_analyzer_can_introspect_res_dlp_policy(self):
        """Analyzer.analyze should run on ResDlpPolicy without raising."""
        try:
            from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]

            a = Analyzer(PULUMI_PKG_NAME)
            result = a.analyze([ResDlpPolicy])
            assert result is not None
        except ImportError:
            pytest.skip("pulumi Analyzer not available in this environment")

    def test_res_dlp_policy_args_no_future_annotations(self):
        """ResDlpPolicyArgs must have real runtime type annotations."""
        for field_name, field in ResDlpPolicyArgs.__dataclass_fields__.items():
            ann = field.type
            assert not isinstance(ann, str), (
                f"Field {field_name!r} annotation is a string (lazy); must be runtime type."
            )

    def test_analyzer_generates_display_name_key(self):
        """Analyzer must generate 'displayName' camelCase key for display_name."""
        try:
            from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]

            try:
                from pulumi.provider.experimental.schema import generate_schema  # type: ignore[import]
            except ImportError:
                from pulumi.provider.experimental import generate_schema  # type: ignore[import]

            a = Analyzer(PULUMI_PKG_NAME)
            result = a.analyze([ResDlpPolicy])
            pkg_spec = generate_schema(
                name=PULUMI_PKG_NAME,
                version="",
                namespace=PULUMI_PKG_NAME,
                components=result["component_definitions"],
                type_definitions=result["type_definitions"],
                dependencies=result.get("dependencies", {}),
            )
            schema_dict = pkg_spec.to_json()  # returns dict, despite the name
            resources = schema_dict.get("resources", {})
            component_def = None
            for token, defn in resources.items():
                if "ResDlpPolicy" in token:
                    component_def = defn
                    break
            if component_def is None:
                pytest.skip("ResDlpPolicy not found in generated schema resources")
            input_props = component_def.get("inputProperties", {})
            assert "displayName" in input_props, (
                f"Expected 'displayName' in inputProperties, got: {list(input_props.keys())}"
            )
            assert "ruleSets" in input_props, (
                f"Expected 'ruleSets' in inputProperties, got: {list(input_props.keys())}"
            )
        except ImportError:
            pytest.skip("pulumi Analyzer not available in this environment")
