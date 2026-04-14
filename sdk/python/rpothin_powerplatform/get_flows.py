"""Power Platform getFlows function."""

import pulumi


def get_flows(environment_id: str, opts: pulumi.InvokeOptions = None):
    """Lists Cloud Flows in a Power Platform environment."""
    return pulumi.runtime.invoke(
        "powerplatform:index:getFlows",
        {"environmentId": environment_id},
        opts=opts,
    ).value
