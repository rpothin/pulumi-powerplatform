#!/usr/bin/env python3
"""Remove generator artifacts that conflict with the hand-maintained pyproject.toml.

The Pulumi SDK generator creates setup.py with a hardcoded VERSION = "0.0.0"
and no PEP 621 metadata. This project uses pyproject.toml for packaging
instead, so setup.py is removed after generation.

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
