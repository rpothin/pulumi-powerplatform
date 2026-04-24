#!/usr/bin/env python3
"""Add manually-maintained npm fields to a generated Node.js SDK package.json.

pulumi-gen-nodejs does not emit the ``main``, ``types``, or ``files`` fields.
These fields are required for correct npm packaging and are maintained by hand
in the committed sdk/nodejs/package.json. This script injects them into the
generated copy so that the sdk-sync-check diff passes.

Usage:
    python3 scripts/normalize-nodejs-sdk.py <nodejs-sdk-dir>
"""

import json
import sys
from pathlib import Path

NODEJS_SDK_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None

if NODEJS_SDK_DIR is None:
    print("usage: normalize-nodejs-sdk.py <nodejs-sdk-dir>", file=sys.stderr)
    sys.exit(1)

pkg_path = NODEJS_SDK_DIR / "package.json"
if not pkg_path.exists():
    print(f"ERROR: {pkg_path} not found", file=sys.stderr)
    sys.exit(1)

with pkg_path.open(encoding="utf-8") as f:
    pkg = json.load(f)

# Insert the manually-maintained fields after "license" so the key order
# matches the hand-edited committed file.
updated = {}
for key, value in pkg.items():
    updated[key] = value
    if key == "license":
        updated["main"] = "bin/index.js"
        updated["types"] = "bin/index.d.ts"
        updated["files"] = ["bin"]

if updated == pkg:
    print(f"normalize-nodejs-sdk: fields already present in {pkg_path}")
    sys.exit(0)

with pkg_path.open("w", encoding="utf-8") as f:
    json.dump(updated, f, indent=4)
    f.write("\n")

print(f"normalize-nodejs-sdk: injected main/types/files into {pkg_path}")
