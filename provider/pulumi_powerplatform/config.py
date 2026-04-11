"""Provider configuration handling for the Power Platform Pulumi provider.

Resolves credentials from Pulumi config args and environment variables, then
constructs an authenticated ``PowerPlatformClient``.
"""

from __future__ import annotations

from typing import Optional

from pulumi.provider.experimental.property_value import PropertyValue

from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.utils import pv_str


def resolve_client(args: dict[str, PropertyValue]) -> PowerPlatformClient:
    """Build a ``PowerPlatformClient`` from Pulumi configuration arguments.

    The following resolution order is used for each credential:

    1. Explicit value from ``args`` (Pulumi config).
    2. Environment variable (``AZURE_TENANT_ID``, ``AZURE_CLIENT_ID``,
       ``AZURE_CLIENT_SECRET``).
    3. ``DefaultAzureCredential`` fallback (handled inside ``PowerPlatformClient``).

    Parameters
    ----------
    args:
        The ``ConfigureRequest.args`` dictionary containing Pulumi config values.

    Returns
    -------
    PowerPlatformClient
        A fully authenticated client ready for SDK calls.
    """
    tenant_id: Optional[str] = pv_str(args.get("tenantId"))
    client_id: Optional[str] = pv_str(args.get("clientId"))
    client_secret: Optional[str] = pv_str(args.get("clientSecret"))

    return PowerPlatformClient(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_secret,
    )
