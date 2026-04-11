"""Function (data source) handlers for the Power Platform provider."""

from pulumi_powerplatform.functions.get_apps import GetAppsFunction
from pulumi_powerplatform.functions.get_connectors import GetConnectorsFunction
from pulumi_powerplatform.functions.get_environments import GetEnvironmentsFunction
from pulumi_powerplatform.functions.get_flows import GetFlowsFunction

__all__ = [
    "GetAppsFunction",
    "GetConnectorsFunction",
    "GetEnvironmentsFunction",
    "GetFlowsFunction",
]
