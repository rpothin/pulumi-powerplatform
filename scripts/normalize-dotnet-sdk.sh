#!/usr/bin/env bash
set -euo pipefail

DOTNET_SDK_DIR="${1:?usage: normalize-dotnet-sdk.sh <dotnet-sdk-dir>}"

sed -i 's#<TargetFramework>net6.0</TargetFramework>#<TargetFramework>net8.0</TargetFramework>#' \
  "$DOTNET_SDK_DIR/Pulumi.Powerplatform.csproj"

# Add PackageId so NuGet uses the Rpothin.Powerplatform identifier
sed -i 's#<GeneratePackageOnBuild>true</GeneratePackageOnBuild>#<GeneratePackageOnBuild>true</GeneratePackageOnBuild>\n    <PackageId>Rpothin.Powerplatform</PackageId>#' \
  "$DOTNET_SDK_DIR/Pulumi.Powerplatform.csproj"

# Rename the csproj to match the NuGet package ID
mv "$DOTNET_SDK_DIR/Pulumi.Powerplatform.csproj" "$DOTNET_SDK_DIR/Rpothin.Powerplatform.csproj"

cat > "$DOTNET_SDK_DIR/global.json" <<'EOF'
{
  "sdk": {
    "version": "8.0.0",
    "rollForward": "latestMajor",
    "allowPrerelease": false
  }
}
EOF
