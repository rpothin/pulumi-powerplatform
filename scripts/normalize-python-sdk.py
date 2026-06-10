#!/usr/bin/env python3
"""Remove generator artifacts that conflict with the hand-maintained pyproject.toml.

The Pulumi SDK generator creates setup.py with a hardcoded VERSION = "0.0.0"
and no PEP 621 metadata. This project uses pyproject.toml for packaging
instead, so setup.py is removed after generation.

Note: the generated _utilities.py calls _get_semver_version() at module level
(no try/except fallback). This requires parver>=0.2.1 and semver>=2.8.1 to be
installed at import time. These packages are listed in the root pyproject.toml
[project.optional-dependencies] dev section so that tests and CI satisfy the
requirement via `pip install -e ".[dev]"`. Do not remove them from root dev deps.

Usage:
  python3 scripts/normalize-python-sdk.py [sdk/python]   # default: sdk/python
"""

import os
import sys

sdk_python = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(__file__), "..", "sdk", "python"
)
sdk_python = os.path.normpath(sdk_python)

setup_py = os.path.join(sdk_python, "setup.py")
if os.path.exists(setup_py):
    os.remove(setup_py)
    print(f"Removed {setup_py}")
else:
    print(f"Nothing to remove at {setup_py}")
