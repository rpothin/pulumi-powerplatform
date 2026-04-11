"""Entry point for the Pulumi Power Platform provider gRPC server."""

import sys

from pulumi.provider.experimental.server import main as serve

from pulumi_powerplatform.provider import PowerPlatformProvider

VERSION = "0.1.0"


def main():
    """Start the provider gRPC server."""
    serve(sys.argv[1:], VERSION, PowerPlatformProvider())


if __name__ == "__main__":
    main()
