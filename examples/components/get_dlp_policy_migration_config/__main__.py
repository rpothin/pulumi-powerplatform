"""Example: generate a migration config for an existing DLP policy."""

import pulumi
import rpothin_powerplatform as pp

migration_config = pp.get_dlp_policy_migration_config(
    source_policy_id="<source-policy-id>",
)

pulumi.export("display_name", migration_config.display_name)
pulumi.export("rule_set_count", len(migration_config.rule_sets))
