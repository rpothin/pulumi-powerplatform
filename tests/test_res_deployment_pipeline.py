"""Tests for the ``ResDeploymentPipeline`` component resource."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pulumi.runtime.mocks as mocks_module
import pytest
from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import ConstructResponse
from rpothin_powerplatform.utils import pv_to_python

sys.path.insert(0, "provider")
from rpothin_powerplatform.components._base import (  # noqa: E402
    _ANALYZER_REGISTRY,
    _CONSTRUCT_REGISTRY,
)
from rpothin_powerplatform.components.res_deployment_pipeline import (  # noqa: E402
    COMPONENT_TYPE,
    PipelineEnvironmentEntry,
    PipelineStageConfig,
    ResDeploymentPipeline,
    ResDeploymentPipelineArgs,
    _construct_res_deployment_pipeline,
)


class _RecordingMocks(mocks_module.Mocks):
    def __init__(self) -> None:
        self.resources = []

    def new_resource(self, args):
        self.resources.append({"type": args.typ, "name": args.name, "inputs": args.inputs})
        return f"{args.name}_id", args.inputs

    def call(self, args):
        return {}, []


@pytest.fixture
async def pulumi_mocks():
    recorder = _RecordingMocks()
    mocks_module.set_mocks(recorder, preview=False)
    return recorder


class TestResDeploymentPipelineArgs:
    def test_enable_telemetry_inherited_from_base(self):
        args = ResDeploymentPipelineArgs(
            host_environment_id="host-env",
            pipeline_name="Pipeline",
            environments={"dev": PipelineEnvironmentEntry(id="env-dev", name="Dev")},
            dev_environment_key="dev",
            pipeline_stages=[PipelineStageConfig(environment_key="test")],
        )
        assert args.enable_telemetry is None

    def test_no_future_annotations(self):
        for dataclass_type in (
            PipelineEnvironmentEntry,
            PipelineStageConfig,
            ResDeploymentPipelineArgs,
        ):
            for field in dataclass_type.__dataclass_fields__.values():
                assert not isinstance(field.type, str)


class TestResDeploymentPipelineRegistration:
    def test_component_registered(self):
        assert COMPONENT_TYPE == "powerplatform:components:ResDeploymentPipeline"
        assert COMPONENT_TYPE in _CONSTRUCT_REGISTRY
        assert _CONSTRUCT_REGISTRY[COMPONENT_TYPE] is _construct_res_deployment_pipeline
        assert ResDeploymentPipeline in _ANALYZER_REGISTRY

    def test_schema_contains_component_and_related_tokens(self):
        schema = json.loads(Path("schema.json").read_text(encoding="utf-8"))
        assert "powerplatform:components:ResDeploymentPipeline" in schema["resources"]
        assert "powerplatform:index:PipelineSharing" in schema["resources"]
        assert "powerplatform:index:getSecurityRoles" in schema["functions"]
        assert "powerplatform:index:SecurityRole" in schema["types"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("pulumi_mocks")
class TestConstructResDeploymentPipeline:
    @staticmethod
    def _inputs(with_security_group: bool = True):
        inputs = {
            "hostEnvironmentId": PropertyValue("host-env"),
            "pipelineName": PropertyValue("My Pipeline"),
            "environments": PropertyValue(
                {
                    "dev": PropertyValue(
                        {"id": PropertyValue("env-dev"), "name": PropertyValue("Development")}
                    ),
                    "test": PropertyValue(
                        {"id": PropertyValue("env-test"), "name": PropertyValue("Test")}
                    ),
                    "prod": PropertyValue(
                        {"id": PropertyValue("env-prod"), "name": PropertyValue("Production")}
                    ),
                }
            ),
            "devEnvironmentKey": PropertyValue("dev"),
            "pipelineStages": PropertyValue(
                [
                    PropertyValue(
                        {
                            "environmentKey": PropertyValue("test"),
                            "description": PropertyValue("Deploy to test"),
                            "deploymentSpnClientId": PropertyValue("spn-123"),
                            "requirePreexportApproval": PropertyValue(True),
                            "useDelegatedDeployment": PropertyValue(True),
                        }
                    ),
                    PropertyValue(
                        {
                            "environmentKey": PropertyValue("prod"),
                            "description": PropertyValue("Deploy to prod"),
                            "isSharingEnabled": PropertyValue(False),
                            "requirePredeploymentApproval": PropertyValue(True),
                        }
                    ),
                ]
            ),
            "lifecycleState": PropertyValue("inactive"),
            "pipelineDescription": PropertyValue("Pipeline description"),
            "enableAiDeploymentNotes": PropertyValue(False),
            "enableRedeployment": PropertyValue(True),
        }
        if with_security_group:
            inputs.update(
                {
                    "securityGroupId": PropertyValue("group-1"),
                    "rootBusinessUnitId": PropertyValue("root-bu"),
                    "deploymentPipelineUserRoleId": PropertyValue("role-1"),
                }
            )
        return inputs

    async def test_returns_construct_response(self):
        result = await _construct_res_deployment_pipeline("pipe", self._inputs(), opts=None)
        state = {key: pv_to_python(value) for key, value in result.state.items()}
        assert isinstance(result, ConstructResponse)
        assert state["resourceId"] == "pipe-pipeline_id"
        assert state["pipelineId"] == "pipe-pipeline_id"
        assert state["pipelineName"] == "My Pipeline"
        assert state["pipelineTeamId"] == "pipe-team_id"
        assert state["deploymentEnvironmentIds"] == {
            "dev": "pipe-deployment-environment-dev_id",
            "test": "pipe-deployment-environment-test_id",
            "prod": "pipe-deployment-environment-prod_id",
        }
        assert state["deploymentStageIds"] == {
            "test": "pipe-stage-0_id",
            "prod": "pipe-stage-1_id",
        }

    async def test_construct_creates_expected_child_resources(self, pulumi_mocks):
        await _construct_res_deployment_pipeline("pipe", self._inputs(), opts=None)

        data_records = [r for r in pulumi_mocks.resources if r["type"] == "powerplatform:index:DataRecord"]
        sharing = [r for r in pulumi_mocks.resources if r["type"] == "powerplatform:index:PipelineSharing"]
        assert len(data_records) == 7
        assert len(sharing) == 1

        env_dev = next(r for r in data_records if r["name"] == "pipe-deployment-environment-dev")
        env_test = next(r for r in data_records if r["name"] == "pipe-deployment-environment-test")
        pipeline = next(r for r in data_records if r["name"] == "pipe-pipeline")
        stage0 = next(r for r in data_records if r["name"] == "pipe-stage-0")
        stage1 = next(r for r in data_records if r["name"] == "pipe-stage-1")
        team = next(r for r in data_records if r["name"] == "pipe-team")

        assert env_dev["inputs"]["disableOnDestroy"] is True
        assert env_dev["inputs"]["columns"]["environmenttype"] == 200000000
        assert env_test["inputs"]["columns"]["environmenttype"] == 200000001
        assert pipeline["inputs"]["columns"]["deploymentpipeline_deploymentenvironment"][0]["dataRecordId"] == (
            "pipe-deployment-environment-dev_id"
        )
        assert pipeline["inputs"]["columns"]["statecode"] == 1
        assert pipeline["inputs"]["columns"]["statuscode"] == 2
        assert pipeline["inputs"]["columns"]["enableaideploymentnotes"] is False
        assert stage0["inputs"]["columns"]["preexportsteprequired"] is True
        assert stage1["inputs"]["columns"]["preexportsteprequired"] is False
        assert stage1["inputs"]["columns"]["previousdeploymentstageid"]["dataRecordId"] == "pipe-stage-0_id"
        assert stage0["inputs"]["columns"]["deploymentpipelineid"]["dataRecordId"] == "pipe-pipeline_id"
        assert stage0["inputs"]["columns"]["targetdeploymentenvironmentid"]["dataRecordId"] == (
            "pipe-deployment-environment-test_id"
        )
        assert team["inputs"]["columns"]["teamroles_association"][0]["dataRecordId"] == "role-1"
        assert sharing[0]["inputs"]["pipelineId"] == "pipe-pipeline_id"
        assert sharing[0]["inputs"]["teamId"] == "pipe-team_id"

    async def test_construct_omits_team_and_sharing_without_security_group(self, pulumi_mocks):
        result = await _construct_res_deployment_pipeline(
            "pipe",
            self._inputs(with_security_group=False),
            opts=None,
        )
        state = {key: pv_to_python(value) for key, value in result.state.items()}

        data_records = [r for r in pulumi_mocks.resources if r["type"] == "powerplatform:index:DataRecord"]
        sharing = [r for r in pulumi_mocks.resources if r["type"] == "powerplatform:index:PipelineSharing"]
        assert len(data_records) == 6
        assert sharing == []
        assert state["pipelineTeamId"] == ""


@pytest.mark.asyncio
@pytest.mark.usefixtures("pulumi_mocks")
class TestResDeploymentPipelineValidation:
    @staticmethod
    def _base_args() -> ResDeploymentPipelineArgs:
        return ResDeploymentPipelineArgs(
            host_environment_id="host-env",
            pipeline_name="My Pipeline",
            environments={
                "dev": PipelineEnvironmentEntry(id="env-dev", name="Development"),
                "test": PipelineEnvironmentEntry(id="env-test", name="Test"),
            },
            dev_environment_key="dev",
            pipeline_stages=[PipelineStageConfig(environment_key="test")],
        )

    async def test_rejects_missing_dev_environment_key(self):
        args = self._base_args()
        args.dev_environment_key = "missing"
        with pytest.raises(ValueError, match="dev_environment_key"):
            ResDeploymentPipeline("bad", args=args)

    async def test_rejects_delegated_deployment_without_spn(self):
        args = self._base_args()
        args.pipeline_stages = [
            PipelineStageConfig(environment_key="test", use_delegated_deployment=True)
        ]
        with pytest.raises(ValueError, match="deployment_spn_client_id"):
            ResDeploymentPipeline("bad", args=args)

    async def test_rejects_security_group_without_role_inputs(self):
        args = self._base_args()
        args.security_group_id = "group-1"
        with pytest.raises(ValueError, match="root_business_unit_id"):
            ResDeploymentPipeline("bad", args=args)

    async def test_rejects_more_than_six_stages(self):
        args = ResDeploymentPipelineArgs(
            host_environment_id="host-env",
            pipeline_name="My Pipeline",
            environments={
                "dev": PipelineEnvironmentEntry(id="env-dev", name="Development"),
                **{
                    f"stage{i}": PipelineEnvironmentEntry(id=f"env-{i}", name=f"Stage {i}")
                    for i in range(7)
                },
            },
            dev_environment_key="dev",
            pipeline_stages=[
                PipelineStageConfig(environment_key=f"stage{i}")
                for i in range(7)
            ],
        )
        with pytest.raises(ValueError, match="between 1 and 6"):
            ResDeploymentPipeline("bad", args=args)

    async def test_rejects_computed_security_group_id(self):
        from pulumi.provider.experimental.property_value import Computed

        inputs = dict(TestConstructResDeploymentPipeline._inputs())
        inputs["securityGroupId"] = PropertyValue(Computed())
        with pytest.raises(ValueError, match="securityGroupId"):
            await _construct_res_deployment_pipeline("pipe", inputs, opts=None)


class TestResDeploymentPipelineSchemaSmoke:
    def test_analyzer_can_introspect_component(self):
        try:
            from pulumi.provider.experimental.analyzer import Analyzer  # type: ignore[import]

            analyzer = Analyzer("powerplatform")
            result = analyzer.analyze([ResDeploymentPipeline])
            assert result is not None
        except ImportError:
            pytest.skip("pulumi Analyzer not available in this environment")
