"""EnterprisePolicyLink resource handler.

Links an Azure enterprise policy to a Power Platform environment using an
async POST/poll lifecycle.  All properties are immutable — any change
triggers a full replacement (delete-then-create).
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Awaitable, Callable, Optional

from pulumi.provider.experimental.property_value import PropertyValue
from pulumi.provider.experimental.provider import (
    CheckFailure,
    CheckRequest,
    CheckResponse,
    CreateRequest,
    CreateResponse,
    DeleteRequest,
    DiffRequest,
    DiffResponse,
    PropertyDiff,
    PropertyDiffKind,
    ReadRequest,
    ReadResponse,
)

from rpothin_powerplatform.client import PowerPlatformClient
from rpothin_powerplatform.utils import HttpError, retry_with_backoff
from rpothin_powerplatform.utils import pv_str as _pv_str

logger = logging.getLogger(__name__)

_API_VERSION = "2019-10-01"

_LINK_PATH = (
    "/providers/Microsoft.BusinessAppPlatform/scopes/admin"
    "/environments/{env_id}/enterprisePolicies/{policy_type}/link"
)
_UNLINK_PATH = (
    "/providers/Microsoft.BusinessAppPlatform/scopes/admin"
    "/environments/{env_id}/enterprisePolicies/{policy_type}/unlink"
)
_ENV_READ_PATH = (
    "/providers/Microsoft.BusinessAppPlatform/scopes/admin"
    "/environments/{env_id}"
)

# Map policyType → key in the ``enterprisePolicies`` JSON returned by the env API.
_POLICY_TYPE_TO_KEY: dict[str, str] = {
    "NetworkInjection": "vnets",
    "Encryption": "customerManagedKeys",
    "Identity": "identity",
}
_LOWER_TO_POLICY_TYPE: dict[str, str] = {k.lower(): k for k in _POLICY_TYPE_TO_KEY}
_VALID_POLICY_TYPES = frozenset(_POLICY_TYPE_TO_KEY.keys())

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)
# ARM resource path: /regions/{location}/providers/Microsoft.PowerPlatform/enterprisePolicies/{guid}
_SYSTEM_ID_RE = re.compile(
    r"^/regions/[^/\s]+/providers/Microsoft\.PowerPlatform/enterprisePolicies/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)

_MAX_LINK_ATTEMPTS = 5
_POLL_INTERVAL = 10.0
_RETRY_DELAY = 15.0
# Maximum number of polls per operation (default ~10 min at 10s/poll).
_MAX_POLLS = 60


class EnterprisePolicyLinkResource:
    """Handles CRUD for powerplatform:index:EnterprisePolicyLink."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate environmentId, policyType, and systemId."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        policy_type = _pv_str(inputs.get("policyType"))
        system_id = _pv_str(inputs.get("systemId"))

        if not env_id:
            failures.append(
                CheckFailure(
                    property="environmentId",
                    reason="environmentId is required and cannot be empty.",
                )
            )
        elif not _UUID_RE.match(env_id):
            failures.append(
                CheckFailure(
                    property="environmentId",
                    reason=f"environmentId must be a valid UUID/GUID, got: {env_id!r}.",
                )
            )
        else:
            inputs["environmentId"] = PropertyValue(env_id.lower())

        if not policy_type:
            failures.append(
                CheckFailure(
                    property="policyType",
                    reason=f"policyType is required. Valid values: {sorted(_VALID_POLICY_TYPES)}.",
                )
            )
        elif policy_type not in _VALID_POLICY_TYPES:
            failures.append(
                CheckFailure(
                    property="policyType",
                    reason=(
                        f"policyType must be one of {sorted(_VALID_POLICY_TYPES)}, "
                        f"got: {policy_type!r}."
                    ),
                )
            )

        if not system_id:
            failures.append(
                CheckFailure(
                    property="systemId",
                    reason=(
                        "systemId is required. Expected format: "
                        "/regions/{location}/providers/Microsoft.PowerPlatform/"
                        "enterprisePolicies/{guid}."
                    ),
                )
            )
        elif not _SYSTEM_ID_RE.match(system_id):
            failures.append(
                CheckFailure(
                    property="systemId",
                    reason=(
                        f"systemId must match the ARM resource path format "
                        "/regions/{location}/providers/Microsoft.PowerPlatform/"
                        f"enterprisePolicies/{{guid}}, got: {system_id!r}."
                    ),
                )
            )

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """All properties are immutable — any change triggers replacement."""
        diffs: list[str] = []
        detailed_diff: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        for field in ("environmentId", "policyType", "systemId"):
            old_val = _pv_str(request.old_state.get(field))
            new_val = _pv_str(request.new_inputs.get(field))
            if old_val != new_val:
                diffs.append(field)
                replaces.append(field)
                detailed_diff[field] = PropertyDiff(
                    kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True
                )

        if diffs:
            return DiffResponse(
                changes=True,
                diffs=diffs,
                detailed_diff=detailed_diff,
                replaces=replaces,
            )
        return DiffResponse(changes=False, diffs=[], detailed_diff=None)

    async def create(
        self,
        request: CreateRequest,
        *,
        _sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> CreateResponse:
        """Link the enterprise policy to the environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        env_id = _pv_str(request.properties.get("environmentId"))
        policy_type = _pv_str(request.properties.get("policyType"))
        system_id = _pv_str(request.properties.get("systemId"))

        if not env_id or not policy_type or not system_id:
            raise ValueError("environmentId, policyType, and systemId are all required.")

        max_polls = max(1, int(request.timeout / _POLL_INTERVAL)) if request.timeout else _MAX_POLLS
        await self._perform_link(env_id, policy_type, system_id, _sleep=_sleep, max_polls=max_polls)

        resource_id = f"{env_id}_{policy_type.lower()}"
        return CreateResponse(
            resource_id=resource_id,
            properties={
                "environmentId": PropertyValue(env_id),
                "policyType": PropertyValue(policy_type),
                "systemId": PropertyValue(system_id),
            },
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current link state from the environment's enterprisePolicies map."""
        env_id, policy_type_lower = _parse_resource_id(request.resource_id)
        policy_type = _LOWER_TO_POLICY_TYPE.get(policy_type_lower, "")
        system_id = _pv_str(request.inputs.get("systemId"))

        try:
            env = await retry_with_backoff(
                lambda: self._client.raw.request(
                    "GET",
                    _ENV_READ_PATH.format(env_id=env_id),
                    api_version=_API_VERSION,
                )
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        policy_key = _POLICY_TYPE_TO_KEY.get(policy_type)
        if not policy_key:
            return ReadResponse(resource_id="", properties={}, inputs={})

        try:
            live_system_id: Optional[str] = env["properties"]["enterprisePolicies"][policy_key][
                "systemId"
            ]
        except (KeyError, TypeError):
            live_system_id = None

        if not live_system_id:
            return ReadResponse(resource_id="", properties={}, inputs={})

        if system_id and live_system_id != system_id:
            return ReadResponse(resource_id="", properties={}, inputs={})

        resource_id = f"{env_id}_{policy_type_lower}"
        outputs = {
            "environmentId": PropertyValue(env_id),
            "policyType": PropertyValue(policy_type),
            "systemId": PropertyValue(live_system_id),
        }
        return ReadResponse(
            resource_id=resource_id,
            properties=outputs,
            inputs={
                "environmentId": PropertyValue(env_id),
                "policyType": PropertyValue(policy_type),
                "systemId": PropertyValue(live_system_id),
            },
        )

    async def delete(
        self,
        request: DeleteRequest,
        *,
        _sleep: Optional[Callable[[float], Awaitable[None]]] = None,
    ) -> None:
        """Unlink the enterprise policy from the environment."""
        env_id, policy_type_lower = _parse_resource_id(request.resource_id)
        policy_type = _LOWER_TO_POLICY_TYPE.get(
            policy_type_lower,
            _pv_str(request.properties.get("policyType")) or "",
        )
        system_id = _pv_str(request.properties.get("systemId"))

        if not system_id:
            logger.warning(
                "systemId missing from state for EnterprisePolicyLink %r — skipping unlink.",
                request.resource_id,
            )
            return

        max_polls = max(1, int(request.timeout / _POLL_INTERVAL)) if request.timeout else _MAX_POLLS
        try:
            await self._perform_unlink(env_id, policy_type, system_id, _sleep=_sleep, max_polls=max_polls)
        except HttpError as exc:
            if exc.status_code == 404:
                return  # Already unlinked / environment gone.
            raise

    async def update(self, request: object) -> None:  # type: ignore[override]
        """EnterprisePolicyLink is fully immutable; updates are not supported.

        Diff always marks all fields as UPDATE_REPLACE, so Pulumi should never
        call this method.  It exists as a safeguard to produce a clear error.
        """
        raise NotImplementedError(
            "EnterprisePolicyLink is fully immutable. "
            "Any change to environmentId, policyType, or systemId requires resource replacement."
        )

    # ---- Internal helpers -------------------------------------------------------

    async def _perform_link(
        self,
        env_id: str,
        policy_type: str,
        system_id: str,
        *,
        _sleep: Optional[Callable[[float], Awaitable[None]]] = None,
        max_polls: int = _MAX_POLLS,
    ) -> None:
        """POST link, poll the operation URL, and retry on operation failure.

        Retries up to ``_MAX_LINK_ATTEMPTS`` times.  A 409 Conflict response
        means the policy is already linked and is treated as success.
        """
        sleep = _sleep or asyncio.sleep
        for attempt in range(_MAX_LINK_ATTEMPTS):
            try:
                _, raw_headers = await self._client.raw.request(
                    "POST",
                    _LINK_PATH.format(env_id=env_id, policy_type=policy_type),
                    body={"systemId": system_id},
                    api_version=_API_VERSION,
                    return_headers=True,
                )
            except HttpError as exc:
                if exc.status_code == 409:
                    return  # Already linked — treat as success.
                raise

            operation_url = _extract_operation_url(raw_headers)
            if not operation_url:
                return  # Synchronous success (no async operation URL).

            succeeded = await self._poll_operation(operation_url, sleep=sleep, max_polls=max_polls)
            if succeeded:
                return

            if attempt < _MAX_LINK_ATTEMPTS - 1:
                logger.warning(
                    "Enterprise policy link failed (attempt %d/%d). Retrying in %.0fs.",
                    attempt + 1,
                    _MAX_LINK_ATTEMPTS,
                    _RETRY_DELAY,
                )
                await sleep(_RETRY_DELAY)

        raise RuntimeError(
            f"Failed to link enterprise policy {system_id!r} to environment {env_id!r} "
            f"after {_MAX_LINK_ATTEMPTS} attempts."
        )

    async def _perform_unlink(
        self,
        env_id: str,
        policy_type: str,
        system_id: str,
        *,
        _sleep: Optional[Callable[[float], Awaitable[None]]] = None,
        max_polls: int = _MAX_POLLS,
    ) -> None:
        """POST unlink and poll the operation URL to completion."""
        sleep = _sleep or asyncio.sleep

        _, raw_headers = await self._client.raw.request(
            "POST",
            _UNLINK_PATH.format(env_id=env_id, policy_type=policy_type),
            body={"systemId": system_id},
            api_version=_API_VERSION,
            return_headers=True,
        )

        operation_url = _extract_operation_url(raw_headers)
        if not operation_url:
            return  # Synchronous success.

        succeeded = await self._poll_operation(operation_url, sleep=sleep, max_polls=max_polls)
        if not succeeded:
            raise RuntimeError(
                f"Unlink operation for environment {env_id!r} / policy {policy_type!r} failed."
            )

    async def _poll_operation(
        self,
        operation_url: str,
        *,
        sleep: Callable[[float], Awaitable[None]],
        max_polls: int = _MAX_POLLS,
    ) -> bool:
        """Poll the operation URL until Succeeded or Failed.

        Returns ``True`` when the operation succeeded, ``False`` when it failed.
        Polls every ``_POLL_INTERVAL`` seconds while the operation is still running.
        Raises ``TimeoutError`` after ``max_polls`` attempts with no terminal state.
        """
        for poll_count in range(max_polls):
            result = await retry_with_backoff(
                lambda: self._client.raw.request("GET", operation_url, api_version=None)
            )
            state_id = _extract_state_id(result)
            if state_id and state_id.lower() == "succeeded":
                return True
            if state_id and state_id.lower() == "failed":
                return False
            if poll_count < max_polls - 1:
                await sleep(_POLL_INTERVAL)

        raise TimeoutError(
            f"Operation at {operation_url!r} did not reach a terminal state "
            f"after {max_polls} polls."
        )


def _extract_operation_url(raw_headers: dict[str, Any]) -> Optional[str]:
    """Return the async operation URL from response headers, case-insensitively.

    Checks both ``Location`` and ``Operation-Location`` header names.
    """
    headers_lower = {k.lower(): v for k, v in raw_headers.items()}
    return headers_lower.get("location") or headers_lower.get("operation-location")


def _extract_state_id(result: Any) -> Optional[str]:
    """Extract the operation state ID from a polling response body.

    Handles both Power Platform ``{"State": {"Id": "Succeeded"}}`` and
    ARM-style ``{"status": "Succeeded"}`` response shapes.
    """
    if not isinstance(result, dict):
        return None
    state = result.get("State") or result.get("state")
    if isinstance(state, dict):
        return state.get("Id") or state.get("id")
    return result.get("status") or result.get("Status")


def _parse_resource_id(resource_id: str) -> tuple[str, str]:
    """Split ``'{environmentId}_{policyType_lowercase}'`` into components.

    UUIDs never contain underscores, so the first ``_`` is the delimiter.
    """
    env_id, _, policy_type_lower = resource_id.partition("_")
    return env_id, policy_type_lower
