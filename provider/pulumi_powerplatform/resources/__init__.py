"""Resource handlers for the Power Platform provider."""

from pulumi_powerplatform.resources.billing_policy import BillingPolicyResource
from pulumi_powerplatform.resources.dlp_policy import DlpPolicyResource
from pulumi_powerplatform.resources.environment_backup import EnvironmentBackupResource
from pulumi_powerplatform.resources.environment_group import EnvironmentGroupResource
from pulumi_powerplatform.resources.isv_contract import IsvContractResource
from pulumi_powerplatform.resources.managed_environment import ManagedEnvironmentResource
from pulumi_powerplatform.resources.role_assignment import RoleAssignmentResource

__all__ = [
    "BillingPolicyResource",
    "DlpPolicyResource",
    "EnvironmentBackupResource",
    "EnvironmentGroupResource",
    "IsvContractResource",
    "ManagedEnvironmentResource",
    "RoleAssignmentResource",
]
