"""Structural smoke tests for the generated Python SDK.

Architecture note — conftest.py path-stitching:
  PYTHONPATH=provider makes rpothin_powerplatform load from provider/.
  conftest.py then appends sdk/python/rpothin_powerplatform/ to __path__.

  As a result:
    UNIQUE to SDK   (_inputs.py, outputs.py, _utilities.py, config/)
                    → resolve to sdk/python/
    IN BOTH         (provider.py, config.py, environment.py, ...)
                    → SHADOWED: provider/ wins (appears first in __path__)

  Shadowing is intentional — provider code runs during tests; generated SDK
  client classes that share names with provider files are validated here via
  isolated imports rather than through the stitched namespace.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import Set

import pytest

SDK_DIR = Path(__file__).parent.parent / "sdk" / "python" / "rpothin_powerplatform"
PROVIDER_DIR = Path(__file__).parent.parent / "provider" / "rpothin_powerplatform"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_sdk_module_isolated(relative_path: str):
    """Load a single SDK source file under a synthetic private module name.

    Sets __package__ = 'rpothin_powerplatform' so relative imports like
    'from . import _utilities' resolve against the conftest-stitched package
    (where _utilities.py has already been loaded from sdk/python/).

    The module is NOT inserted into sys.modules under any importable name,
    preventing shadowing of either the provider version or the real SDK module.
    """
    sdk_file = SDK_DIR / relative_path
    _NAME = "__sdk_smoke_isolated__"
    spec = importlib.util.spec_from_file_location(_NAME, sdk_file)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    mod.__package__ = "rpothin_powerplatform"
    sys.modules[_NAME] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        sys.modules.pop(_NAME, None)
    return mod


def _ast_class_names(path: Path) -> Set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}


def _ast_property_method_names(class_node: ast.ClassDef) -> Set[str]:
    """Return names of methods in *class_node* decorated with @property
    (or @_builtins.property as emitted by the Pulumi generator)."""
    result: Set[str] = set()
    for node in ast.walk(class_node):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id == "property":
                result.add(node.name)
                break
            if isinstance(dec, ast.Attribute) and dec.attr == "property":
                result.add(node.name)
                break
    return result


# ---------------------------------------------------------------------------
# 1. Module resolution — SDK-unique files must come from sdk/python/
# ---------------------------------------------------------------------------

class TestSdkModuleResolution:
    """Verify SDK-unique files resolve to sdk/python/ via path-stitching."""

    def test_inputs_resolves_to_sdk(self):
        import rpothin_powerplatform._inputs as m
        assert Path(m.__file__).resolve().is_relative_to(SDK_DIR.resolve())

    def test_outputs_resolves_to_sdk(self):
        import rpothin_powerplatform.outputs as m
        assert Path(m.__file__).resolve().is_relative_to(SDK_DIR.resolve())

    def test_utilities_resolves_to_sdk(self):
        import rpothin_powerplatform._utilities as m
        assert Path(m.__file__).resolve().is_relative_to(SDK_DIR.resolve())


# ---------------------------------------------------------------------------
# 2. File completeness — all expected SDK artifacts must be present on disk
# ---------------------------------------------------------------------------

class TestSdkFileCompleteness:
    """Generated SDK must ship all required files."""

    def test_config_package_exists(self):
        assert (SDK_DIR / "config" / "__init__.py").exists()
        assert (SDK_DIR / "config" / "vars.py").exists()

    def test_utilities_file_exists(self):
        assert (SDK_DIR / "_utilities.py").exists()

    def test_pulumi_plugin_json_exists(self):
        assert (SDK_DIR / "pulumi-plugin.json").exists()

    def test_py_typed_exists(self):
        assert (SDK_DIR / "py.typed").exists()

    def test_inputs_file_exists(self):
        assert (SDK_DIR / "_inputs.py").exists()

    def test_outputs_file_exists(self):
        assert (SDK_DIR / "outputs.py").exists()


# ---------------------------------------------------------------------------
# 3. SDK config structure (AST) — config/vars.py must expose credentials
# ---------------------------------------------------------------------------

class TestSdkConfigStructure:
    """SDK config/vars.py must expose client_id, client_secret, tenant_id as
    @property methods on _ExportableConfig.

    Tested via AST rather than import because the property implementations call
    pulumi.Config('powerplatform') which requires a live Pulumi stack context.
    """

    @pytest.fixture(scope="class")
    def exportable_class(self):
        tree = ast.parse((SDK_DIR / "config" / "vars.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_ExportableConfig":
                return node
        pytest.fail("_ExportableConfig not found in sdk/python/.../config/vars.py")

    def test_has_client_id_property(self, exportable_class):
        assert "client_id" in _ast_property_method_names(exportable_class)

    def test_has_client_secret_property(self, exportable_class):
        assert "client_secret" in _ast_property_method_names(exportable_class)

    def test_has_tenant_id_property(self, exportable_class):
        assert "tenant_id" in _ast_property_method_names(exportable_class)

    def test_config_init_wires_exportable_class(self):
        """config/__init__.py must replace the module's class with _ExportableConfig
        so that module-level attribute access works (sdk/python pattern)."""
        src = (SDK_DIR / "config" / "__init__.py").read_text(encoding="utf-8")
        assert "_ExportableConfig" in src
        assert "sys.modules[__name__].__class__" in src


# ---------------------------------------------------------------------------
# 4. Isolated import — shadowed SDK modules (provider.py) must be importable
# ---------------------------------------------------------------------------

class TestSdkProviderIsolated:
    """The generated SDK provider.py must import cleanly and export ProviderArgs
    and Provider.  Loaded in isolation to bypass the path-shadowing that makes
    rpothin_powerplatform.provider resolve to the provider runtime module in tests.
    """

    @pytest.fixture(scope="class")
    def sdk_provider_mod(self):
        return _load_sdk_module_isolated("provider.py")

    def test_provider_args_exists(self, sdk_provider_mod):
        assert hasattr(sdk_provider_mod, "ProviderArgs")

    def test_provider_class_exists(self, sdk_provider_mod):
        assert hasattr(sdk_provider_mod, "Provider")

    def test_provider_args_takes_no_credentials(self, sdk_provider_mod):
        """ProviderArgs must not accept tenant_id/client_id/client_secret as args.
        See CHANGELOG.md — this was a breaking change from the hand-maintained SDK.
        """
        import inspect
        sig = inspect.signature(sdk_provider_mod.ProviderArgs.__init__)
        params = {p for p in sig.parameters if p != "self"}
        assert "tenant_id" not in params
        assert "client_id" not in params
        assert "client_secret" not in params


# ---------------------------------------------------------------------------
# 5. Key symbols in SDK-unique files
# ---------------------------------------------------------------------------

class TestSdkInputsStructure:
    """_inputs.py must contain DataverseArgs (the generated name)."""

    def test_has_dataverse_args(self):
        assert "DataverseArgs" in _ast_class_names(SDK_DIR / "_inputs.py")


class TestSdkOutputsStructure:
    """outputs.py must contain Dataverse (the generated name)."""

    def test_has_dataverse(self):
        assert "Dataverse" in _ast_class_names(SDK_DIR / "outputs.py")


# ---------------------------------------------------------------------------
# 6. Shadowing — document and pin the expected resolution order
# ---------------------------------------------------------------------------

class TestSdkShadowing:
    """Confirm that known module shadowing (provider/ wins over sdk/python/) is
    stable and intentional.  These tests guard against accidental resolution
    changes; they do NOT indicate bugs in the SDK.

    In a real user installation only sdk/python/ is installed, so
    rpothin_powerplatform.config → the generated config/ package, and
    rpothin_powerplatform.provider → the generated Provider/ProviderArgs.
    """

    def test_config_shadowed_by_provider(self):
        """rpothin_powerplatform.config resolves to provider/config.py in tests."""
        import rpothin_powerplatform.config as cfg
        assert Path(cfg.__file__).resolve().is_relative_to(PROVIDER_DIR.resolve()), (
            "Expected provider/config.py to shadow SDK config/ package. "
            "If this changed, update the smoke test and verify the SDK config "
            "interface is still exercised by TestSdkConfigStructure."
        )

    def test_provider_shadowed_by_provider(self):
        """rpothin_powerplatform.provider resolves to provider/provider.py in tests."""
        import rpothin_powerplatform.provider as pmod
        assert Path(pmod.__file__).resolve().is_relative_to(PROVIDER_DIR.resolve()), (
            "Expected provider/provider.py to shadow generated SDK provider.py. "
            "If this changed, update the smoke test and verify TestSdkProviderIsolated "
            "still covers the generated module."
        )
