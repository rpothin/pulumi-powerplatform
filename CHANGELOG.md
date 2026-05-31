# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Added
- **Component Resources** (AVM-aligned multi-language Pulumi component resources):
  - `ResEnvironment` (`powerplatform:components:ResEnvironment`): composes `Environment`, `ManagedEnvironment`, `EnvironmentSettings`
  - `ResDlpPolicy` (`powerplatform:components:ResDlpPolicy`): composes `DlpPolicy`
  - `ResTenantSettings` (`powerplatform:components:ResTenantSettings`): composes `TenantSettings`
  - `ResDeploymentPipeline` (`powerplatform:components:ResDeploymentPipeline`): composes `DataRecord` instances for pipeline, stages, and team membership; links dev environment via `PipelineSharing`
- **New resources**: `DataRecord`, `TenantSettings`, `ManagedEnvironment`, `EnvironmentSettings`, `PipelineSharing`, `EnterprisePolicyLink`, `AdminManagementApplication`, `EnvironmentApplicationAdmin`
- **New functions**: `getDlpPolicies`, `getDlpPolicyMigrationConfig`, `getSecurityRoles`, `getDataRecords`
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
