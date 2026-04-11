# pulumi-powerplatform

Community led Pulumi custom provider for Power Platform based on the [Microsoft Power Platform Management Python SDK](https://pypi.org/project/powerplatform-management/).

## Overview

This provider enables managing Microsoft Power Platform resources using [Pulumi](https://www.pulumi.com/) Infrastructure-as-Code. It is built as a native Python Pulumi provider using the **experimental provider framework** (`pulumi.provider.experimental.Provider`), which provides full async CRUD lifecycle support.

### Architecture

- **Provider Framework**: Pulumi Experimental Provider (gRPC-based, async, distributable)
- **Backend SDK**: [`powerplatform-management`](https://pypi.org/project/powerplatform-management/) (Microsoft Kiota-generated, async)
- **Authentication**: Azure Identity (`azure-identity`) supporting client secret, managed identity, Azure CLI, and more

## Resources

| Resource | Type Token | Status | Notes |
|----------|-----------|--------|-------|
| Environment Group | `powerplatform:index:EnvironmentGroup` | ✅ Full CRUD | |
| DLP Policy | `powerplatform:index:DlpPolicy` | ✅ Full CRUD | Delete removes rule sets individually (see [Known Limitations](#known-limitations)) |
| Billing Policy | `powerplatform:index:BillingPolicy` | ✅ Full CRUD | |
| Managed Environment | `powerplatform:index:ManagedEnvironment` | ✅ Enable/Disable | |
| Environment Backup | `powerplatform:index:EnvironmentBackup` | ✅ Create/Read/Delete | |
| Role Assignment | `powerplatform:index:RoleAssignment` | ✅ Create/Read/Delete | |
| ISV Contract | `powerplatform:index:IsvContract` | ✅ Full CRUD | `geo` is immutable after creation |

## Data Sources (Functions)

| Function | Token | Status |
|----------|-------|--------|
| Get Environments | `powerplatform:index:getEnvironments` | ✅ Available |
| Get Connectors | `powerplatform:index:getConnectors` | ✅ Available |
| Get Apps | `powerplatform:index:getApps` | ✅ Available |
| Get Flows | `powerplatform:index:getFlows` | ✅ Available |

## Prerequisites

- Python 3.10+
- [Pulumi CLI](https://www.pulumi.com/docs/install/) v3+
- An Azure AD application with Power Platform API permissions, or access via Azure CLI / Managed Identity

## Installation

```bash
pip install pulumi-powerplatform
```

## Configuration

The provider supports the following configuration variables:

| Variable | Environment Variable | Description |
|----------|---------------------|-------------|
| `powerplatform:tenantId` | `AZURE_TENANT_ID` | Azure AD Tenant ID |
| `powerplatform:clientId` | `AZURE_CLIENT_ID` | Azure AD Application (Client) ID |
| `powerplatform:clientSecret` | `AZURE_CLIENT_SECRET` | Azure AD Client Secret |

If no explicit credentials are provided, the provider falls back to `DefaultAzureCredential` which tries managed identity, Azure CLI, environment variables, and more.

### Setting configuration

```bash
pulumi config set powerplatform:tenantId <your-tenant-id>
pulumi config set powerplatform:clientId <your-client-id>
pulumi config set powerplatform:clientSecret <your-secret> --secret
```

## Usage Examples

### Environment Group

```python
import pulumi
import pulumi_powerplatform as pp

env_group = pp.EnvironmentGroup(
    "my-env-group",
    display_name="Development Environments",
    description="Group for all development Power Platform environments",
)

pulumi.export("groupId", env_group.id)
```

### DLP Policy

```python
import pulumi
import pulumi_powerplatform as pp

dlp_policy = pp.DlpPolicy(
    "my-dlp-policy",
    name="Restrict Business Data Group",
    rule_sets=[
        {
            "id": "default-rule-set",
            "version": "1.0",
            "inputs": {
                "businessDataGroup": ["shared_office365"],
                "nonBusinessDataGroup": ["shared_twitter"],
            },
        }
    ],
)

pulumi.export("policyId", dlp_policy.id)
```

### Billing Policy

```python
import pulumi
import pulumi_powerplatform as pp

billing_policy = pp.BillingPolicy(
    "my-billing-policy",
    name="Production Billing",
    location="unitedstates",
    status="Enabled",
    billing_instrument={
        "id": "/subscriptions/00000000-0000-0000-0000-000000000000",
        "resourceGroup": "rg-powerplatform",
        "subscriptionId": "00000000-0000-0000-0000-000000000000",
    },
)

pulumi.export("billingPolicyId", billing_policy.id)
```

### Managed Environment

```python
import pulumi
import pulumi_powerplatform as pp

managed_env = pp.ManagedEnvironment(
    "my-managed-env",
    environment_id="00000000-0000-0000-0000-000000000000",
)

pulumi.export("managedEnvId", managed_env.id)
```

### Environment Backup

```python
import pulumi
import pulumi_powerplatform as pp

backup = pp.EnvironmentBackup(
    "my-env-backup",
    environment_id="00000000-0000-0000-0000-000000000000",
    label="pre-release-backup",
)

pulumi.export("backupId", backup.id)
```

### Role Assignment

```python
import pulumi
import pulumi_powerplatform as pp

role_assignment = pp.RoleAssignment(
    "my-role-assignment",
    principal_object_id="00000000-0000-0000-0000-000000000000",
    principal_type="User",
    role_definition_id="00000000-0000-0000-0000-000000000001",
    scope="/providers/Microsoft.PowerPlatform",
)

pulumi.export("roleAssignmentId", role_assignment.id)
```

### ISV Contract

```python
import pulumi
import pulumi_powerplatform as pp

isv_contract = pp.IsvContract(
    "my-isv-contract",
    name="Contoso ISV Contract",
    geo="unitedstates",
    status="Enabled",
)

pulumi.export("isvContractId", isv_contract.id)
```

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/rpothin/pulumi-powerplatform.git
cd pulumi-powerplatform

# Install in development mode
pip install -e ".[dev]"
```

### Running Tests

```bash
python -m pytest tests/ -v
```

### Linting

```bash
ruff check provider/ tests/
```

### Project Structure

```
pulumi-powerplatform/
├── provider/
│   └── pulumi_powerplatform/
│       ├── __init__.py              # Package exports
│       ├── __main__.py              # gRPC server entry point
│       ├── provider.py              # Main provider (CRUD dispatch)
│       ├── config.py                # Configuration resolution
│       ├── client.py                # SDK client factory (auth)
│       ├── utils.py                 # Shared helpers (pv_str)
│       ├── resources/
│       │   ├── environment_group.py # Environment Group CRUD
│       │   ├── dlp_policy.py        # DLP Policy CRUD
│       │   ├── billing_policy.py    # Billing Policy CRUD
│       │   ├── managed_environment.py # Managed Environment Enable/Disable
│       │   ├── environment_backup.py  # Environment Backup Create/Read/Delete
│       │   ├── role_assignment.py     # Role Assignment Create/Read/Delete
│       │   └── isv_contract.py        # ISV Contract CRUD
│       ├── functions/
│       │   ├── get_environments.py  # List environments
│       │   ├── get_connectors.py    # List connectors
│       │   ├── get_apps.py          # List apps
│       │   └── get_flows.py         # List flows
│       └── raw_api/                 # Raw REST API for SDK gaps
│           ├── __init__.py
│           └── client.py            # RawApiClient scaffold
├── sdk/
│   └── python/
│       └── pulumi_powerplatform/    # End-user Python SDK
├── examples/                        # Usage examples (one per resource)
├── tests/                           # Unit tests
├── .github/
│   └── workflows/
│       └── ci.yaml                  # CI/CD pipeline
├── schema.json                      # Pulumi Package Schema
├── PulumiPlugin.yaml                # Plugin metadata
├── pyproject.toml                   # Python project config
├── CONTRIBUTING.md                  # Contributor guide
└── README.md
```

## Roadmap

### Phase 1: Foundation (MVP) ✅
- Provider skeleton with authentication
- Environment Group — Full CRUD
- DLP Policy — Full CRUD
- Role Assignment — Create/Read/Delete
- Data source: getEnvironments

### Phase 2: Core Resources ⚠️ Partial
- ✅ Billing Policy — Full CRUD
- ✅ Managed Environment — Enable/Disable
- ✅ Environment Backup — Create/Read/Delete
- ✅ Data sources: getConnectors, getApps, getFlows
- ❌ Environment resource (requires raw REST API — see `raw_api/`)
- ❌ Environment Settings resource

### Phase 3: Extended Resources ⚠️ Partial
- ✅ ISV Contract — Full CRUD
- ❌ Power Pages Website
- ❌ DLP Policy Assignment
- ❌ Copilot Studio Bot admin
- ❌ Dynamics FinOps Settings
- ❌ Cross-tenant reports
- ❌ Application package install

### Phase 4: Polish & Distribution ⚠️ Partial
- ✅ Python SDK for end-user consumption (`sdk/python/`)
- ✅ Examples for all resources
- ✅ CI/CD pipeline (lint, test, schema validation)
- ❌ PyPI publication
- ❌ Pulumi Registry listing
- ❌ Multi-language SDK generation (TypeScript, Go, C#)
- ❌ Import support

### Phase 5: Future
- Generated SDKs for TypeScript, Go, C#
- PyPI publication
- Pulumi Registry listing
- Import support
- Retry/exponential backoff for transient failures
- Additional resources (see Phase 2/3 gaps above)

## Known Limitations

- **DLP Policy delete**: The `powerplatform-management` SDK does not expose a direct DELETE endpoint for rule-based policies. The provider works around this by deleting each rule set individually. A future version may use the `raw_api/` module for direct deletion.
- **ISV Contract `geo`**: Immutable after creation — changing `geo` triggers a resource replacement.
- **No retry logic**: API rate limiting (HTTP 429) and transient failures are not yet handled. This is planned as future work.
- **No raw REST API**: The `raw_api/` module is currently a scaffold. It will be implemented when the first resource requires direct REST access (e.g., Environment creation).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and how to add new resources.

## License

MIT — see [LICENSE](LICENSE) for details.
