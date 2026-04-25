`ManagedEnvironment` enables the managed environment governance setting on an existing Power Platform environment.

**Deletion behavior:** Running `pulumi destroy` (or removing the resource from your program) **disables** the managed environment setting on the target environment. It does **not** delete the environment itself. The environment continues to exist; it simply reverts to a non-managed state.

**Drift detection:** If managed environment mode is disabled outside of Pulumi, `pulumi refresh` will treat this resource as gone (the provider returns an empty state when the environment is no longer in managed mode).

**Dependency ordering:** Because `ManagedEnvironment` modifies an existing environment, use the [`dependsOn`](https://www.pulumi.com/docs/concepts/options/dependson/) resource option to ensure the target environment is fully created before enabling managed environment governance:

{{< chooser language "python,typescript,go,csharp,yaml" >}}

{{% choosable language python %}}
```python
managed = pp.ManagedEnvironment("managed",
    environment_id=env.id,
    opts=pulumi.ResourceOptions(depends_on=[env])
)
```
{{% /choosable %}}

{{% choosable language typescript %}}
```typescript
const managed = new pp.ManagedEnvironment("managed", {
    environmentId: env.id,
}, { dependsOn: [env] });
```
{{% /choosable %}}

{{% choosable language go %}}
```go
managed, err := pp.NewManagedEnvironment(ctx, "managed", &pp.ManagedEnvironmentArgs{
    EnvironmentId: env.ID(),
}, pulumi.DependsOn([]pulumi.Resource{env}))
```
{{% /choosable %}}

{{% choosable language csharp %}}
```csharp
var managed = new ManagedEnvironment("managed", new ManagedEnvironmentArgs
{
    EnvironmentId = env.Id,
}, new CustomResourceOptions { DependsOn = { env } });
```
{{% /choosable %}}

{{% choosable language yaml %}}
```yaml
resources:
  managed:
    type: powerplatform:index:ManagedEnvironment
    properties:
      environmentId: ${env.id}
    options:
      dependsOn:
        - ${env}
```
{{% /choosable %}}

{{< /chooser >}}
