"""Shared utility functions for the Power Platform provider."""

from __future__ import annotations

import json
from typing import Any, Optional

from pulumi.provider.experimental.property_value import PropertyValue


def pv_str(pv: Optional[PropertyValue]) -> Optional[str]:
    """Extract a string from a PropertyValue, returning None if null/missing."""
    if pv is None or pv.value is None:
        return None
    return str(pv.value)


def pv_to_comparable(pv: Optional[PropertyValue]) -> str:
    """Convert a PropertyValue to a stable JSON string for deep equality comparison.

    This handles nested dicts and lists of PropertyValue objects, which
    ``PropertyValue.__eq__`` may not compare structurally.
    """
    return json.dumps(_pv_to_python(pv), sort_keys=True, default=str)


def _pv_to_python(pv: Optional[PropertyValue]) -> Any:
    """Recursively convert a PropertyValue to a plain Python value."""
    if pv is None or pv.value is None:
        return None
    val = pv.value
    if isinstance(val, (str, bool, float, int)):
        return val
    if isinstance(val, list):
        return [_pv_to_python(item) for item in val]
    if isinstance(val, dict):
        return {k: _pv_to_python(v) for k, v in val.items()}
    return val
