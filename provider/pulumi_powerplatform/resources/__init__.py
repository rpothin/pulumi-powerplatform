"""Resource handlers for the Power Platform provider."""

from pulumi_powerplatform.resources.dlp_policy import DlpPolicyResource
from pulumi_powerplatform.resources.environment_group import EnvironmentGroupResource

__all__ = ["EnvironmentGroupResource", "DlpPolicyResource"]
