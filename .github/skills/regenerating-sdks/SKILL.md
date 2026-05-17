---
name: regenerating-sdks
description: >
  Regenerates non-Python SDKs (nodejs, go, dotnet, java) after schema.json changes
  in the rpothin/pulumi-powerplatform repository. Must be invoked whenever schema.json
  is modified to ensure the sdk-sync-check CI job passes. Handles normalization of the
  dotnet and nodejs SDKs, go.mod/go.sum preservation, and Java POM metadata patching
  via a single helper script. Key terms: schema.json, SDK regeneration, sdk-sync-check.
allowed-tools: [shell]
---

## When to invoke

Any time `schema.json` is modified. The `sdk-sync-check` CI job will fail if the
non-Python SDKs are not regenerated and committed in the same commit.

## Version requirement

CI pins Pulumi CLI **v3.230.0** for deterministic output. Install before running:

```bash
curl -fsSL https://get.pulumi.com | sh -s -- --version 3.230.0
export PATH="$HOME/.pulumi/bin:$PATH"
```

## How to run

From the repo root:

```bash
bash scripts/regen-sdks.sh
```

The script: backs up and restores `sdk/go/powerplatform/go.mod` and `go.sum`,
runs `pulumi package gen-sdk` for all four languages, then applies
`normalize-dotnet-sdk.sh`, `normalize-nodejs-sdk.py`, and `patch-java-pom-metadata.py`.

## Same-commit invariant

The regenerated `sdk/` files **must** be staged and committed in the **same commit**
as the `schema.json` change — never in a separate commit.

```bash
git add sdk/ schema.json
git commit -m "feat: ..."
```

## What NOT to regenerate

`sdk/python/` is manually maintained. Never run gen-sdk for Python.
