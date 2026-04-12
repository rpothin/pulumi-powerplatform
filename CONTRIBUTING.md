# Contributing to pulumi-powerplatform

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/rpothin/pulumi-powerplatform.git
cd pulumi-powerplatform

# Install in development mode with all dev dependencies
pip install -e ".[dev]"
```

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests are organized as:

- `test_<resource>.py` — check/diff validation for each resource handler
- `test_<resource>_crud.py` — create/read/update/delete with mocked SDK clients
- `test_get_<function>_invoke.py` — function/invoke tests with mocked SDK
- `test_provider.py` — schema validation tests

## Linting

```bash
ruff check provider/ tests/
```

## Project Structure

```
provider/pulumi_powerplatform/
├── provider.py              # Main provider (CRUD/invoke dispatch)
├── config.py                # Configuration resolution (args + env vars)
├── client.py                # SDK client factory (Azure Identity auth)
├── utils.py                 # Shared helpers (pv_str, etc.)
├── resources/               # Resource handlers (one file per resource)
│   ├── environment_group.py
│   ├── dlp_policy.py
│   └── ...
├── functions/               # Data source handlers (one file per function)
│   ├── get_environments.py
│   └── ...
└── raw_api/                 # Raw REST API for SDK gaps (see below)
    ├── __init__.py
    └── client.py
```

## Adding a New Resource

1. **Create the handler** in `provider/pulumi_powerplatform/resources/my_resource.py`:
   - Implement `check()`, `diff()`, `create()`, `read()`, `update()` (or subset), `delete()`
   - Use `from pulumi_powerplatform.utils import pv_str as _pv_str` for the shared helper
   - Follow the pattern of existing resources (e.g., `environment_group.py`)

2. **Register in `provider.py`**:
   - Add a type token constant (e.g., `_MY_RESOURCE = "powerplatform:index:MyResource"`)
   - Import the handler class
   - Initialize it in `configure()` and add to `_handler_for_type()`

3. **Add to `schema.json`**:
   - Define the resource under `resources` with `inputProperties`, `properties`, and `requiredInputs`

4. **Add an SDK class** in `sdk/python/pulumi_powerplatform/my_resource.py`:
   - Extend `pulumi.CustomResource`
   - Use `Optional[str] = None` for constructor parameters
   - Export from `__init__.py`

5. **Add an example** in `examples/my_resource/__main__.py`

6. **Add tests**:
   - `tests/test_my_resource.py` for check/diff
   - `tests/test_my_resource_crud.py` for create/read/update/delete with mocked SDK

## Handling SDK Gaps — The `raw_api/` Pattern

The `powerplatform-management` SDK does not cover all Power Platform REST APIs.
Known gaps include:

- **Environment creation** — not yet available in the SDK
- **Environment update** — properties and settings
- **Tenant Settings** — global tenant configuration
- **Solution Management** — solution import/export
- **Data Records** — Dataverse CRUD operations

For these cases, use the `raw_api/` module which provides direct HTTP access via
the Kiota `HttpxRequestAdapter`. This reuses the same authentication and transport
as the SDK:

```python
from pulumi_powerplatform.raw_api import RawApiClient

raw = RawApiClient(self._client.adapter)
result = await raw.request("GET", "/providers/Microsoft.BusinessAppPlatform/environments")
```

The `RawApiClient` is currently a scaffold — it will be fully implemented when the
first resource requires raw REST access (e.g., Environment creation).

## Known Limitations

- **DLP Policy delete**: The SDK does not expose a direct DELETE endpoint for
  rule-based policies. The provider works around this by deleting each rule set
  individually. A future version may use `raw_api/` for direct deletion.

- **Retry logic**: HTTP 429 and 5xx errors are retried automatically via
  `retry_with_backoff` in `utils.py`. Use it for all SDK/API calls in
  resource handlers.

## CI/CD

The GitHub Actions CI pipeline runs on every push and PR:

- **Lint**: `ruff check` on provider and test code
- **Test**: `pytest` across Python 3.10, 3.11, 3.12
- **Schema validation**: Structural checks on `schema.json`
