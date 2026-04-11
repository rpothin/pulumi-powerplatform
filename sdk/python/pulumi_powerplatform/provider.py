"""Power Platform Pulumi provider resource."""

import pulumi


class Provider(pulumi.ProviderResource):
    """The provider for Power Platform resources."""

    tenant_id: pulumi.Output[str]
    client_id: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        tenant_id: str = None,
        client_id: str = None,
        client_secret: str = None,
        opts: pulumi.ResourceOptions = None,
    ):
        props = {
            "tenantId": tenant_id,
            "clientId": client_id,
            "clientSecret": client_secret,
        }
        super().__init__("powerplatform", resource_name, props, opts)
