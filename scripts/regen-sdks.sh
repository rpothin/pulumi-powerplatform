#!/usr/bin/env bash
# Regenerate all non-Python SDKs from schema.json, applying the same
# normalization steps that the sdk-sync-check CI job runs.
#
# CI pins Pulumi CLI v3.230.0 for deterministic output. Install before running:
#   curl -fsSL https://get.pulumi.com | sh -s -- --version 3.230.0
#   export PATH="$HOME/.pulumi/bin:$PATH"

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

EXPECTED_PULUMI_VERSION="v3.230.0"
ACTUAL_PULUMI_VERSION=$(pulumi version 2>/dev/null || echo "not installed")
if [ "$ACTUAL_PULUMI_VERSION" != "$EXPECTED_PULUMI_VERSION" ]; then
  echo "ERROR: Pulumi CLI $EXPECTED_PULUMI_VERSION is required for deterministic SDK output." >&2
  echo "  Installed: $ACTUAL_PULUMI_VERSION" >&2
  echo "  Install:   curl -fsSL https://get.pulumi.com | sh -s -- --version 3.230.0 && export PATH=\"\$HOME/.pulumi/bin:\$PATH\"" >&2
  exit 1
fi

# Back up go.mod and go.sum — pulumi package gen-sdk overwrites them but
# they are manually maintained and must be preserved.
GO_BACKUP=$(mktemp -d)
cp sdk/go/powerplatform/go.mod "$GO_BACKUP/go.mod"
cp sdk/go/powerplatform/go.sum  "$GO_BACKUP/go.sum"

restore_go_files() {
  cp "$GO_BACKUP/go.mod" sdk/go/powerplatform/go.mod || true
  cp "$GO_BACKUP/go.sum"  sdk/go/powerplatform/go.sum || true
  rm -rf "$GO_BACKUP"
}
trap restore_go_files EXIT

pulumi package gen-sdk . --language nodejs --out sdk
pulumi package gen-sdk . --language go     --out sdk
pulumi package gen-sdk . --language dotnet --out sdk
pulumi package gen-sdk . --language java   --out sdk

python3 scripts/patch-java-pom-metadata.py
bash scripts/normalize-dotnet-sdk.sh sdk/dotnet
python3 scripts/normalize-nodejs-sdk.py sdk/nodejs

echo ""
echo "✓ SDKs regenerated. Stage sdk/ together with schema.json in the same commit:"
echo "  git add sdk/ schema.json"
