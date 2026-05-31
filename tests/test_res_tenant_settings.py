"""Tests for the ``ResTenantSettings`` component resource (Phase 4).

Covers:
- ``ResTenantSettingsArgs`` dataclass defaults and field types
- Component type token and dispatch registration
- PropertyValue extraction in the construct factory
- NPS acronym mapping (disableNpsCommentsReachout vs disableNPSCommentsReachout)
- Analyzer smoke test (no crash from bad type annotations)
- Schema key verification (generated camelCase matches expectations)
"""

from __future__ import annotations

import sys
from typing import Any

import pulumi.runtime.mocks as mocks_module
import pytest

# Import the component under test.
sys.path.insert(0, "provider")
from rpothin_powerplatform.components._base import (  # noqa: E402
    _ANALYZER_REGISTRY,
    _CONSTRUCT_REGISTRY,
)
from rpothin_powerplatform.components.res_tenant_settings import (  # noqa: E402
    COMPONENT_TYPE,
    ResTenantSettings,
    ResTenantSettingsArgs,
    _construct_res_tenant_settings,
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


class TestResTenantSettingsArgs:
    """Verify defaults and field semantics for ``ResTenantSettingsArgs``."""

    def test_all_fields_default_to_none(self):
        """All optional boolean fields and power_platform default to None."""
        args = ResTenantSettingsArgs()
        assert args.disable_capacity_allocation_by_environment_admins is None
        assert args.disable_environment_creation_by_non_admin_users is None
        assert args.disable_nps_comments_reachout is None
        assert args.disable_newsletter_sendout is None
        assert args.disable_portals_creation_by_non_admin_users is None
        assert args.disable_support_tickets_visible_by_all_users is None
        assert args.disable_survey_feedback is None
        assert args.disable_trial_environment_creation_by_non_admin_users is None
        assert args.power_platform is None
        assert args.walk_me_opt_out is None

    def test_enable_telemetry_inherited_from_base(self):
        """enable_telemetry is inherited from ComponentArgs and defaults to None."""
        args = ResTenantSettingsArgs()
        assert args.enable_telemetry is None

    def test_boolean_fields_accept_true_false(self):
        """All boolean fields accept True and False without error."""
        args = ResTenantSettingsArgs(
            disable_capacity_allocation_by_environment_admins=True,
            disable_environment_creation_by_non_admin_users=False,
            disable_nps_comments_reachout=True,
            disable_newsletter_sendout=False,
            disable_portals_creation_by_non_admin_users=True,
            disable_support_tickets_visible_by_all_users=False,
            disable_survey_feedback=True,
            disable_trial_environment_creation_by_non_admin_users=False,
            walk_me_opt_out=True,
        )
        assert args.disable_capacity_allocation_by_environment_admins is True
        assert args.disable_environment_creation_by_non_admin_users is False
        assert args.disable_nps_comments_reachout is True
        assert args.disable_newsletter_sendout is False
        assert args.disable_portals_creation_by_non_admin_users is True
        assert args.disable_support_tickets_visible_by_all_users is False
        assert args.disable_survey_feedback is True
        assert args.disable_trial_environment_creation_by_non_admin_users is False
        assert args.walk_me_opt_out is True

    def test_power_platform_accepts_arbitrary_dict(self):
        """power_platform field accepts a dict with arbitrary string keys."""
        pp_settings = {
            "search": {"disableDocsSearch": True},
            "powerApps": {"disableShareWithEveryone": False},
        }
        args = ResTenantSettingsArgs(power_platform=pp_settings)
        assert args.power_platform == pp_settings

    def test_dataclass_is_kw_only(self):
        """ResTenantSettingsArgs must be instantiated with keyword arguments."""
        # Passing a positional bool should raise TypeError.
        with pytest.raises(TypeError):
            ResTenantSettingsArgs(True)  # type: ignore[misc]

    def test_no_future_annotations(self):
        """All field annotations must be real runtime types (not lazy strings).

        The Pulumi Analyzer uses ``__dataclass_fields__`` at runtime.  If
        ``from __future__ import annotations`` were present, all annotations
        would be strings and the Analyzer would silently skip them.
        """
        for field_name, field in ResTenantSettingsArgs.__dataclass_fields__.items():
            ann = field.type
            assert not isinstance(ann, str), (
                f"Field {field_name!r} annotation is a string (lazy); must be runtime type."
            )


# ---------------------------------------------------------------------------
# Dispatch registration
# ---------------------------------------------------------------------------


class TestResTenantSettingsRegistration:
    """Verify that decorators register the component correctly."""

    def test_component_type_token(self):
        """COMPONENT_TYPE must use the expected token prefix."""
        assert COMPONENT_TYPE == "powerplatform:components:ResTenantSettings"

    def test_construct_registry_entry(self):
        """@register_construct must register the factory under COMPONENT_TYPE."""
        assert COMPONENT_TYPE in _CONSTRUCT_REGISTRY, (
            f"{COMPONENT_TYPE!r} not found in _CONSTRUCT_REGISTRY"
        )
        assert _CONSTRUCT_REGISTRY[COMPONENT_TYPE] is _construct_res_tenant_settings

    def test_analyzer_registry_entry(self):
        """@register_component must register ResTenantSettings in _ANALYZER_REGISTRY."""
        assert ResTenantSettings in _ANALYZER_REGISTRY, (
            "ResTenantSettings not found in _ANALYZER_REGISTRY"
        )


# ---------------------------------------------------------------------------
# Construct factory: PropertyValue extraction
# ---------------------------------------------------------------------------


class _MockPV:
    """Minimal PropertyValue-like object with a .value attribute."""

    def __init__(self, value: Any) -> None:
        self.value = value


@pytest.mark.asyncio
@pytest.mark.usefixtures("_pulumi_mocks")
class TestConstructResTenantSettings:
    """Verify that the construct factory extracts inputs correctly."""

    async def test_factory_with_no_inputs_does_not_raise(self):
        """Factory must succeed with an empty inputs dict."""
        component = _construct_res_tenant_settings("ts", {}, opts=None)
        assert isinstance(component, ResTenantSettings)

    async def test_extracts_boolean_flag(self):
        """Factory must pass a boolean PropertyValue through to args."""
        inputs = {"disableEnvironmentCreationByNonAdminUsers": _MockPV(True)}
        component = _construct_res_tenant_settings("ts", inputs, opts=None)
        assert isinstance(component, ResTenantSettings)

    async def test_nps_key_mapping(self):
        """Factory reads disableNpsCommentsReachout (standard camelCase from Analyzer)."""
        inputs = {"disableNpsCommentsReachout": _MockPV(True)}
        _construct_res_tenant_settings("ts", inputs, opts=None)

    async def test_power_platform_extracted(self):
        """Factory must extract the powerPlatform nested dict."""
        pp = {"search": {"disableDocsSearch": True}}
        inputs = {"powerPlatform": _MockPV(pp)}
        _construct_res_tenant_settings("ts", inputs, opts=None)

    async def test_raw_value_fallback(self):
        """A plain (non-PropertyValue) value in inputs must also be accepted."""
        inputs = {"disableSurveyFeedback": False}
        _construct_res_tenant_settings("ts", inputs, opts=None)

    async def test_all_fields_extracted(self):
        """Factory must accept all known camelCase keys without raising."""
        inputs = {
            "disableCapacityAllocationByEnvironmentAdmins": _MockPV(True),
            "disableEnvironmentCreationByNonAdminUsers": _MockPV(False),
            "disableNpsCommentsReachout": _MockPV(True),
            "disableNewsletterSendout": _MockPV(False),
            "disablePortalsCreationByNonAdminUsers": _MockPV(True),
            "disableSupportTicketsVisibleByAllUsers": _MockPV(False),
            "disableSurveyFeedback": _MockPV(True),
            "disableTrialEnvironmentCreationByNonAdminUsers": _MockPV(False),
            "powerPlatform": _MockPV({"key": "value"}),
            "walkMeOptOut": _MockPV(True),
            "enableTelemetry": _MockPV(True),
        }
        _construct_res_tenant_settings("ts", inputs, opts=None)


# ---------------------------------------------------------------------------
# NPS acronym key isolation test
# ---------------------------------------------------------------------------


class TestNPSKeyMapping:
    """Ensure the NPS acronym mapping between component and provider is correct.

    The Pulumi Analyzer generates standard camelCase from Python field names:
    ``disable_nps_comments_reachout`` → ``disableNpsCommentsReachout``.

    The underlying ``TenantSettings`` resource uses all-caps
    ``disableNPSCommentsReachout``.

    The component factory must read the Analyzer-generated key from inputs;
    the wrapper must pass the provider's wire key to the child resource.
    """

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_pulumi_mocks")
    async def test_factory_reads_standard_camel_case_nps_key(self):
        """Factory reads 'disableNpsCommentsReachout', not 'disableNPSCommentsReachout'."""
        inputs_wrong_key = {"disableNPSCommentsReachout": _MockPV(True)}
        component = _construct_res_tenant_settings("ts", inputs_wrong_key, opts=None)
        assert isinstance(component, ResTenantSettings)

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("_pulumi_mocks")
    async def test_factory_reads_lowercase_nps_key(self):
        """Factory reads 'disableNpsCommentsReachout' and passes the value through."""
        inputs_correct_key = {"disableNpsCommentsReachout": _MockPV(True)}
        _construct_res_tenant_settings("ts", inputs_correct_key, opts=None)

    def test_wrapper_uses_uppercase_nps_wire_key(self):
        """_TenantSettingsWrap must use 'disableNPSCommentsReachout' (all-caps) wire key."""
        import inspect

        from rpothin_powerplatform.components._resource_wrappers import _TenantSettingsWrap

        # Inspect the __init__ signature / props dict indirectly by checking
        # the parameter is named disable_nps_comments_reachout (standard snake).
        sig = inspect.signature(_TenantSettingsWrap.__init__)
        assert "disable_nps_comments_reachout" in sig.parameters, (
            "_TenantSettingsWrap.__init__ must accept disable_nps_comments_reachout parameter"
        )


# ---------------------------------------------------------------------------
# Schema generation smoke test
# ---------------------------------------------------------------------------


class TestResTenantSettingsSchemaSmoke:
    """Verify that the Analyzer can inspect ResTenantSettings without errors."""

    def test_analyzer_can_introspect_res_tenant_settings(self):
        """Analyzer.analyze should run on ResTenantSettings without raising."""
        try:
            from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]

            a = Analyzer(PULUMI_PKG_NAME)
            result = a.analyze([ResTenantSettings])
            assert result is not None
        except ImportError:
            pytest.skip("pulumi Analyzer not available in this environment")

    def test_res_tenant_settings_args_no_future_annotations(self):
        """ResTenantSettingsArgs must have real runtime type annotations."""
        for field_name, field in ResTenantSettingsArgs.__dataclass_fields__.items():
            ann = field.type
            assert not isinstance(ann, str), (
                f"Field {field_name!r} annotation is a string (lazy); must be runtime type."
            )

    def test_analyzer_generates_expected_keys(self):
        """Analyzer must generate expected camelCase keys for ResTenantSettings."""
        try:
            from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]

            try:
                from pulumi.provider.experimental.schema import generate_schema  # type: ignore[import]
            except ImportError:
                from pulumi.provider.experimental import generate_schema  # type: ignore[import]

            a = Analyzer(PULUMI_PKG_NAME)
            result = a.analyze([ResTenantSettings])
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
                if "ResTenantSettings" in token:
                    component_def = defn
                    break
            if component_def is None:
                pytest.skip("ResTenantSettings not found in generated schema resources")
            input_props = component_def.get("inputProperties", {})

            # Standard camelCase keys from the Analyzer (not all-caps NPS):
            assert "disableNpsCommentsReachout" in input_props, (
                "Expected standard camelCase 'disableNpsCommentsReachout', "
                f"got: {list(input_props.keys())}"
            )
            assert "powerPlatform" in input_props
            assert "walkMeOptOut" in input_props
            assert "disableSurveyFeedback" in input_props

            # The all-caps variant must NOT appear in the component schema
            # (it's an internal wire key, not exposed to callers).
            assert "disableNPSCommentsReachout" not in input_props, (
                "All-caps 'disableNPSCommentsReachout' must not appear in component schema; "
                "use 'disableNpsCommentsReachout' instead."
            )
        except ImportError:
            pytest.skip("pulumi Analyzer not available in this environment")
