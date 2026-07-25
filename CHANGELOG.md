# Changelog

All notable changes to this project are documented in this file.

## [Unreleased]

### Fixed

#### AVM components (`ResEnvironment`, `ResDlpPolicy`, `ResTenantSettings`, `ResDeploymentPipeline`): child-resource CRUD dispatch failed with `NotImplementedError`

`PowerPlatformProvider._handler_for_type()` did an exact dict lookup against
plain resource-type tokens (e.g. `powerplatform:index:Environment`). This
works for top-level custom resources, but the four AVM components run their
entire `construct()` server-side and internally instantiate plain child
custom resources (e.g. `Environment`, `DlpPolicy`, `TenantSettings`,
`DataRecord`, `PipelineSharing`). When the engine round-trips those children
back into the same provider process for Check/Diff/Create/Read/Update/Delete,
it reports a composite, `$`-joined qualified type —
`ParentComponentToken$ChildResourceToken` (e.g.
`powerplatform:components:ResEnvironment$powerplatform:index:Environment`) —
instead of the plain child token, because `CreateRequest.type` (and its
Check/Diff/Read/Update siblings) derive from the request URN via Pulumi's
`_extract_type()` helper, which — unlike `pulumi.urn._parse_urn` — does not
strip the qualified-type prefix. The dict lookup on that composite string
always missed, so `create()`/`update()`/`delete()` raised
`NotImplementedError(f"... not implemented for resource type: {request.type}")`
immediately on every `pulumi preview`/`pulumi up`, breaking all four
components in every language SDK.

`_handler_for_type()` now normalizes the incoming type by taking the last
`$`-delimited segment (`resource_type.rsplit("$", 1)[-1]`) before doing the
lookup — mirroring the same convention Pulumi's own SDK uses in
`pulumi.urn._parse_urn`. Since `check`, `diff`, `create`, `read`, `update`,
and `delete` all route through `_handler_for_type()`, this single fix
restores correct dispatch across the board for both plain and composite
tokens.

Discovered via live end-to-end component tests in the separate
[`rpothin/pulumi-powerplatform-test`](https://github.com/rpothin/pulumi-powerplatform-test)
harness repo
([CI run 30140749814](https://github.com/rpothin/pulumi-powerplatform-test/actions/runs/30140749814)),
which failed identically across the Python, TypeScript, Go, .NET, and Java
SDK matrix jobs for `ResEnvironment` and `ResDlpPolicy` — a systemic,
100%-reproducible bug affecting v0.4.0/v0.4.1 and current `main`, not a
flaky or environment-specific failure.

### Added

#### Node.js SDK: `./components` subpath export

`sdk/nodejs/package.json` now declares an `exports` map so the component
resources can be imported directly from a `components` subpath, in addition
to the existing full-package import:

```ts
// New: deep import
import { ResEnvironment } from "@rpothin/powerplatform/components";

// Still works: full-package import
import * as pp from "@rpothin/powerplatform";
pp.components.ResEnvironment;
```

This is purely additive — the `main`/`types` root entry points are
unchanged, so existing imports of `@rpothin/powerplatform` continue to work
without modification.

> [!NOTE]
> `scripts/normalize-nodejs-sdk.py` now injects this `exports` field into the
> generated `sdk/nodejs/package.json` alongside the existing `main`/`types`/
> `files` fields, so it survives future SDK regeneration.

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
