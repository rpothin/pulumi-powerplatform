"""Shared DLP serialization helpers for getDlpPolicies and getDlpPolicyMigrationConfig."""

from __future__ import annotations

from typing import Any

from pulumi.provider.experimental.property_value import PropertyValue


def dict_to_pv_map(data: dict[str, Any]) -> dict[str, PropertyValue]:
    """Recursively convert a Python dict to a PropertyValue map."""
    return {k: python_to_pv(v) for k, v in data.items()}


def python_to_pv(val: Any) -> PropertyValue:
    """Recursively convert a Python value to a PropertyValue."""
    if val is None:
        return PropertyValue(None)
    if isinstance(val, bool):
        return PropertyValue(val)
    if isinstance(val, (int, float)):
        return PropertyValue(float(val))
    if isinstance(val, str):
        return PropertyValue(val)
    if isinstance(val, list):
        return PropertyValue([python_to_pv(item) for item in val])
    if isinstance(val, dict):
        return PropertyValue(dict_to_pv_map(val))
    return PropertyValue(str(val))


def rule_set_to_pv(rs: object) -> PropertyValue:
    """Convert a RuleSet SDK object to a PropertyValue map preserving id, version, and inputs."""
    rs_map: dict[str, PropertyValue] = {}
    rs_id = getattr(rs, "id", None)
    if rs_id is not None:
        rs_map["id"] = PropertyValue(rs_id)
    rs_version = getattr(rs, "version", None)
    if rs_version is not None:
        rs_map["version"] = PropertyValue(rs_version)
    rs_inputs = getattr(rs, "inputs", None)
    if rs_inputs is not None:
        additional = getattr(rs_inputs, "additional_data", None)
        if additional is not None:
            rs_map["inputs"] = PropertyValue(dict_to_pv_map(additional))
    return PropertyValue(rs_map)
