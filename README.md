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
| Environment | `powerplatform:index:Environment` | ✅ Full CRUD | |
| Environment Group | `powerplatform:index:EnvironmentGroup` | ✅ Full CRUD | |
| Environment Settings | `powerplatform:index:EnvironmentSettings` | ✅ Full CRUD | |
| Managed Environment | `powerplatform:index:ManagedEnvironment` | ✅ Enable/Disable | |
| Tenant Settings | `powerplatform:index:TenantSettings` | ✅ Available | Tenant-wide singleton settings |
| DLP Policy | `powerplatform:index:DlpPolicy` | ✅ Full CRUD | Delete removes rule sets individually (see [Known Limitations](#known-limitations)) |
| Billing Policy | `powerplatform:index:BillingPolicy` | ✅ Full CRUD | |
| Data Record | `powerplatform:index:DataRecord` | ✅ Full CRUD | Dataverse table row primitive |
| Pipeline Sharing | `powerplatform:index:PipelineSharing` | ✅ Create/Delete | Shares deployment pipelines with teams |
| Enterprise Policy Link | `powerplatform:index:EnterprisePolicyLink` | ✅ Full CRUD | |
| Admin Management Application | `powerplatform:index:AdminManagementApplication` | ✅ Full CRUD | |
| Environment Application Admin | `powerplatform:index:EnvironmentApplicationAdmin` | ✅ Create/Read/Delete | |
| Environment Backup | `powerplatform:index:EnvironmentBackup` | ✅ Create/Read/Delete | |
| Role Assignment | `powerplatform:index:RoleAssignment` | ✅ Create/Read/Delete | |
| ISV Contract | `powerplatform:index:IsvContract` | ✅ Full CRUD | `geo` is immutable after creation |

## Component Resources

AVM-aligned component resources compose multiple primitives into reusable modules. They are available in the `components` sub-namespace.

| Component | Token | Description |
| --- | --- | --- |
| `ResEnvironment` | `powerplatform:components:ResEnvironment` | Provisions a Power Platform environment (with optional Dataverse, Managed Environment, and settings) |
| `ResDlpPolicy` | `powerplatform:components:ResDlpPolicy` | Manages a Data Loss Prevention policy |
| `ResTenantSettings` | `powerplatform:components:ResTenantSettings` | Manages tenant-wide Power Platform settings |
| `ResDeploymentPipeline` | `powerplatform:components:ResDeploymentPipeline` | Provisions a deployment pipeline with stages, team membership, and environment linking |

## Data Sources (Functions)

| Function | Token | Status |
|----------|-------|--------|
| Get Environments | `powerplatform:index:getEnvironments` | ✅ Available |
| Get Connectors | `powerplatform:index:getConnectors` | ✅ Available |
| Get Apps | `powerplatform:index:getApps` | ✅ Available |
| Get Flows | `powerplatform:index:getFlows` | ✅ Available |
| Get DLP Policies | `powerplatform:index:getDlpPolicies` | ✅ Available |
| Get DLP Policy Migration Config | `powerplatform:index:getDlpPolicyMigrationConfig` | ✅ Available |
| Get Security Roles | `powerplatform:index:getSecurityRoles` | ✅ Available |
| Get Data Records | `powerplatform:index:getDataRecords` | ✅ Available |

## Prerequisites

- Python 3.10+
- [Pulumi CLI](https://www.pulumi.com/docs/install/) v3+
- An Azure AD application with Power Platform API permissions, or access via Azure CLI / Managed Identity

## Installation

```bash
pip install rpothin-powerplatform
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
import rpothin_powerplatform as pp

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
import rpothin_powerplatform as pp

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
import rpothin_powerplatform as pp

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
import rpothin_powerplatform as pp

managed_env = pp.ManagedEnvironment(
    "my-managed-env",
    environment_id="00000000-0000-0000-0000-000000000000",
)

pulumi.export("managedEnvId", managed_env.id)
```

### Environment Backup

```python
import pulumi
import rpothin_powerplatform as pp

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
import rpothin_powerplatform as pp

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
import rpothin_powerplatform as pp

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
│   └── rpothin_powerplatform/
│       ├── __init__.py              # Package exports
│       ├── __main__.py              # gRPC server entry point
│       ├── provider.py              # Main provider (CRUD dispatch)
│       ├── config.py                # Configuration resolution
│       ├── client.py                # SDK client factory (auth)
│       ├── utils.py                 # Shared helpers (pv_str)
│       ├── components/              # AVM-aligned component resources
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
│       └── rpothin_powerplatform/    # End-user Python SDK
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

### Phase 2: Core Resources ✅
- ✅ Billing Policy — Full CRUD
- ✅ Managed Environment — Enable/Disable
- ✅ Environment Backup — Create/Read/Delete
- ✅ Data sources: getConnectors, getApps, getFlows
- ✅ Environment resource
- ✅ Environment Settings resource

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
- ✅ PyPI publication
- ⚠️ Pulumi Registry listing
- ✅ Multi-language SDK generation (TypeScript, Go, C#, Java)
- ❌ Import support
- ❌ Retry/exponential backoff for transient failures

## Known Limitations

- **DLP Policy delete**: The `powerplatform-management` SDK does not expose a direct DELETE endpoint for rule-based policies. The provider works around this by deleting each rule set individually.
- **ISV Contract `geo`**: Immutable after creation — changing `geo` triggers a resource replacement.
- **No retry logic**: API rate limiting (HTTP 429) and transient failures are not yet handled. This is planned as future work.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and how to add new resources.

## License

MIT — see [LICENSE](LICENSE) for details.
