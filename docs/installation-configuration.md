---
title: Power Platform Installation & Configuration
meta_desc: How to install and configure the Pulumi Power Platform provider.
layout: package
---

## Installation

The Power Platform provider is available as a package in the following
Pulumi-supported languages:

### Python

```bash
pip install pulumi-powerplatform
```

### Node.js

```bash
npm install @rpothin/powerplatform
```

### .NET

```bash
dotnet add package Rpothin.Powerplatform
```

### Go

```bash
go get github.com/rpothin/pulumi-powerplatform/sdk/go/powerplatform
```

## Authentication

The provider authenticates with Microsoft Power Platform using
Azure Active Directory credentials. You can supply credentials in
three ways (in order of precedence):

### 1. Explicit configuration

Set configuration values on the provider:

```bash
pulumi config set powerplatform:tenantId <AZURE_TENANT_ID>
pulumi config set powerplatform:clientId <AZURE_CLIENT_ID>
pulumi config set --secret powerplatform:clientSecret <AZURE_CLIENT_SECRET>
```

### 2. Environment variables

Export the following environment variables:

| Variable              | Description                       |
|-----------------------|-----------------------------------|
| `AZURE_TENANT_ID`    | Azure AD tenant (directory) ID    |
| `AZURE_CLIENT_ID`    | Application (client) ID           |
| `AZURE_CLIENT_SECRET` | Client secret value              |

### 3. DefaultAzureCredential

When explicit credentials are not provided the provider falls back to
[`DefaultAzureCredential`](https://learn.microsoft.com/python/api/azure-identity/azure.identity.defaultazurecredential),
which automatically tries managed identity, Azure CLI, Visual Studio Code,
and other credential sources.

## Configuration Reference

| Property       | Type   | Required | Description |
|---------------|--------|----------|-------------|
| `tenantId`    | string | No       | Azure AD Tenant ID. Falls back to `AZURE_TENANT_ID`. |
| `clientId`    | string | No       | Azure AD Application (Client) ID. Falls back to `AZURE_CLIENT_ID`. |
| `clientSecret`| string | No       | Azure AD Client Secret. Falls back to `AZURE_CLIENT_SECRET`. |

## Prerequisites

- A Microsoft Power Platform tenant with admin access
- An Azure AD app registration with the appropriate Power Platform API
  permissions (`https://api.powerplatform.com/.default`)
- Pulumi CLI v3 or later
