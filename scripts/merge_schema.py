#!/usr/bin/env python3
"""Schema surgery: merge Pulumi Analyzer-generated component definitions into schema.json.

Usage:
    python scripts/merge_schema.py [--dry-run] [--check]

Options:
    --dry-run   Print the merged schema to stdout without writing schema.json.
    --check     Exit with code 1 if schema.json would change (for CI validation).

Design notes:
    - Components are loaded in **isolation** so that importing the provider package
      (which requires mspp_management at runtime) does not block this script.
    - Token rewriting: Pulumi Analyzer always generates tokens as
      ``{pkg}:index:{Name}``.  We rewrite them to ``{pkg}:components:{Name}`` before
      merging.
    - Idempotency: existing ``powerplatform:components:*`` entries are removed before
      the new ones are merged in.  The components namespace is reserved exclusively
      for this script; any unexpected entry causes a loud failure.
    - Collision detection: if any generated token already exists under a *non-components*
      namespace in schema.json, the script fails.
    - Protected top-level keys are never overwritten.
    - Registry consistency: every component registered for schema gen must also have a
      runtime construct handler; drift between the two is caught at merge time.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.resolve()
SCHEMA_PATH = REPO_ROOT / "schema.json"
COMPONENTS_DIR = REPO_ROOT / "provider" / "rpothin_powerplatform" / "components"
PROVIDER_PKG = "rpothin_powerplatform"
PROVIDER_DIR = REPO_ROOT / "provider"

#: Pulumi package name as it appears in schema.json token namespace (e.g. ``"powerplatform:index:..."``).
#: Distinct from the Python module name (``rpothin_powerplatform``).
PULUMI_PKG_NAME = "powerplatform"

# ---------------------------------------------------------------------------
# Protected top-level schema keys that must NEVER be overwritten
# ---------------------------------------------------------------------------

PROTECTED_KEYS = {"language", "config", "functions", "version", "dependencies", "pluginDownloadURL"}

# External $ref values that are intentionally not resolved locally
EXTERNAL_REFS = {"pulumi.json#/Any", "pulumi.json#/Archive", "pulumi.json#/Asset"}

#: Namespace produced by Pulumi Analyzer / generate_schema (always uses Pulumi pkg name)
INDEX_NS = f"{PULUMI_PKG_NAME}:index:"

#: Namespace we force components into
COMPONENT_NS = f"{PULUMI_PKG_NAME}:components:"


# ---------------------------------------------------------------------------
# Isolated component loader
# ---------------------------------------------------------------------------

class _IsolatedLoader:
    """Context manager that loads component modules without importing the full provider.

    On enter, it takes a full snapshot of ``sys.modules`` and injects stubs for
    modules that would cause import-time side effects (mspp_management SDK, the
    provider itself).  On exit it restores ``sys.modules`` exactly to the snapshot
    state, removing any modules that were injected during the context window.
    """

    #: Top-level modules to stub so that isolated component loads do not fail.
    _STUBS: list[str] = [
        "mspp_management",
        "rpothin_powerplatform",
        "rpothin_powerplatform.config",
        "rpothin_powerplatform.client",
        "rpothin_powerplatform.provider",
        "rpothin_powerplatform.utils",
        "rpothin_powerplatform.functions",
        "rpothin_powerplatform.functions.get_apps",
    ]

    def __enter__(self) -> "_IsolatedLoader":
        # Full snapshot — guarantees both new keys and modified values are restored.
        self._snapshot: dict[str, object] = dict(sys.modules)
        for name in self._STUBS:
            if name not in sys.modules:
                sys.modules[name] = types.ModuleType(name)
        return self

    def __exit__(self, *args: object) -> None:
        # Remove any module injected during the context window.
        for key in list(sys.modules.keys()):
            if key not in self._snapshot:
                del sys.modules[key]
        # Restore any module that was present before and may have been replaced.
        for key, value in self._snapshot.items():
            sys.modules[key] = value  # type: ignore[assignment]

    def load_module(self, module_name: str, file_path: Path) -> types.ModuleType:
        """Load a module by file path, registering it in sys.modules."""
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod


def load_components_isolated() -> list[type]:
    """Load all component modules in isolation and return registered component classes.

    Only modules whose name does NOT start with ``_`` are loaded (``_base.py`` and
    ``__init__.py`` are handled internally).
    """
    with _IsolatedLoader() as loader:
        # Ensure provider package stub exists so relative imports in component modules work.
        pkg_stub = types.ModuleType(PROVIDER_PKG)
        pkg_stub.__path__ = [str(PROVIDER_DIR / PROVIDER_PKG)]  # type: ignore[assignment]
        pkg_stub.__package__ = PROVIDER_PKG
        sys.modules[PROVIDER_PKG] = pkg_stub

        # Load _base first so registries exist before component modules run.
        components_pkg_name = f"{PROVIDER_PKG}.components"
        components_pkg = types.ModuleType(components_pkg_name)
        components_pkg.__path__ = [str(COMPONENTS_DIR)]  # type: ignore[assignment]
        components_pkg.__package__ = components_pkg_name
        sys.modules[components_pkg_name] = components_pkg

        base_mod = loader.load_module(
            f"{components_pkg_name}._base",
            COMPONENTS_DIR / "_base.py",
        )
        # Expose _base as attribute of the components package (mirrors normal import).
        components_pkg._base = base_mod  # type: ignore[attr-defined]

        # Stub construct_bridge so lazy imports in component factories don't fail at load.
        bridge_stub = types.ModuleType(f"{PROVIDER_PKG}.construct_bridge")
        sys.modules[f"{PROVIDER_PKG}.construct_bridge"] = bridge_stub

        # Discover and load all non-private component modules.
        for py_file in sorted(COMPONENTS_DIR.glob("*.py")):
            stem = py_file.stem
            if stem.startswith("_"):
                continue
            mod_name = f"{components_pkg_name}.{stem}"
            mod = loader.load_module(mod_name, py_file)
            setattr(components_pkg, stem, mod)

        # Extract registries — must be captured inside context manager.
        analyzer_registry: list[type] = list(base_mod._ANALYZER_REGISTRY)
        construct_registry: dict = dict(base_mod._CONSTRUCT_REGISTRY)

    # Consistency check: every component registered for schema gen must have a
    # runtime construct handler.  Use the prefix from the loaded _base module so
    # this check is always in sync with COMPONENT_TOKEN_PREFIX in _base.py.
    component_prefix: str = base_mod.COMPONENT_TOKEN_PREFIX
    for cls in analyzer_registry:
        expected_token = f"{component_prefix}{cls.__name__}"
        if expected_token not in construct_registry:
            raise SystemExit(
                f"Registry drift: '{cls.__name__}' is registered for schema generation "
                f"but has no construct handler for token '{expected_token}'. "
                f"Add @register_construct('{expected_token}') to a factory function "
                f"in {COMPONENTS_DIR / (cls.__name__.lower() + '.py')}"
            )

    return analyzer_registry


# ---------------------------------------------------------------------------
# Schema analysis + generation
# ---------------------------------------------------------------------------

def analyze_components(component_classes: list[type]) -> dict:
    """Run Pulumi Analyzer on component classes and return the raw schema dict.

    Requires ``pulumi.provider.experimental.analyzer`` (shipped with Pulumi Python SDK ≥ 3.x).
    Returns the ``PackageSpec``-shaped dict with ``resources`` and ``types`` keys.
    """
    try:
        from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]
    except ImportError as exc:
        raise SystemExit(
            "Cannot import pulumi.provider.experimental.analyzer — "
            "ensure you have pulumi>=3.x installed.\n" + str(exc)
        ) from exc

    # generate_schema was moved between Pulumi SDK versions; try both paths.
    try:
        from pulumi.provider.experimental.schema import generate_schema  # type: ignore[import]
    except ImportError:
        try:
            from pulumi.provider.experimental import generate_schema  # type: ignore[import]
        except ImportError as exc:
            raise SystemExit(
                "Cannot import generate_schema from pulumi.provider.experimental — "
                "ensure you have pulumi>=3.x installed.\n" + str(exc)
            ) from exc

    analyzer = Analyzer(PULUMI_PKG_NAME)
    result = analyzer.analyze(component_classes)

    pkg_spec = generate_schema(
        name=PULUMI_PKG_NAME,
        version="",
        namespace=PULUMI_PKG_NAME,
        components=result["component_definitions"],
        type_definitions=result["type_definitions"],
        dependencies=result.get("dependencies", {}),
    )
    return pkg_spec.to_json()


# ---------------------------------------------------------------------------
# Token rewriting
# ---------------------------------------------------------------------------

def _rewrite_value(value: object) -> object:
    """Recursively rewrite ``{pkg}:index:`` to ``{pkg}:components:`` in a JSON value."""
    if isinstance(value, str):
        return value.replace(INDEX_NS, COMPONENT_NS)
    if isinstance(value, dict):
        return {_rewrite_value(k): _rewrite_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_rewrite_value(item) for item in value]
    return value


def rewrite_index_to_components(schema_fragment: dict) -> dict:
    """Rewrite all ``{pkg}:index:*`` tokens to ``{pkg}:components:*`` in a schema fragment."""
    return _rewrite_value(schema_fragment)  # type: ignore[return-value]


def _drop_plain_on_ref_collections(value: object) -> object:
    """Drop ``plain`` from ``items``/``additionalProperties`` that carry ``$ref``.

    Pulumi's Go SDK generator can emit references to ``*Args`` helper types for
    object refs nested inside arrays/maps while omitting the helper type
    definitions when these nested schemas are marked ``plain``.  Removing the
    nested ``plain`` markers preserves scalar ``plain`` usage while producing
    valid generated Go SDKs.
    """
    if isinstance(value, dict):
        cleaned = {k: _drop_plain_on_ref_collections(v) for k, v in value.items()}
        for collection_key in ("items", "additionalProperties"):
            collection = cleaned.get(collection_key)
            if isinstance(collection, dict) and "$ref" in collection:
                collection.pop("plain", None)
        return cleaned
    if isinstance(value, list):
        return [_drop_plain_on_ref_collections(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def _strip_existing_components(base: dict) -> dict:
    """Remove all existing ``powerplatform:components:*`` entries from base schema.

    Returns the stripped schema.  Raises if an unexpected (hand-authored) entry is
    found in the ``components`` namespace — that namespace is reserved for generated
    components only.
    """
    for section in ("resources", "types"):
        section_dict = base.get(section, {})
        keys_to_remove = [k for k in section_dict if k.startswith(COMPONENT_NS)]
        for key in keys_to_remove:
            del section_dict[key]
    return base


def _validate_no_collision(base: dict, generated: dict) -> None:
    """Fail loudly if any generated token collides with an existing non-component entry."""
    for section in ("resources", "types"):
        base_section = base.get(section, {})
        gen_section = generated.get(section, {})
        for token in gen_section:
            if token in base_section:
                raise SystemExit(
                    f"Token collision: '{token}' already exists in schema.json "
                    f"under '{section}' as a non-component entry.  Aborting."
                )


def _collect_all_refs(obj: object) -> set[str]:
    """Recursively collect all ``$ref`` string values from a JSON-like structure."""
    refs: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                refs.add(v)
            else:
                refs |= _collect_all_refs(v)
    elif isinstance(obj, list):
        for item in obj:
            refs |= _collect_all_refs(item)
    return refs


def _validate_refs(merged: dict) -> None:
    """Check that every ``$ref`` in the components section resolves locally.

    ``pulumi.json#/...`` refs are external and are always accepted.
    """
    resources = merged.get("resources", {})
    types_ = merged.get("types", {})

    # Only validate refs that originate from component entries.
    component_entries: dict = {}
    for token, defn in resources.items():
        if token.startswith(COMPONENT_NS):
            component_entries[token] = defn
    for token, defn in types_.items():
        if token.startswith(COMPONENT_NS):
            component_entries[token] = defn

    all_types = set(types_.keys())
    all_resources = set(resources.keys())
    known_tokens = all_types | all_resources

    for ref in _collect_all_refs(component_entries):
        if ref.startswith("pulumi.json#"):
            continue
        # Local $ref format: "#/types/{token}" or "#/resources/{token}"
        match = re.fullmatch(r"#/(types|resources)/(.+)", ref)
        if match is None:
            raise SystemExit(f"Unrecognised $ref format in component schema: '{ref}'")
        token = match.group(2)
        if token not in known_tokens:
            raise SystemExit(
                f"$ref '{ref}' in component schema references missing token '{token}'"
            )


def merge_into_schema(base: dict, generated: dict) -> dict:
    """Merge rewritten component definitions into the base schema.

    Steps:
    1. Strip any existing ``powerplatform:components:*`` entries (idempotency).
    2. Detect collisions with non-component entries.
    3. Merge ``resources`` and ``types``.
    4. Validate all $refs.
    5. Never overwrite PROTECTED_KEYS.
    """
    import copy

    base = copy.deepcopy(base)
    generated = _drop_plain_on_ref_collections(rewrite_index_to_components(generated))

    base = _strip_existing_components(base)
    _validate_no_collision(base, generated)

    for section in ("resources", "types"):
        if section in generated:
            base.setdefault(section, {}).update(generated[section])

    _validate_refs(base)
    return base


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _dump_schema(schema: dict) -> str:
    return json.dumps(schema, indent=4, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print result; do not write file.")
    parser.add_argument("--check", action="store_true", help="Exit 1 if schema.json would change.")
    args = parser.parse_args(argv)

    # Add provider dir to sys.path so absolute imports work inside component modules.
    provider_path = str(PROVIDER_DIR)
    if provider_path not in sys.path:
        sys.path.insert(0, provider_path)

    # Pre-warm the Pulumi Analyzer BEFORE _IsolatedLoader runs its snapshot/restore cycle.
    # The restore in _IsolatedLoader.__exit__ can corrupt typing module identity so that
    # get_origin(Optional[T]) == Union returns False if the Analyzer (which imports private
    # typing internals like _GenericAlias) is first imported AFTER the restore.  Importing
    # it here ensures its typing references are established before any module snapshot is taken.
    try:
        import pulumi.provider.experimental.analyzer as _  # noqa: F401, PLC0415
    except ImportError:
        pass  # Error will surface with a friendly message inside analyze_components.

    print("Loading components in isolation…", file=sys.stderr)
    component_classes = load_components_isolated()
    if not component_classes:
        print("No components registered — stripping any stale component entries.", file=sys.stderr)
        generated: dict = {"resources": {}, "types": {}}
    else:
        print(f"  Found {len(component_classes)} component(s): "
              f"{[c.__name__ for c in component_classes]}", file=sys.stderr)
        print("Analyzing component schema…", file=sys.stderr)
        generated = analyze_components(component_classes)

    print("Loading schema.json…", file=sys.stderr)
    base = _load_schema()

    # Protect top-level keys.
    for key in PROTECTED_KEYS:
        if key in generated and key in base and generated[key] != base[key]:
            print(
                f"  WARNING: generated schema has conflicting '{key}'; ignoring generated value.",
                file=sys.stderr,
            )

    print("Merging…", file=sys.stderr)
    merged = merge_into_schema(base, generated)
    merged_text = _dump_schema(merged)

    if args.dry_run:
        print(merged_text)
        return 0

    if args.check:
        original_text = _dump_schema(base)
        if merged_text != original_text:
            print("schema.json WOULD change — re-run merge-schema.py.", file=sys.stderr)
            return 1
        print("schema.json is up-to-date.", file=sys.stderr)
        return 0

    print(f"Writing {SCHEMA_PATH}…", file=sys.stderr)
    SCHEMA_PATH.write_text(merged_text, encoding="utf-8")
    print("Done.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
