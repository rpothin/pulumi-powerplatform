Manual environment backups are **immutable** — the Power Platform API does not support updating a backup after it has been created.

The only inputs are `environmentId` and `label`. Any change to either will trigger a **replacement**: Pulumi will delete the existing backup and create a new one.

To make this replacement behavior explicit in your program, use the [`replaceOnChanges`](https://www.pulumi.com/docs/concepts/options/replaceonchanges/) resource option:

{{< chooser language "python,typescript,go,csharp,yaml" >}}

{{% choosable language python %}}
```python
backup = pp.EnvironmentBackup("my-backup",
    environment_id=env.id,
    label="pre-release",
    opts=pulumi.ResourceOptions(replace_on_changes=["label"])
)
```
{{% /choosable %}}

{{% choosable language typescript %}}
```typescript
const backup = new pp.EnvironmentBackup("my-backup", {
    environmentId: env.id,
    label: "pre-release",
}, { replaceOnChanges: ["label"] });
```
{{% /choosable %}}

{{% choosable language go %}}
```go
backup, err := pp.NewEnvironmentBackup(ctx, "my-backup", &pp.EnvironmentBackupArgs{
    EnvironmentId: env.ID(),
    Label:         pulumi.String("pre-release"),
}, pulumi.ReplaceOnChanges([]string{"label"}))
```
{{% /choosable %}}

{{% choosable language csharp %}}
```csharp
var backup = new EnvironmentBackup("my-backup", new EnvironmentBackupArgs
{
    EnvironmentId = env.Id,
    Label = "pre-release",
}, new CustomResourceOptions { ReplaceOnChanges = { "label" } });
```
{{% /choosable %}}

{{% choosable language yaml %}}
```yaml
resources:
  my-backup:
    type: powerplatform:index:EnvironmentBackup
    properties:
      environmentId: ${env.id}
      label: pre-release
    options:
      replaceOnChanges:
        - label
```
{{% /choosable %}}

{{< /chooser >}}
