"""Example: provision a deployment pipeline using ResDeploymentPipeline component."""

import pulumi
import rpothin_powerplatform as pp

pipeline = pp.components.ResDeploymentPipeline(
    "demo-pipeline",
    args=pp.components.ResDeploymentPipelineArgs(
        host_environment_id="<host-environment-id>",
        pipeline_name="DemoPipeline",
        pipeline_description="Demo deployment pipeline",
        dev_environment_key="dev",
        environments={
            "dev": pp.components.PipelineEnvironmentEntryArgs(
                id="<dev-environment-id>",
                name="Development",
            ),
            "test": pp.components.PipelineEnvironmentEntryArgs(
                id="<test-environment-id>",
                name="Test",
            ),
        },
        pipeline_stages=[
            pp.components.PipelineStageConfigArgs(
                environment_key="test",
                description="Promote to test",
            ),
        ],
    ),
)

pulumi.export("pipeline_id", pipeline.resource_id)
