---
title: Power Platform Installation & Configuration
meta_desc: How to install and configure the Pulumi Power Platform provider.
layout: package
---

## Installation

The Power Platform provider is available as a package in the following
Pulumi-supported languages:

### Python

[rpothin-powerplatform on PyPI](https://pypi.org/project/rpothin-powerplatform/)

```bash
pip install rpothin-powerplatform
```

### Node.js

[@rpothin/powerplatform on npm](https://www.npmjs.com/package/@rpothin/powerplatform)

```bash
npm install @rpothin/powerplatform
```

### .NET

[Rpothin.Powerplatform on NuGet](https://www.nuget.org/packages/Rpothin.Powerplatform/)

```bash
dotnet add package Rpothin.Powerplatform
```

### Go

[powerplatform on pkg.go.dev](https://pkg.go.dev/github.com/rpothin/pulumi-powerplatform/sdk/go/powerplatform)

```bash
go get github.com/rpothin/pulumi-powerplatform/sdk/go/powerplatform
```

### Java

[io.github.rpothin:powerplatform on Maven Central](https://central.sonatype.com/artifact/io.github.rpothin/powerplatform)

**Gradle**

```groovy
implementation "io.github.rpothin:powerplatform:<version>"
```

**Maven**

```xml
<dependency>
  <groupId>io.github.rpothin</groupId>
  <artifactId>powerplatform</artifactId>
  <version>&lt;version&gt;</version>
</dependency>
```

### Plugin installation

```bash
VERSION=$(curl -sL https://api.github.com/repos/rpothin/pulumi-powerplatform/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
pulumi plugin install resource powerplatform $VERSION --server github://api.github.com/rpothin
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
- Python 3.10 or later available on `PATH`
