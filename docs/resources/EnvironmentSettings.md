`EnvironmentSettings` manages settings on a Power Platform environment via PATCH to the admin API.

**Deletion behavior:** Running `pulumi destroy` (or removing the resource from your program) removes the `EnvironmentSettings` resource from Pulumi state only. The settings themselves **persist in Power Platform** — they cannot be unset via the API. This means your environment retains the configured settings even after the Pulumi resource is gone.

If you need to revert settings, you must either:
- Update the resource to your desired values before destroying it, or
- Adjust the settings manually in the Power Platform admin center.

**Drift detection:** Because the API returns the full settings object on every read, `pulumi refresh` will correctly detect any settings changed outside of Pulumi.
