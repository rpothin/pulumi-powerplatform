"""AVM-aligned ``ResDeploymentPipeline`` component resource.

Mirrors the ``rpothin/terraform-powerplatform-res-deploymentpipeline`` AVM module.
Composes DataRecord resources for deployment environments, pipeline, stages (0–5),
and optionally a team + pipeline-sharing access grant.

No ``from __future__ import annotations`` — the Pulumi Analyzer needs runtime type objects.
"""

from dataclasses import dataclass
from typing import Optional

import pulumi

from ._base import COMPONENT_TOKEN_PREFIX, ComponentArgs, register_component, register_construct

COMPONENT_TYPE = f"{COMPONENT_TOKEN_PREFIX}ResDeploymentPipeline"


@dataclass(kw_only=True)
class PipelineEnvironmentEntry:
    """One entry in the ``environments`` map."""

    id: str
    name: str


@dataclass(kw_only=True)
class PipelineStageConfig:
    """Configuration for one deployment stage."""

    environment_key: str
    description: Optional[str] = None
    deployment_spn_client_id: Optional[str] = None
    is_sharing_enabled: Optional[bool] = None
    require_predeployment_approval: Optional[bool] = None
    require_preexport_approval: Optional[bool] = None
    use_delegated_deployment: Optional[bool] = None


@dataclass(kw_only=True)
class ResDeploymentPipelineArgs(ComponentArgs):
    """Input arguments for :class:`ResDeploymentPipeline`."""

    host_environment_id: str
    pipeline_name: str
    environments: dict[str, PipelineEnvironmentEntry]
    dev_environment_key: str
    pipeline_stages: list[PipelineStageConfig]
    security_group_id: Optional[str] = None
    root_business_unit_id: Optional[str] = None
    deployment_pipeline_user_role_id: Optional[str] = None
    lifecycle_state: Optional[str] = None
    pipeline_description: Optional[str] = None
    enable_ai_deployment_notes: Optional[bool] = None
    enable_redeployment: Optional[bool] = None


@register_component
class ResDeploymentPipeline(pulumi.ComponentResource):
    """AVM-aligned component that manages a Power Platform deployment pipeline lifecycle."""

    resource_id: pulumi.Output[str]
    pipeline_id: pulumi.Output[str]
    pipeline_name: pulumi.Output[str]
    deployment_environment_ids: pulumi.Output[dict[str, str]]
    deployment_stage_ids: pulumi.Output[dict[str, str]]
    pipeline_team_id: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        args: ResDeploymentPipelineArgs,
        opts: Optional[pulumi.ResourceOptions] = None,
    ) -> None:
        super().__init__(COMPONENT_TYPE, name, {}, opts)

        from ._resource_wrappers import _DataRecordWrap, _PipelineSharingWrap  # noqa: PLC0415

        if not args.pipeline_name or not args.pipeline_name.strip():
            raise ValueError("pipeline_name is required.")
        if not isinstance(args.environments, dict) or len(args.environments) < 2:
            raise ValueError("environments must contain at least the dev and one target environment.")
        if not isinstance(args.pipeline_stages, list) or not (1 <= len(args.pipeline_stages) <= 6):
            raise ValueError("pipeline_stages must contain between 1 and 6 stages.")
        if args.dev_environment_key not in args.environments:
            raise ValueError("dev_environment_key must reference an entry in environments.")

        stage_keys = [stage.environment_key for stage in args.pipeline_stages]
        if any(key not in args.environments for key in stage_keys):
            raise ValueError("Each pipeline stage must reference an entry in environments.")
        if args.dev_environment_key in stage_keys:
            raise ValueError("dev_environment_key cannot also be used as a deployment stage target.")
        if len(stage_keys) != len(set(stage_keys)):
            raise ValueError("Each deployment stage must target a unique environment.")
        for stage in args.pipeline_stages:
            if stage.use_delegated_deployment and not stage.deployment_spn_client_id:
                raise ValueError(
                    "deployment_spn_client_id is required when use_delegated_deployment is true."
                )
        if args.security_group_id is not None and (
            args.root_business_unit_id is None or args.deployment_pipeline_user_role_id is None
        ):
            raise ValueError(
                "root_business_unit_id and deployment_pipeline_user_role_id are required when security_group_id is set."
            )

        lifecycle_state = (args.lifecycle_state or "active").lower()
        if lifecycle_state not in {"active", "inactive"}:
            raise ValueError("lifecycle_state must be 'active' or 'inactive'.")
        statecode = 0 if lifecycle_state == "active" else 1
        statuscode = 1 if lifecycle_state == "active" else 2

        child_opts = pulumi.ResourceOptions(
            parent=self,
            providers=(opts.providers if opts else None),
            provider=(opts.provider if opts else None),
        )

        env_records: dict[str, pulumi.CustomResource] = {}
        for env_key, env_entry in args.environments.items():
            env_columns = _omit_none(
                {
                    "environmentid": env_entry.id,
                    "environmenttype": 200000000 if env_key == args.dev_environment_key else 200000001,
                    "name": env_entry.name,
                    "statecode": statecode,
                    "statuscode": statuscode,
                }
            )
            env_records[env_key] = _DataRecordWrap(
                f"{name}-deployment-environment-{env_key}",
                environment_id=args.host_environment_id,
                table_logical_name="deploymentenvironment",
                columns=env_columns,
                disable_on_destroy=True,
                opts=child_opts,
            )

        pipeline_columns = _omit_none(
            {
                "name": args.pipeline_name,
                "deploymenttype": 0,
                "description": args.pipeline_description,
                "enableaideploymentnotes": True
                if args.enable_ai_deployment_notes is None
                else args.enable_ai_deployment_notes,
                "enableredeployment": True
                if args.enable_redeployment is None
                else args.enable_redeployment,
                "statecode": statecode,
                "statuscode": statuscode,
                "deploymentpipeline_deploymentenvironment": [
                    {
                        "tableLogicalName": "deploymentenvironment",
                        "dataRecordId": env_records[args.dev_environment_key].id,
                    }
                ],
            }
        )
        pipeline_record = _DataRecordWrap(
            f"{name}-pipeline",
            environment_id=args.host_environment_id,
            table_logical_name="deploymentpipeline",
            columns=pipeline_columns,
            disable_on_destroy=True,
            opts=child_opts,
        )

        stage_records: list[pulumi.CustomResource] = []
        previous_stage = None
        for index, stage_cfg in enumerate(args.pipeline_stages):
            target_env = args.environments[stage_cfg.environment_key]
            stage_columns = {
                "deploymentpipelineid": {
                    "tableLogicalName": "deploymentpipeline",
                    "dataRecordId": pipeline_record.id,
                },
                "description": stage_cfg.description,
                "isdelegateddeployment": bool(stage_cfg.use_delegated_deployment),
                "issharingenabled": True
                if stage_cfg.is_sharing_enabled is None
                else stage_cfg.is_sharing_enabled,
                "name": target_env.name,
                "predeploymentsteprequired": True
                if stage_cfg.require_predeployment_approval is True
                else False,
                "preexportsteprequired": bool(stage_cfg.require_preexport_approval)
                if index == 0
                else False,
                "spnclientid": stage_cfg.deployment_spn_client_id,
                "statecode": statecode,
                "statuscode": statuscode,
                "targetdeploymentenvironmentid": {
                    "tableLogicalName": "deploymentenvironment",
                    "dataRecordId": env_records[stage_cfg.environment_key].id,
                },
            }
            if previous_stage is not None:
                stage_columns["previousdeploymentstageid"] = {
                    "tableLogicalName": "deploymentstage",
                    "dataRecordId": previous_stage.id,
                }

            stage_record = _DataRecordWrap(
                f"{name}-stage-{index}",
                environment_id=args.host_environment_id,
                table_logical_name="deploymentstage",
                columns=_omit_none(stage_columns),
                disable_on_destroy=True,
                opts=child_opts,
            )
            stage_records.append(stage_record)
            previous_stage = stage_record

        team_record = None
        if args.security_group_id is not None:
            team_record = _DataRecordWrap(
                f"{name}-team",
                environment_id=args.host_environment_id,
                table_logical_name="team",
                columns=_omit_none(
                    {
                        "name": f"{args.pipeline_name} - Deployment Pipeline Users",
                        "teamtype": 2,
                        "membershiptype": 0,
                        "azureactivedirectoryobjectid": args.security_group_id,
                        "businessunitid": {
                            "tableLogicalName": "businessunit",
                            "dataRecordId": args.root_business_unit_id,
                        },
                        "teamroles_association": [
                            {
                                "tableLogicalName": "role",
                                "dataRecordId": args.deployment_pipeline_user_role_id,
                            }
                        ],
                    }
                ),
                disable_on_destroy=True,
                opts=child_opts,
            )
            _PipelineSharingWrap(
                f"{name}-sharing",
                environment_id=args.host_environment_id,
                pipeline_id=pipeline_record.id,
                team_id=team_record.id,
                opts=pulumi.ResourceOptions(
                    parent=self,
                    providers=(opts.providers if opts else None),
                    provider=(opts.provider if opts else None),
                    depends_on=[pipeline_record, team_record],
                ),
            )

        self.resource_id = pipeline_record.id
        self.pipeline_id = pipeline_record.id
        self.pipeline_name = pulumi.Output.from_input(args.pipeline_name)
        self.deployment_environment_ids = pulumi.Output.all(
            **{key: record.id for key, record in env_records.items()}
        ).apply(lambda d: d)
        self.deployment_stage_ids = pulumi.Output.all(
            **{
                args.pipeline_stages[index].environment_key: stage.id
                for index, stage in enumerate(stage_records)
            }
        ).apply(lambda d: d)
        self.pipeline_team_id = (
            team_record.id if team_record is not None else pulumi.Output.from_input("")
        )
        self.register_outputs(
            {
                "resourceId": self.resource_id,
                "pipelineId": self.pipeline_id,
                "pipelineName": self.pipeline_name,
                "deploymentEnvironmentIds": self.deployment_environment_ids,
                "deploymentStageIds": self.deployment_stage_ids,
                "pipelineTeamId": self.pipeline_team_id,
            }
        )


@register_construct(COMPONENT_TYPE)
async def _construct_res_deployment_pipeline(
    name: str,
    inputs: dict,
    opts: Optional[pulumi.ResourceOptions],
) -> object:
    """Async factory for :class:`ResDeploymentPipeline`."""
    from pulumi.provider.experimental.property_value import Computed, PropertyValue  # noqa: PLC0415
    from pulumi.provider.experimental.provider import ConstructResponse  # noqa: PLC0415

    from ..construct_bridge import pv_to_input, resolve_outputs  # noqa: PLC0415

    def _pv(key: str, default=None):
        return pv_to_input(inputs.get(key, PropertyValue(default)))

    def _pv_bool(key: str) -> Optional[bool]:
        pv = inputs.get(key)
        if pv is None:
            return None
        value = pv.value
        return value if isinstance(value, bool) else None

    def _pv_str_concrete(key: str) -> Optional[str]:
        pv = inputs.get(key)
        if pv is None:
            return None
        value = pv.value
        if value is None or isinstance(value, Computed):
            return None
        return str(value)

    def _nested_input(mapping, key: str, default=None):
        return pv_to_input(mapping.get(key, PropertyValue(default)))

    def _nested_bool(mapping, key: str) -> Optional[bool]:
        pv = mapping.get(key)
        if pv is None:
            return None
        value = pv.value
        return value if isinstance(value, bool) else None

    def _nested_str_concrete(mapping, key: str) -> Optional[str]:
        pv = mapping.get(key)
        if pv is None:
            return None
        value = pv.value
        if value is None or isinstance(value, Computed):
            return None
        return str(value)

    environments_input = inputs.get("environments")
    raw_environments = environments_input.value if environments_input is not None else None
    if raw_environments is None or isinstance(raw_environments, Computed) or not hasattr(raw_environments, "items"):
        raise ValueError("environments keys must be known at plan time.")

    environments: dict[str, PipelineEnvironmentEntry] = {}
    for env_key, env_value in raw_environments.items():
        if not isinstance(env_key, str):
            raise ValueError("environments keys must be strings.")
        entry_map = env_value.value if isinstance(env_value, PropertyValue) else env_value
        if entry_map is None or isinstance(entry_map, Computed) or not hasattr(entry_map, "get"):
            raise ValueError(f"Environment entry {env_key!r} must be a concrete object.")
        environments[env_key] = PipelineEnvironmentEntry(
            id=_nested_input(entry_map, "id"),
            name=_nested_input(entry_map, "name"),
        )

    stages_input = inputs.get("pipelineStages")
    raw_stages = stages_input.value if stages_input is not None else None
    if raw_stages is None or isinstance(raw_stages, Computed) or not isinstance(raw_stages, (list, tuple)):
        raise ValueError("pipelineStages must be a concrete list.")

    pipeline_stages: list[PipelineStageConfig] = []
    for index, stage_value in enumerate(raw_stages):
        stage_map = stage_value.value if isinstance(stage_value, PropertyValue) else stage_value
        if stage_map is None or isinstance(stage_map, Computed) or not hasattr(stage_map, "get"):
            raise ValueError(f"pipelineStages[{index}] must be a concrete object.")
        environment_key = _nested_str_concrete(stage_map, "environmentKey")
        if not environment_key:
            raise ValueError("pipelineStages[*].environmentKey must be known at plan time.")
        pipeline_stages.append(
            PipelineStageConfig(
                environment_key=environment_key,
                description=_nested_input(stage_map, "description"),
                deployment_spn_client_id=_nested_input(stage_map, "deploymentSpnClientId"),
                is_sharing_enabled=_nested_bool(stage_map, "isSharingEnabled"),
                require_predeployment_approval=_nested_bool(stage_map, "requirePredeploymentApproval"),
                require_preexport_approval=_nested_bool(stage_map, "requirePreexportApproval"),
                use_delegated_deployment=_nested_bool(stage_map, "useDelegatedDeployment"),
            )
        )

    args = ResDeploymentPipelineArgs(
        host_environment_id=_pv("hostEnvironmentId"),
        pipeline_name=_pv_str_concrete("pipelineName") or "",
        environments=environments,
        dev_environment_key=_pv_str_concrete("devEnvironmentKey") or "",
        pipeline_stages=pipeline_stages,
        security_group_id=_pv_str_concrete("securityGroupId"),
        root_business_unit_id=_pv("rootBusinessUnitId"),
        deployment_pipeline_user_role_id=_pv("deploymentPipelineUserRoleId"),
        lifecycle_state=_pv_str_concrete("lifecycleState"),
        pipeline_description=_pv("pipelineDescription"),
        enable_ai_deployment_notes=_pv_bool("enableAiDeploymentNotes"),
        enable_redeployment=_pv_bool("enableRedeployment"),
        enable_telemetry=_pv_bool("enableTelemetry"),
    )

    comp = ResDeploymentPipeline(name, args=args, opts=opts)
    urn = await comp.urn.future()
    state = await resolve_outputs(
        {
            "resourceId": comp.resource_id,
            "pipelineId": comp.pipeline_id,
            "pipelineName": comp.pipeline_name,
            "deploymentEnvironmentIds": comp.deployment_environment_ids,
            "deploymentStageIds": comp.deployment_stage_ids,
            "pipelineTeamId": comp.pipeline_team_id,
        }
    )
    return ConstructResponse(urn=urn, state=state, state_dependencies={})


def _omit_none(values: dict) -> dict:
    return {key: value for key, value in values.items() if value is not None}
