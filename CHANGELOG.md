# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

## [0.4.1] — Backward-compatibility patch for v0.4.0

### Fixed

#### `EnvironmentDataverseArgs` backward-compatibility alias restored

`sdk/python/rpothin_powerplatform/_inputs.py` now re-exports
`EnvironmentDataverseArgs` and `EnvironmentDataverseArgsDict` as aliases for
`DataverseArgs` and `DataverseArgsDict` respectively.

Code that was using the pre-v0.4.0 name continues to work without any changes:

```python
# Still works in v0.4.1+
dataverse_block = pp.EnvironmentDataverseArgs(
    currency_code="USD",
    language_code=1033,
    ...
)
```

### Migration guide for `get_*` invoke functions (breaking change from v0.4.0)

The five `get_*` invoke functions (`get_environments`, `get_connectors`,
`get_apps`, `get_flows`, `get_data_records`) now return **typed result objects**
instead of plain dicts. This is standard Pulumi SDK behavior; property access
replaces subscript access:

| Function | Old pattern (broken since v0.4.0) | New pattern |
|---|---|---|
| `get_environments()` | `result["environments"]` | `result.environments` |
| `get_connectors()` | `result["connectors"]` | `result.connectors` |
| `get_apps()` | `result["apps"]` | `result.apps` |
| `get_flows()` | `result["flows"]` | `result.flows` |
| `get_data_records()` | `result.value["records"]` | `result.records` |

Example migration:

```python
# Before (v0.3.x / hand-maintained SDK)
result = await get_environments()
envs = result["environments"]

# After (v0.4.0+ / generated SDK)
result = await get_environments()
envs = result.environments
```

For `get_data_records`, the `.value` wrapper no longer exists:

```python
# Before
result = await get_data_records(environment_id=..., entity_collection=...)
records = result.value["records"]

# After
result = await get_data_records(environment_id=..., entity_collection=...)
records = result.records
```

---

## [Unreleased — v0.4.0 changes]

### Added
- **Component Resources** (AVM-aligned multi-language Pulumi component resources):
  - `ResEnvironment` (`powerplatform:components:ResEnvironment`): composes `Environment`, `ManagedEnvironment`, `EnvironmentSettings`
  - `ResDlpPolicy` (`powerplatform:components:ResDlpPolicy`): composes `DlpPolicy`
  - `ResTenantSettings` (`powerplatform:components:ResTenantSettings`): composes `TenantSettings`
  - `ResDeploymentPipeline` (`powerplatform:components:ResDeploymentPipeline`): composes `DataRecord` instances for pipeline, stages, and team membership; links dev environment via `PipelineSharing`
- **New resources**: `DataRecord`, `TenantSettings`, `ManagedEnvironment`, `EnvironmentSettings`, `PipelineSharing`, `EnterprisePolicyLink`, `AdminManagementApplication`, `EnvironmentApplicationAdmin`
- **New functions**: `getDlpPolicies`, `getDlpPolicyMigrationConfig`, `getSecurityRoles`
- Component resource examples in `examples/components/`
- Schema merge tooling (`scripts/merge_schema.py`) for embedding component schemas into the provider schema

### Removed
- `PocComponent` proof-of-concept scaffold (replaced by real component implementations)

### Breaking Changes

#### Python SDK now schema-generated (Phase 1 — Option G)

The `sdk/python/` package is now fully generated from `schema.json` by
`pulumi package gen-sdk` and must not be edited by hand. Regenerate it with
`bash scripts/regen-sdks.sh` after any `schema.json` change.

**Renamed types** — the generated SDK uses shorter, module-qualified names:

| Before (hand-maintained) | After (generated) | Location |
|---|---|---|
| `rpothin_powerplatform.environment.EnvironmentDataverse` | `rpothin_powerplatform.outputs.Dataverse` | `outputs.py` |
| `rpothin_powerplatform.environment.EnvironmentDataverseArgs` | `rpothin_powerplatform._inputs.DataverseArgs` | `_inputs.py` |

Migration in existing code:

```python
# Before
from rpothin_powerplatform.environment import EnvironmentDataverse, EnvironmentDataverseArgs

# After
from rpothin_powerplatform.outputs import Dataverse as EnvironmentDataverse
from rpothin_powerplatform._inputs import DataverseArgs as EnvironmentDataverseArgs
```

**`ProviderArgs` no longer accepts constructor arguments** — the old
hand-maintained SDK had `tenant_id`, `client_id`, and `client_secret` as
constructor parameters on `ProviderArgs`. This was inconsistent with how Pulumi
providers work: credentials are always resolved via Pulumi config keys (or
environment variables), not via SDK constructor arguments. The generated
`ProviderArgs` class is now empty (no constructor args). Provider credentials are
accessed as module-level properties via the `config` sub-package:

```python
import rpothin_powerplatform as pp

# Access provider config values (read-only, from pulumi config or env vars)
print(pp.config.client_id)
print(pp.config.tenant_id)
```

**New runtime dependencies** — the generated `_utilities.py` requires `parver`
and `semver` at import time. These packages are declared in the root
`pyproject.toml` dev extras and are installed automatically when running
`pip install -e ".[dev]"` for development and testing.
