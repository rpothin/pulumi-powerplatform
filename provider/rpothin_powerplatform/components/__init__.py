"""Power Platform Pulumi Component Resources.

Components live under the ``powerplatform:components:*`` token namespace and are
embedded directly in this provider package (Option A+).  They are dispatched via
the provider's ``construct`` method without touching the CRUD/invoke handlers.

Importing this package triggers all ``@register_component`` and
``@register_construct`` decorators, populating the schema-generation and
runtime-dispatch registries in :mod:`._base`.

Auto-discovery mirrors :func:`scripts.merge_schema.load_components_isolated`: every
public ``.py`` module in this directory (not starting with ``_``) is imported so
that adding a new component file is sufficient to register it for both schema
generation and runtime dispatch — no manual listing required.
"""

import importlib
from pathlib import Path

from .res_deployment_pipeline import ResDeploymentPipeline  # noqa: F401

_here = Path(__file__).parent
for _py_file in sorted(_here.glob("*.py")):
    _stem = _py_file.stem
    if not _stem.startswith("_"):
        importlib.import_module(f".{_stem}", package=__name__)
