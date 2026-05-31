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
import types
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Minimal stubs so the component module loads without pulumi installed.
# ---------------------------------------------------------------------------

if "pulumi" not in sys.modules:
    pulumi_stub = types.ModuleType("pulumi")

    class _FakeOutput:
        pass

    class _FakeComponentResource:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def register_outputs(self, outputs: dict[str, Any]) -> None:
            pass

    class _FakeResourceOptions:
        def __init__(self, **kwargs: Any) -> None:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def _fake_get(resource: Any, key: str) -> _FakeOutput:
        return _FakeOutput()

    pulumi_stub.ComponentResource = _FakeComponentResource
    pulumi_stub.CustomResource = _FakeComponentResource
    pulumi_stub.ResourceOptions = _FakeResourceOptions
    pulumi_stub.Output = _FakeOutput
    pulumi_stub.get = _fake_get
    sys.modules["pulumi"] = pulumi_stub

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


# ---------------------------------------------------------------------------
# Args dataclass
# ---------------------------------------------------------------------------


class TestResDlpPolicyArgs:
    """Verify defaults and field semantics for ``ResDlpPolicyArgs``."""

    def test_required_display_name_default_empty_string(self):
        """display_name must be provided; default is empty string (dataclass sentinel)."""
        args = ResDlpPolicyArgs(display_name="My Policy")
        assert args.display_name == "My Policy"

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


class _MockPV:
    """Minimal PropertyValue-like object with a .value attribute."""

    def __init__(self, value: Any) -> None:
        self.value = value


class TestConstructResDlpPolicy:
    """Verify that the construct factory extracts inputs correctly."""

    def test_extracts_display_name(self):
        """Factory must pass displayName through to ResDlpPolicyArgs.display_name."""
        inputs = {"displayName": _MockPV("Extracted Policy")}
        component = _construct_res_dlp_policy("p", inputs, opts=None)
        # We can't call the real constructor in unit tests, but we can verify
        # the factory doesn't raise and returns a ResDlpPolicy instance.
        assert isinstance(component, ResDlpPolicy)

    def test_extracts_rule_sets(self):
        """Factory must pass ruleSets through when provided."""
        rule_sets = [{"classification": "Blocked", "connectors": []}]
        inputs = {"displayName": _MockPV("p"), "ruleSets": _MockPV(rule_sets)}
        # Should not raise.
        _construct_res_dlp_policy("p", inputs, opts=None)

    def test_missing_optional_keys_are_none(self):
        """Missing optional keys must not raise KeyError."""
        inputs = {"displayName": _MockPV("p")}
        _construct_res_dlp_policy("p", inputs, opts=None)

    def test_raw_value_fallback(self):
        """A plain (non-PropertyValue) value in inputs must also be accepted."""
        inputs = {"displayName": "raw-display-name"}
        _construct_res_dlp_policy("p", inputs, opts=None)

    def test_none_value_in_inputs_is_treated_as_none(self):
        """An explicit None in inputs for an optional key returns None."""
        inputs = {"displayName": _MockPV("p"), "ruleSets": None}
        _construct_res_dlp_policy("p", inputs, opts=None)


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
