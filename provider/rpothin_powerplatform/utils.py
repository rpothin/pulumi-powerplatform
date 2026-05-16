"""Shared utility functions for the Power Platform provider."""

from __future__ import annotations

import json
import logging
import random
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, TypeVar

from pulumi.provider.experimental.property_value import PropertyValue

if TYPE_CHECKING:
    from rpothin_powerplatform.raw_api import RawApiClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


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
    if isinstance(val, (list, tuple)):
        return [_pv_to_python(item) for item in val]
    if isinstance(val, Mapping):
        return {k: _pv_to_python(v) for k, v in val.items()}
    return val


# Public alias — import this in new code instead of the private name.
pv_to_python = _pv_to_python


class HttpError(Exception):
    """Represents an HTTP error response with a status code and optional headers."""

    def __init__(
        self,
        status_code: int,
        message: str = "",
        *,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.headers = headers or {}


def _is_retryable(exc: Exception) -> bool:
    """Return True if the exception represents a retryable HTTP error (429 or 5xx)."""
    if isinstance(exc, HttpError):
        return exc.status_code == 429 or 500 <= exc.status_code < 600
    return False


def _get_retry_after(exc: Exception) -> Optional[float]:
    """Extract Retry-After header value (in seconds) from an HttpError, if present."""
    if isinstance(exc, HttpError):
        retry_after = exc.headers.get("Retry-After") or exc.headers.get("retry-after")
        if retry_after is not None:
            try:
                return float(retry_after)
            except ValueError:
                return None
    return None


async def retry_with_backoff(
    fn: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 5,
    base_delay: float = 1.0,
    _sleep: Optional[Callable[[float], Awaitable[None]]] = None,
) -> T:
    """Execute an async function with exponential backoff retry on transient errors.

    Retries on HTTP 429 (rate limit) and 5xx server errors. Respects the
    ``Retry-After`` header when present on 429 responses.

    Parameters
    ----------
    fn:
        An async callable (taking no arguments) to execute.
    max_retries:
        Maximum number of retry attempts (default 5). The function is called
        at most ``max_retries + 1`` times total.
    base_delay:
        Base delay in seconds for exponential backoff (default 1.0).
    _sleep:
        Injectable sleep function for testing. Defaults to ``asyncio.sleep``.
    """
    import asyncio

    sleep = _sleep or asyncio.sleep
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt >= max_retries:
                raise

            # Use Retry-After header if available, otherwise exponential backoff with jitter
            retry_after = _get_retry_after(exc)
            if retry_after is not None:
                delay = retry_after
            else:
                delay = base_delay * (2 ** attempt) + random.uniform(0, base_delay)

            logger.warning(
                "Retryable error (attempt %d/%d, status=%s): %s. Retrying in %.1fs.",
                attempt + 1,
                max_retries + 1,
                getattr(exc, "status_code", "?"),
                exc,
                delay,
            )
            await sleep(delay)

    # Should not reach here, but satisfy type checker
    assert last_exc is not None
    raise last_exc


async def resolve_dataverse_url(raw_client: RawApiClient, env_id: str) -> str:
    """Resolve the Dataverse instance URL for a Power Platform environment.

    Parameters
    ----------
    raw_client:
        A ``RawApiClient`` configured for the BAP admin API.
    env_id:
        The GUID of the environment.

    Returns
    -------
    The Dataverse ``instanceUrl`` (e.g. ``https://org123.crm.dynamics.com/``),
    or an empty string when the environment has no Dataverse instance.
    """
    env = await retry_with_backoff(
        lambda: raw_client.request(
            "GET",
            f"/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/{env_id}",
            api_version="2023-06-01",
        )
    )
    try:
        url: str = env["properties"]["linkedEnvironmentMetadata"]["instanceUrl"]
    except (KeyError, TypeError):
        url = ""
    return url or ""
