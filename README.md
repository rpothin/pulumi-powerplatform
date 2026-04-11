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

## Data Sources (Functions)

| Function | Token | Status |
|----------|-------|--------|
| Get Environments | `powerplatform:index:getEnvironments` | ✅ Available |

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
│       │   └── dlp_policy.py        # DLP Policy CRUD
│       └── functions/
│           └── get_environments.py  # List environments
├── examples/                        # Usage examples
├── tests/                           # Unit tests
├── schema.json                      # Pulumi Package Schema
├── PulumiPlugin.yaml                # Plugin metadata
├── pyproject.toml                   # Python project config
└── README.md
```

## Roadmap

### Phase 1: Foundation (Current — MVP) ✅
- Provider skeleton with authentication
- Environment Group — Full CRUD
- DLP Policy — Full CRUD
- Data source: getEnvironments

### Phase 2: Core Resources
- Environment — Full CRUD (via raw REST API for creation)
- Environment Settings — Create/Read/Update
- Billing Policy — Full CRUD
- Managed Environment — Enable/Disable
- Environment Backup — Create/Read/Delete
- Data sources: connectors, connections, apps, flows

### Phase 3: Extended Resources
- Power Pages Website — Create/Read/Delete + operations
- ISV Contract — Full CRUD
- DLP Policy Assignment — Create/Read
- Role Assignment — Create/Read/Delete
- Dynamics FinOps Settings — Read/Update

### Phase 4: Polish & Distribution
- Generated SDK for end-user consumption (Python, TypeScript, Go, C#)
- PyPI publication
- Pulumi Registry listing
- CI/CD pipeline
- Import support

## License

MIT — see [LICENSE](LICENSE) for details.
