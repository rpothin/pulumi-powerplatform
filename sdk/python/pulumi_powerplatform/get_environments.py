"""Power Platform getEnvironments function."""

import pulumi


def get_environments(filter: str = None, top: int = None, opts: pulumi.InvokeOptions = None):
    """Lists Power Platform environments."""
    return pulumi.runtime.invoke(
        "powerplatform:index:getEnvironments",
        {"filter": filter, "top": top},
        opts=opts,
    ).value
