---
title: Power Platform
meta_desc: The Pulumi Power Platform provider manages Microsoft Power Platform resources.
layout: package
---

The Power Platform provider for Pulumi allows you to manage
[Microsoft Power Platform](https://powerplatform.microsoft.com/) resources
using infrastructure as code.

## Overview

The provider supports:

- **Environment** — create, update, and delete Power Platform environments
- **Environment Group** — organise environments into groups
- **Environment Settings** — govern per-environment settings (audit, logging, etc.)
- **Environment Backup** — manage environment backups
- **Managed Environment** — enable/disable managed-environment governance
- **DLP Policy** — configure data loss prevention policies
- **Billing Policy** — manage pay-as-you-go billing policies
- **Role Assignment** — assign security roles to principals
- **ISV Contract** — manage ISV contract resources

Data-source functions are available for listing environments, connectors,
apps, and flows.

## Example

{{< chooser language "python,typescript,go,csharp" >}}

{{% choosable language python %}}

```python
import pulumi
import pulumi_powerplatform as pp

env = pp.Environment(
    "dev",
    display_name="Development",
    location="unitedstates",
    environment_type="Sandbox",
)

pulumi.export("envId", env.id)
```

{{% /choosable %}}

{{% choosable language typescript %}}

```typescript
import * as pp from "@pulumi/powerplatform";

const env = new pp.Environment("dev", {
    displayName: "Development",
    location: "unitedstates",
    environmentType: "Sandbox",
});

export const envId = env.id;
```

{{% /choosable %}}

{{% choosable language go %}}

```go
package main

import (
	pp "github.com/rpothin/pulumi-powerplatform/sdk/go/powerplatform"
	"github.com/pulumi/pulumi/sdk/v3/go/pulumi"
)

func main() {
	pulumi.Run(func(ctx *pulumi.Context) error {
		env, err := pp.NewEnvironment(ctx, "dev", &pp.EnvironmentArgs{
			DisplayName:     pulumi.String("Development"),
			Location:        pulumi.String("unitedstates"),
			EnvironmentType: pulumi.String("Sandbox"),
		})
		if err != nil {
			return err
		}
		ctx.Export("envId", env.ID())
		return nil
	})
}
```

{{% /choosable %}}

{{% choosable language csharp %}}

```csharp
using Pulumi;
using Pulumi.Powerplatform;

return await Deployment.RunAsync(() =>
{
    var env = new Environment("dev", new EnvironmentArgs
    {
        DisplayName = "Development",
        Location = "unitedstates",
        EnvironmentType = "Sandbox",
    });

    return new Dictionary<string, object?>
    {
        ["envId"] = env.Id,
    };
});
```

{{% /choosable %}}

{{< /chooser >}}
