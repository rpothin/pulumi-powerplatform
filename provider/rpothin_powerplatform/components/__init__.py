"""Power Platform Pulumi Component Resources.

Components live under the ``powerplatform:components:*`` token namespace and are
embedded directly in this provider package (Option A+).  They are dispatched via
the provider's ``construct`` method without touching the CRUD/invoke handlers.

Importing this package triggers all ``@register_component`` and
``@register_construct`` decorators, populating the schema-generation and
runtime-dispatch registries in :mod:`._base`.
"""

# Import all component modules to register them.  New components added here
# automatically appear in both schema generation and runtime dispatch.
from . import poc_component as _poc_component  # noqa: F401
