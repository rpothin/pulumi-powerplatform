"""Tests for the Pulumi provider entry point."""

from pathlib import Path

from rpothin_powerplatform.__main__ import VERSION


def test_provider_version_uses_release_placeholder() -> None:
    """The release workflow must replace the provider's development version."""
    assert VERSION == "0.0.0"


def test_release_workflow_substitutes_provider_version() -> None:
    """Provider archives must advertise the same version as their release tag."""
    workflow = Path(__file__).parents[1] / ".github" / "workflows" / "release.yaml"
    content = workflow.read_text(encoding="utf-8")
    assert 'sed -i "s/0\\.0\\.0/$VERSION/g" provider/rpothin_powerplatform/__main__.py' in content
