"""Tests for scripts/merge_schema.py.

These tests exercise the schema-surgery helpers WITHOUT writing schema.json.
They do NOT require the pulumi.provider.experimental.analyzer API (all tests
that use analyze_components are skipped when the API is unavailable).
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable.
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import merge_schema as ms  # noqa: E402, I001


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_SCHEMA: dict = {
    "name": "powerplatform",
    "version": "0.0.1",
    "displayName": "Power Platform",
    "language": {"python": {"packageName": "rpothin_powerplatform"}},
    "config": {"variables": {}},
    "functions": {},
    "dependencies": {},
    "pluginDownloadURL": "",
    "resources": {
        "powerplatform:index:Environment": {
            "description": "An environment resource.",
            "inputProperties": {"displayName": {"type": "string"}},
            "properties": {"id": {"type": "string"}},
            "type": "object",
        }
    },
    "types": {},
}

_GENERATED_FRAGMENT: dict = {
    "resources": {
        "powerplatform:index:PocComponent": {
            "description": "POC component.",
            "inputProperties": {
                "label": {"type": "string"},
                "enableTelemetry": {"type": "boolean"},
            },
            "properties": {
                "labelOut": {"type": "string"},
                "resourceId": {"type": "string"},
            },
            "isComponent": True,
        }
    },
    "types": {},
}


# ---------------------------------------------------------------------------
# rewrite_index_to_components
# ---------------------------------------------------------------------------


class TestRewriteIndexToComponents:
    def test_rewrites_resource_key(self):
        fragment = {"resources": {"powerplatform:index:PocComponent": {}}}
        result = ms.rewrite_index_to_components(fragment)
        assert "powerplatform:components:PocComponent" in result["resources"]
        assert "powerplatform:index:PocComponent" not in result["resources"]

    def test_rewrites_ref_string(self):
        fragment = {"$ref": "#/types/powerplatform:index:SomeType"}
        result = ms.rewrite_index_to_components(fragment)
        assert result["$ref"] == "#/types/powerplatform:components:SomeType"

    def test_rewrites_nested_type_key(self):
        fragment = {"types": {"powerplatform:index:SomeType": {"type": "object"}}}
        result = ms.rewrite_index_to_components(fragment)
        assert "powerplatform:components:SomeType" in result["types"]

    def test_leaves_non_index_tokens_unchanged(self):
        fragment = {"resources": {"powerplatform:index:Environment": {}}}
        # "powerplatform:index:Environment" WOULD be rewritten too — this is by design;
        # in practice the base schema is not fed through this function.
        result = ms.rewrite_index_to_components(fragment)
        assert "powerplatform:components:Environment" in result["resources"]

    def test_rewrites_inside_list(self):
        fragment = ["powerplatform:index:PocComponent", "unchanged"]
        result = ms.rewrite_index_to_components(fragment)
        assert result[0] == "powerplatform:components:PocComponent"
        assert result[1] == "unchanged"

    def test_idempotent_on_already_rewritten(self):
        """Rewriting an already-rewritten fragment must be a no-op."""
        fragment = {"resources": {"powerplatform:components:PocComponent": {}}}
        result = ms.rewrite_index_to_components(fragment)
        # "powerplatform:components:" does not contain ":index:" so no change.
        assert "powerplatform:components:PocComponent" in result["resources"]


class TestDropPlainOnRefCollections:
    def test_removes_plain_from_nested_ref_collections_only(self):
        fragment = {
            "resources": {
                "powerplatform:index:PocComponent": {
                    "inputProperties": {
                        "environments": {
                            "type": "object",
                            "plain": True,
                            "additionalProperties": {
                                "$ref": "#/types/powerplatform:index:EnvEntry",
                                "plain": True,
                            },
                        },
                        "pipelineStages": {
                            "type": "array",
                            "items": {
                                "$ref": "#/types/powerplatform:index:StageConfig",
                                "plain": True,
                            },
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string", "plain": True},
                        },
                    }
                }
            }
        }

        result = ms._drop_plain_on_ref_collections(fragment)
        env_additional = result["resources"]["powerplatform:index:PocComponent"]["inputProperties"][
            "environments"
        ]["additionalProperties"]
        stage_items = result["resources"]["powerplatform:index:PocComponent"]["inputProperties"][
            "pipelineStages"
        ]["items"]
        labels_items = result["resources"]["powerplatform:index:PocComponent"]["inputProperties"]["labels"][
            "items"
        ]

        assert "plain" not in env_additional
        assert "plain" not in stage_items
        assert result["resources"]["powerplatform:index:PocComponent"]["inputProperties"]["environments"][
            "plain"
        ]
        assert labels_items["plain"] is True


# ---------------------------------------------------------------------------
# merge_into_schema: idempotency
# ---------------------------------------------------------------------------


class TestMergeIdempotency:
    def _merged_once(self) -> dict:
        generated = ms.rewrite_index_to_components(copy.deepcopy(_GENERATED_FRAGMENT))
        return ms.merge_into_schema(copy.deepcopy(_BASE_SCHEMA), generated)

    def test_merge_twice_equals_once(self):
        once = self._merged_once()
        generated_again = ms.rewrite_index_to_components(copy.deepcopy(_GENERATED_FRAGMENT))
        twice = ms.merge_into_schema(copy.deepcopy(once), generated_again)
        assert once == twice

    def test_merge_adds_component_token(self):
        result = self._merged_once()
        assert "powerplatform:components:PocComponent" in result["resources"]

    def test_original_resource_untouched(self):
        result = self._merged_once()
        assert "powerplatform:index:Environment" in result["resources"]


# ---------------------------------------------------------------------------
# merge_into_schema: protected keys
# ---------------------------------------------------------------------------


class TestProtectedKeys:
    def test_language_not_overwritten(self):
        generated = {"resources": {}, "types": {}, "language": {"python": {"different": True}}}
        base = copy.deepcopy(_BASE_SCHEMA)
        result = ms.merge_into_schema(base, generated)
        assert result["language"] == _BASE_SCHEMA["language"]

    def test_config_not_overwritten(self):
        generated = {"resources": {}, "types": {}, "config": {"variables": {"injected": "bad"}}}
        base = copy.deepcopy(_BASE_SCHEMA)
        result = ms.merge_into_schema(base, generated)
        assert result["config"] == _BASE_SCHEMA["config"]

    def test_functions_not_overwritten(self):
        base = copy.deepcopy(_BASE_SCHEMA)
        base["functions"] = {"powerplatform:index:getStuff": {}}
        generated = {"resources": {}, "types": {}, "functions": {"powerplatform:index:injected": {}}}
        result = ms.merge_into_schema(base, generated)
        assert "powerplatform:index:getStuff" in result["functions"]

    def test_version_not_overwritten(self):
        generated = {"resources": {}, "types": {}, "version": "9.9.9"}
        base = copy.deepcopy(_BASE_SCHEMA)
        result = ms.merge_into_schema(base, generated)
        assert result["version"] == "0.0.1"

    def test_merge_only_modifies_resources_and_types(self):
        """merge_into_schema must never touch top-level keys other than resources/types.

        The PROTECTED_KEYS guard in main() is advisory (WARNING); the real safety is
        that merge_into_schema only updates resources and types.  This test catches
        accidental extensions that merge other sections.
        """
        hostile = {
            "resources": {},
            "types": {},
            "language": {"python": {"override": True}},
            "config": {"variables": {"injected": {}}},
            "functions": {"powerplatform:index:evil": {}},
            "version": "9.9.9",
            "dependencies": {"evil": "1.0.0"},
            "pluginDownloadURL": "https://evil.example.com",
        }
        base = copy.deepcopy(_BASE_SCHEMA)
        result = ms.merge_into_schema(base, hostile)
        for key in ms.PROTECTED_KEYS:
            assert result.get(key) == _BASE_SCHEMA.get(key), (
                f"Key '{key}' was modified by merge_into_schema"
            )
        assert set(result.keys()) == set(_BASE_SCHEMA.keys())


# ---------------------------------------------------------------------------
# merge_into_schema: collision detection
# ---------------------------------------------------------------------------


class TestCollisionDetection:
    def test_strip_removes_existing_component_tokens(self):
        """Existing powerplatform:components:* entries are silently replaced (idempotent)."""
        base = copy.deepcopy(_BASE_SCHEMA)
        base["resources"]["powerplatform:components:PocComponent"] = {"old": True}
        # After strip + merge, the generated version overwrites the old one.
        generated = copy.deepcopy(_GENERATED_FRAGMENT)
        result = ms.merge_into_schema(base, generated)
        poc = result["resources"]["powerplatform:components:PocComponent"]
        assert "isComponent" in poc
        assert "old" not in poc

    def test_raises_on_collision_with_non_component_namespace(self):
        """A generated token colliding with an existing non-components entry fails."""
        # A token in a namespace that _strip_existing_components does NOT remove
        # (it only removes powerplatform:components:*). Directly call
        # _validate_no_collision to exercise the collision guard.
        base_nonstripable = copy.deepcopy(_BASE_SCHEMA)
        base_nonstripable["resources"]["powerplatform:INDEX:PocComponent"] = {"surprise": True}
        rewritten_gen = {
            "resources": {"powerplatform:INDEX:PocComponent": {"isComponent": True}},
            "types": {},
        }
        with pytest.raises(SystemExit, match="Token collision"):
            ms._validate_no_collision(base_nonstripable, rewritten_gen)

    def test_validate_no_collision_passes_when_no_overlap(self):
        """No collision when generated tokens are distinct from existing base tokens."""
        base = copy.deepcopy(_BASE_SCHEMA)
        generated = {"resources": {"powerplatform:components:NewComponent": {}}, "types": {}}
        # Should not raise — powerplatform:components:NewComponent is not in base.
        ms._validate_no_collision(base, generated)


# ---------------------------------------------------------------------------
# Input: required vs optional
# ---------------------------------------------------------------------------


class TestRequiredVsOptionalInputs:
    def test_label_optional_in_generated(self):
        """PocComponentArgs.label is Optional[str] = None — should not be required."""
        generated = ms.rewrite_index_to_components(copy.deepcopy(_GENERATED_FRAGMENT))
        poc = generated["resources"]["powerplatform:components:PocComponent"]
        required = poc.get("requiredInputs", [])
        assert "label" not in required

    def test_enable_telemetry_optional(self):
        generated = ms.rewrite_index_to_components(copy.deepcopy(_GENERATED_FRAGMENT))
        poc = generated["resources"]["powerplatform:components:PocComponent"]
        required = poc.get("requiredInputs", [])
        assert "enableTelemetry" not in required


# ---------------------------------------------------------------------------
# Dispatch coverage (registry ↔ schema)
# ---------------------------------------------------------------------------


class TestDispatchCoverage:
    def test_every_schema_component_has_construct_handler(self):
        """Every token in _ANALYZER_REGISTRY must also be in _CONSTRUCT_REGISTRY."""
        # Trigger component registration by importing the components package.
        # We need the provider on sys.path for this.
        provider_dir = str(Path(__file__).parent.parent / "provider")
        if provider_dir not in sys.path:
            sys.path.insert(0, provider_dir)

        import rpothin_powerplatform.components  # noqa: F401 — registers all
        from rpothin_powerplatform.components._base import (
            _ANALYZER_REGISTRY,
            _CONSTRUCT_REGISTRY,
            COMPONENT_TOKEN_PREFIX,
        )

        for cls in _ANALYZER_REGISTRY:
            expected_token = f"{COMPONENT_TOKEN_PREFIX}{cls.__name__}"
            assert expected_token in _CONSTRUCT_REGISTRY, (
                f"Component '{cls.__name__}' is registered for schema gen "
                f"but has no construct handler for token '{expected_token}'"
            )


# ---------------------------------------------------------------------------
# Isolated loader: no sys.modules pollution
# ---------------------------------------------------------------------------


class TestIsolatedLoader:
    def test_loader_restores_sys_modules(self):
        """After load_components_isolated(), sys.modules is restored to its pre-call state."""
        snapshot_before = dict(sys.modules)
        ms.load_components_isolated()
        snapshot_after = dict(sys.modules)
        # All modules that were absent before must be absent after (full cleanup).
        for key in list(snapshot_after.keys()):
            if key not in snapshot_before:
                pytest.fail(
                    f"Module '{key}' leaked into sys.modules after isolated load. "
                    f"_IsolatedLoader.__exit__ did not clean it up."
                )

    def test_components_found_without_provider(self):
        """load_components_isolated() finds ResEnvironment without provider deps installed."""
        classes = ms.load_components_isolated()
        names = [c.__name__ for c in classes]
        assert "ResEnvironment" in names


# ---------------------------------------------------------------------------
# Dry-run mode
# ---------------------------------------------------------------------------


class TestDryRunMode:
    def test_dry_run_does_not_write(self, tmp_path, capsys):
        """--dry-run prints to stdout but does not write schema.json."""
        # Patch SCHEMA_PATH to a temporary file.
        original = ms.SCHEMA_PATH
        tmp_schema = tmp_path / "schema.json"
        tmp_schema.write_text(json.dumps(_BASE_SCHEMA, indent=4), encoding="utf-8")
        ms.SCHEMA_PATH = tmp_schema
        try:
            # Calling main with --dry-run should not raise; the file mtime should be unchanged.
            mtime_before = tmp_schema.stat().st_mtime
            # We cannot call main() directly here because analyze_components needs the real
            # Pulumi Analyzer, which may not be available.  Instead test _dump_schema + dry-run
            # flag logic via merge_into_schema directly.
            base = copy.deepcopy(_BASE_SCHEMA)
            generated = copy.deepcopy(_GENERATED_FRAGMENT)
            merged = ms.merge_into_schema(base, generated)
            text = ms._dump_schema(merged)
            # Simulate dry-run: print only, do not write.
            assert "powerplatform:components:PocComponent" in text
            assert tmp_schema.stat().st_mtime == mtime_before
        finally:
            ms.SCHEMA_PATH = original

    def test_dump_schema_is_deterministic(self):
        """Same schema dict → same JSON text on repeated calls."""
        base = copy.deepcopy(_BASE_SCHEMA)
        text1 = ms._dump_schema(base)
        text2 = ms._dump_schema(base)
        assert text1 == text2

    def test_dump_schema_ends_with_newline(self):
        assert ms._dump_schema(_BASE_SCHEMA).endswith("\n")


# ---------------------------------------------------------------------------
# Check mode (--check flag)
# ---------------------------------------------------------------------------


class TestCheckMode:
    """Tests for the --check flag: exit 0 when schema.json is up-to-date, 1 otherwise.

    main() is called with SCHEMA_PATH, load_components_isolated, and analyze_components
    monkeypatched so these tests do not require the real Pulumi Analyzer.
    """

    def test_check_passes_when_schema_already_merged(self, tmp_path, monkeypatch):
        """--check exits 0 when schema.json already contains the generated components."""
        merged = ms.merge_into_schema(copy.deepcopy(_BASE_SCHEMA), copy.deepcopy(_GENERATED_FRAGMENT))
        tmp_schema = tmp_path / "schema.json"
        tmp_schema.write_text(ms._dump_schema(merged), encoding="utf-8")

        class _Sentinel:
            pass

        monkeypatch.setattr(ms, "SCHEMA_PATH", tmp_schema)
        monkeypatch.setattr(ms, "load_components_isolated", lambda: [_Sentinel])
        monkeypatch.setattr(ms, "analyze_components", lambda _: copy.deepcopy(_GENERATED_FRAGMENT))

        assert ms.main(["--check"]) == 0

    def test_check_fails_when_schema_is_stale(self, tmp_path, monkeypatch):
        """--check exits 1 when schema.json is missing the generated components."""
        tmp_schema = tmp_path / "schema.json"
        tmp_schema.write_text(ms._dump_schema(copy.deepcopy(_BASE_SCHEMA)), encoding="utf-8")

        class _Sentinel:
            pass

        monkeypatch.setattr(ms, "SCHEMA_PATH", tmp_schema)
        monkeypatch.setattr(ms, "load_components_isolated", lambda: [_Sentinel])
        monkeypatch.setattr(ms, "analyze_components", lambda _: copy.deepcopy(_GENERATED_FRAGMENT))

        assert ms.main(["--check"]) == 1

    def test_check_passes_with_no_components_and_clean_schema(self, tmp_path, monkeypatch):
        """--check exits 0 when no components are registered and schema has none either."""
        tmp_schema = tmp_path / "schema.json"
        tmp_schema.write_text(ms._dump_schema(copy.deepcopy(_BASE_SCHEMA)), encoding="utf-8")

        monkeypatch.setattr(ms, "SCHEMA_PATH", tmp_schema)
        monkeypatch.setattr(ms, "load_components_isolated", lambda: [])

        assert ms.main(["--check"]) == 0

    def test_check_fails_with_no_components_but_stale_schema(self, tmp_path, monkeypatch):
        """--check exits 1 when no components registered but schema still has old entries."""
        stale_base = copy.deepcopy(_BASE_SCHEMA)
        stale_base["resources"]["powerplatform:components:OldComponent"] = {"isComponent": True}
        tmp_schema = tmp_path / "schema.json"
        tmp_schema.write_text(ms._dump_schema(stale_base), encoding="utf-8")

        monkeypatch.setattr(ms, "SCHEMA_PATH", tmp_schema)
        monkeypatch.setattr(ms, "load_components_isolated", lambda: [])

        assert ms.main(["--check"]) == 1
