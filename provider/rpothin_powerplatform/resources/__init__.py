"""Resource handlers for the Power Platform provider."""

from rpothin_powerplatform.resources.billing_policy import BillingPolicyResource
from rpothin_powerplatform.resources.dlp_policy import DlpPolicyResource
from rpothin_powerplatform.resources.environment import EnvironmentResource
from rpothin_powerplatform.resources.environment_backup import EnvironmentBackupResource
from rpothin_powerplatform.resources.environment_group import EnvironmentGroupResource
from rpothin_powerplatform.resources.environment_settings import EnvironmentSettingsResource
from rpothin_powerplatform.resources.isv_contract import IsvContractResource
from rpothin_powerplatform.resources.managed_environment import ManagedEnvironmentResource
from rpothin_powerplatform.resources.role_assignment import RoleAssignmentResource

__all__ = [
    "BillingPolicyResource",
    "DlpPolicyResource",
    "EnvironmentBackupResource",
    "EnvironmentGroupResource",
    "EnvironmentResource",
    "EnvironmentSettingsResource",
    "IsvContractResource",
    "ManagedEnvironmentResource",
    "RoleAssignmentResource",
]
