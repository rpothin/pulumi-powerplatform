"""Shared utility functions for the Power Platform provider."""

from __future__ import annotations

from typing import Optional

from pulumi.provider.experimental.property_value import PropertyValue


def pv_str(pv: Optional[PropertyValue]) -> Optional[str]:
    """Extract a string from a PropertyValue, returning None if null/missing."""
    if pv is None or pv.value is None:
        return None
    return str(pv.value)
