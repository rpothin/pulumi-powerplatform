"""Pytest configuration — stubs out SDK sub-packages unavailable in environments
that lack Windows Long Path support (mspp_management sub-packages cannot be
installed there).  Has no effect when the real packages are present.

Also extends rpothin_powerplatform.__path__ to expose the hand-crafted Python SDK
modules (sdk/python/rpothin_powerplatform/) alongside the provider modules."""

from __future__ import annotations

import sys
from importlib.abc import Loader, MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path
from unittest.mock import MagicMock


class _StubLoader(Loader):
    """Returns a MagicMock module for any module it is asked to load."""

    def create_module(self, spec: ModuleSpec):  # type: ignore[override]
        # Use MagicMock without spec so attribute access is unrestricted
        # (e.g. enum values like BillingPolicyStatus.Enabled resolve fine)
        mod = MagicMock()
        mod.__name__ = spec.name
        mod.__package__ = spec.name.rsplit(".", 1)[0] if "." in spec.name else spec.name
        mod.__spec__ = spec
        mod.__path__ = []  # mark as package so sub-imports work
        mod.__file__ = None
        return mod

    def exec_module(self, module):  # type: ignore[override]
        pass  # MagicMock handles all attribute access


class _SdkStubFinder(MetaPathFinder):
    """Intercepts imports of mspp_management sub-packages that are not installed."""

    _STUB_PREFIXES = ("mspp_management.",)

    def find_spec(self, fullname: str, path, target=None):
        if not any(fullname.startswith(p) for p in self._STUB_PREFIXES):
            return None
        # Only stub if the module is not already in sys.modules
        if fullname in sys.modules:
            return None
        loader = _StubLoader()
        spec = ModuleSpec(fullname, loader, is_package=True)
        return spec


# Register early so it applies during collection
sys.meta_path.insert(0, _SdkStubFinder())

# Import the provider package now (with stubs active) so we can extend its __path__
# to also include the hand-crafted Python SDK modules.
import rpothin_powerplatform as _provider_pkg  # noqa: E402

_sdk_pkg_dir = str(Path(__file__).parent.parent / "sdk" / "python" / "rpothin_powerplatform")
if _sdk_pkg_dir not in _provider_pkg.__path__:
    _provider_pkg.__path__.append(_sdk_pkg_dir)
