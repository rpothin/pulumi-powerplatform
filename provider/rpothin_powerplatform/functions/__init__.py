"""Function (data source) handlers for the Power Platform provider."""

from rpothin_powerplatform.functions.get_apps import GetAppsFunction
from rpothin_powerplatform.functions.get_connectors import GetConnectorsFunction
from rpothin_powerplatform.functions.get_data_records import GetDataRecordsFunction
from rpothin_powerplatform.functions.get_dlp_policies import GetDlpPoliciesFunction
from rpothin_powerplatform.functions.get_dlp_policy_migration_config import GetDlpPolicyMigrationConfigFunction
from rpothin_powerplatform.functions.get_environments import GetEnvironmentsFunction
from rpothin_powerplatform.functions.get_flows import GetFlowsFunction

__all__ = [
    "GetAppsFunction",
    "GetConnectorsFunction",
    "GetDataRecordsFunction",
    "GetDlpPoliciesFunction",
    "GetDlpPolicyMigrationConfigFunction",
    "GetEnvironmentsFunction",
    "GetFlowsFunction",
]
