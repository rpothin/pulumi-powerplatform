#!/usr/bin/env bash
set -euo pipefail

DOTNET_SDK_DIR="${1:?usage: normalize-dotnet-sdk.sh <dotnet-sdk-dir>}"

sed -i 's#<TargetFramework>net6.0</TargetFramework>#<TargetFramework>net8.0</TargetFramework>#' \
  "$DOTNET_SDK_DIR/Pulumi.Powerplatform.csproj"

cat > "$DOTNET_SDK_DIR/global.json" <<'EOF'
{
  "sdk": {
    "version": "8.0.0",
    "rollForward": "latestMajor",
    "allowPrerelease": false
  }
}
EOF
