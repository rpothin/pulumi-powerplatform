`EnvironmentSettings` manages a fixed set of settings on a Power Platform environment via PATCH to the admin API. The five managed properties are: `maxUploadFileSize`, `pluginTraceLogSetting`, `isAuditEnabled`, `isUserAccessAuditEnabled`, and `isActivityLoggingEnabled`.

**Deletion behavior:** Running `pulumi destroy` (or removing the resource from your program) removes the `EnvironmentSettings` resource from Pulumi state only. The settings themselves **persist in Power Platform** — they cannot be unset via the API. This means your environment retains the configured settings even after the Pulumi resource is gone.

If you need to revert settings, you must either:
- Update the resource to your desired values before destroying it, or
- Adjust the settings manually in the Power Platform admin center.

**Partial management:** Only properties that are explicitly set in your program are sent to the API. Removing a property from your code does **not** reset that setting in Power Platform — it simply stops being managed by Pulumi.

**Drift detection:** `pulumi refresh` will detect any changes made outside Pulumi to the five properties listed above. Other environment settings are not tracked by this resource.
