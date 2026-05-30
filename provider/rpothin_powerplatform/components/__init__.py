"""Power Platform Pulumi Component Resources.

Components live under the ``powerplatform:components:*`` token namespace and are
embedded directly in this provider package (Option A+).  They are dispatched via
the provider's ``construct`` method without touching the CRUD/invoke handlers.
"""
