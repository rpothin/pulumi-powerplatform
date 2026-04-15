"""Power Platform getApps function."""

import pulumi


def get_apps(environment_id: str, opts: pulumi.InvokeOptions = None):
    """Lists Power Apps in a Power Platform environment."""
    return pulumi.runtime.invoke(
        "powerplatform:index:getApps",
        {"environmentId": environment_id},
        opts=opts,
    ).value
