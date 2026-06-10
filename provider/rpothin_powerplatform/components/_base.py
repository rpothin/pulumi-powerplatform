"""AVM component base: shared conventions, registries, and base Args class.

All AVM components in this package MUST:
  - Define an Args class that inherits from :class:`ComponentArgs`
  - Decorate the class with :func:`register_component` (schema generation)
  - Provide an async factory function decorated with
    :func:`register_construct` (runtime dispatch)

Token naming convention: ``powerplatform:components:<ClassName>``
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

#: Namespace prefix for all component resource tokens.
COMPONENT_TOKEN_PREFIX = "powerplatform:components:"

# ---------------------------------------------------------------------------
# Runtime construct dispatch registry
# ---------------------------------------------------------------------------

#: Maps component token → async factory ``(name, inputs, opts) → ConstructResponse``.
_CONSTRUCT_REGISTRY: dict[str, Callable] = {}


def register_construct(token: str) -> Callable:
    """Register an async factory function for the given component token.

    The factory receives ``(name: str, inputs: dict[str, PropertyValue],
    opts: ResourceOptions | None)`` and must return a ``ConstructResponse``.
    """
    def decorator(fn: Callable) -> Callable:
        _CONSTRUCT_REGISTRY[token] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Schema-generation registry (used by merge-schema.py)
# ---------------------------------------------------------------------------

#: Component classes to be analyzed by :mod:`pulumi.provider.experimental.analyzer`.
_ANALYZER_REGISTRY: list[type] = []


def register_component(cls: type) -> type:
    """Register a :class:`~pulumi.ComponentResource` subclass for schema generation."""
    _ANALYZER_REGISTRY.append(cls)
    return cls


# ---------------------------------------------------------------------------
# AVM base Args class
# ---------------------------------------------------------------------------

@dataclass(kw_only=True)
class ComponentArgs:
    """Base args class for all AVM components.

    The ``enable_telemetry`` field is inherited by every subclass and
    propagates automatically into the generated Pulumi schema because
    :class:`~pulumi.provider.experimental.analyzer.Analyzer` walks the full
    MRO when collecting property annotations.
    """

    enable_telemetry: Optional[bool] = None
    """Whether to enable telemetry for the component. Defaults to ``True`` at
    runtime if not explicitly set."""
