"""Power Platform getConnectors function."""

import pulumi


def get_connectors(environment_id: str, opts: pulumi.InvokeOptions = None):
    """Lists connectors available in a Power Platform environment."""
    return pulumi.runtime.invoke(
        "powerplatform:index:getConnectors",
        {"environmentId": environment_id},
        opts=opts,
    ).value
