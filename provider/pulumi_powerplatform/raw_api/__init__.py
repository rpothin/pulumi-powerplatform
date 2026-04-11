"""Raw REST API module for Power Platform SDK gaps.

This module provides direct HTTP access via the Kiota ``HttpxRequestAdapter`` for
operations not yet exposed by the ``powerplatform-management`` SDK.  Known gaps
include:

- Environment creation / lifecycle management
- Environment update (properties, settings)
- Tenant Settings
- Solution Management
- Data Records (Dataverse)

Use ``RawApiClient`` when the SDK does not provide a suitable request builder.
"""

from pulumi_powerplatform.raw_api.client import RawApiClient

__all__ = ["RawApiClient"]
