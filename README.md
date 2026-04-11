# pulumi-powerplatform

Community led Pulumi custom provider for Power Platform based on the [Microsoft Power Platform Management Python SDK](https://pypi.org/project/powerplatform-management/).

## Overview

This provider enables managing Microsoft Power Platform resources using [Pulumi](https://www.pulumi.com/) Infrastructure-as-Code. It is built as a native Python Pulumi provider using the **experimental provider framework** (`pulumi.provider.experimental.Provider`), which provides full async CRUD lifecycle support.

### Architecture

- **Provider Framework**: Pulumi Experimental Provider (gRPC-based, async, distributable)
- **Backend SDK**: [`powerplatform-management`](https://pypi.org/project/powerplatform-management/) (Microsoft Kiota-generated, async)
- **Authentication**: Azure Identity (`azure-identity`) supporting client secret, managed identity, Azure CLI, and more

## Resources

| Resource | Type Token | Status |
|----------|-----------|--------|
| Environment Group | `powerplatform:index:EnvironmentGroup` | ✅ Full CRUD |
| DLP Policy | `powerplatform:index:DlpPolicy` | ✅ Full CRUD |
| Billing Policy | `powerplatform:index:BillingPolicy` | ✅ Full CRUD |
| Managed Environment | `powerplatform:index:ManagedEnvironment` | ✅ Enable/Disable |
| Environment Backup | `powerplatform:index:EnvironmentBackup` | ✅ Create/Read/Delete |
| Role Assignment | `powerplatform:index:RoleAssignment` | ✅ Create/Read/Delete |
| ISV Contract | `powerplatform:index:IsvContract` | ✅ Full CRUD |

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

env_group = pulumi.CustomResource(
    "my-env-group",
    "powerplatform:index:EnvironmentGroup",
    {
        "displayName": "Development Environments",
        "description": "Group for all development Power Platform environments",
    },
)

pulumi.export("groupId", env_group.id)
```

### DLP Policy

```python
import pulumi

dlp_policy = pulumi.CustomResource(
    "my-dlp-policy",
    "powerplatform:index:DlpPolicy",
    {
        "name": "Restrict Business Data Group",
        "ruleSets": [
            {
                "id": "default-rule-set",
                "version": "1.0",
                "inputs": {
                    "businessDataGroup": ["shared_office365"],
                    "nonBusinessDataGroup": ["shared_twitter"],
                },
            }
        ],
    },
)

pulumi.export("policyId", dlp_policy.id)
```

### Billing Policy

```python
import pulumi

billing_policy = pulumi.CustomResource(
    "my-billing-policy",
    "powerplatform:index:BillingPolicy",
    {
        "name": "Production Billing",
        "location": "unitedstates",
        "status": "Enabled",
        "billingInstrument": {
            "id": "/subscriptions/00000000-0000-0000-0000-000000000000",
            "resourceGroup": "rg-powerplatform",
            "subscriptionId": "00000000-0000-0000-0000-000000000000",
        },
    },
)

pulumi.export("billingPolicyId", billing_policy.id)
```

### Managed Environment

```python
import pulumi

managed_env = pulumi.CustomResource(
    "my-managed-env",
    "powerplatform:index:ManagedEnvironment",
    {
        "environmentId": "00000000-0000-0000-0000-000000000000",
    },
)

pulumi.export("managedEnvId", managed_env.id)
```

### Environment Backup

```python
import pulumi

backup = pulumi.CustomResource(
    "my-env-backup",
    "powerplatform:index:EnvironmentBackup",
    {
        "environmentId": "00000000-0000-0000-0000-000000000000",
        "label": "pre-release-backup",
    },
)

pulumi.export("backupId", backup.id)
```

### Role Assignment

```python
import pulumi

role_assignment = pulumi.CustomResource(
    "my-role-assignment",
    "powerplatform:index:RoleAssignment",
    {
        "principalObjectId": "00000000-0000-0000-0000-000000000000",
        "principalType": "User",
        "roleDefinitionId": "00000000-0000-0000-0000-000000000001",
        "scope": "/providers/Microsoft.PowerPlatform",
    },
)

pulumi.export("roleAssignmentId", role_assignment.id)
```

### ISV Contract

```python
import pulumi

isv_contract = pulumi.CustomResource(
    "my-isv-contract",
    "powerplatform:index:IsvContract",
    {
        "name": "Contoso ISV Contract",
        "geo": "unitedstates",
        "status": "Enabled",
    },
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
│       ├── client.py                # SDK client factory (auth)
│       ├── resources/
│       │   ├── environment_group.py # Environment Group CRUD
│       │   ├── dlp_policy.py        # DLP Policy CRUD
│       │   ├── billing_policy.py    # Billing Policy CRUD
│       │   ├── managed_environment.py # Managed Environment Enable/Disable
│       │   ├── environment_backup.py  # Environment Backup Create/Read/Delete
│       │   ├── role_assignment.py     # Role Assignment Create/Read/Delete
│       │   └── isv_contract.py        # ISV Contract CRUD
│       └── functions/
│           ├── get_environments.py  # List environments
│           ├── get_connectors.py    # List connectors
│           ├── get_apps.py          # List apps
│           └── get_flows.py         # List flows
├── sdk/
│   └── python/
│       ├── pulumi_powerplatform/    # End-user Python SDK
│       │   ├── __init__.py          # Package exports
│       │   ├── provider.py          # Provider resource
│       │   ├── environment_group.py # EnvironmentGroup resource
│       │   ├── dlp_policy.py        # DlpPolicy resource
│       │   ├── billing_policy.py    # BillingPolicy resource
│       │   ├── managed_environment.py # ManagedEnvironment resource
│       │   ├── environment_backup.py  # EnvironmentBackup resource
│       │   ├── role_assignment.py     # RoleAssignment resource
│       │   ├── isv_contract.py        # IsvContract resource
│       │   ├── get_environments.py  # getEnvironments function
│       │   ├── get_connectors.py    # getConnectors function
│       │   ├── get_apps.py          # getApps function
│       │   └── get_flows.py         # getFlows function
│       └── pyproject.toml           # SDK package config
├── examples/                        # Usage examples
├── tests/                           # Unit tests
├── .github/
│   └── workflows/
│       └── ci.yaml                  # CI/CD pipeline
├── schema.json                      # Pulumi Package Schema
├── PulumiPlugin.yaml                # Plugin metadata
├── pyproject.toml                   # Python project config
└── README.md
```

## Roadmap

### Phase 1: Foundation (MVP) ✅
- Provider skeleton with authentication
- Environment Group — Full CRUD
- DLP Policy — Full CRUD
- Data source: getEnvironments

### Phase 2: Core Resources ✅
- Billing Policy — Full CRUD
- Managed Environment — Enable/Disable
- Environment Backup — Create/Read/Delete
- Data sources: getConnectors, getApps, getFlows

### Phase 3: Extended Resources ✅
- ISV Contract — Full CRUD
- Role Assignment — Create/Read/Delete

### Phase 4: Polish & Distribution ✅
- Python SDK for end-user consumption (`sdk/python/`)
- Examples for all resources
- CI/CD pipeline (lint, test, schema validation)

### Phase 5: Future
- Generated SDKs for TypeScript, Go, C#
- PyPI publication
- Pulumi Registry listing
- Import support
- Additional resources (Power Pages Website, DLP Policy Assignment, etc.)

## License

MIT — see [LICENSE](LICENSE) for details.
