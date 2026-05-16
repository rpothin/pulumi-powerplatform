"""AdminManagementApplication resource handler.

Registers a service principal as a Power Platform admin management application.
"""

from __future__ import annotations

import re
from typing import Optional

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

_API_VERSION = "2022-03-01-preview"
_ADMIN_APPLICATIONS_PATH = "/providers/Microsoft.BusinessAppPlatform/adminApplications/{app_id}"

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class AdminManagementApplicationResource:
    """Handles CRUD operations for powerplatform:index:AdminManagementApplication."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate that applicationId is present and a valid GUID."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        application_id = _pv_str(inputs.get("applicationId"))
        if not application_id:
            failures.append(
                CheckFailure(
                    property="applicationId",
                    reason="applicationId is required and cannot be empty.",
                )
            )
        elif not _UUID_RE.match(application_id):
            failures.append(
                CheckFailure(
                    property="applicationId",
                    reason=f"applicationId must be a valid UUID/GUID, got: {application_id!r}.",
                )
            )
        else:
            # Normalize to lowercase to prevent spurious diffs from casing differences.
            inputs["applicationId"] = PropertyValue(application_id.lower())

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute diff. applicationId is immutable — any change triggers replacement."""
        old_id = _pv_str(request.old_state.get("applicationId"))
        new_id = _pv_str(request.new_inputs.get("applicationId"))

        if old_id != new_id:
            return DiffResponse(
                changes=True,
                diffs=["applicationId"],
                detailed_diff={
                    "applicationId": PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)
                },
                replaces=["applicationId"],
            )

        return DiffResponse(changes=False, diffs=[], detailed_diff=None)

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Register the service principal as an admin management application."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        application_id = _pv_str(request.properties.get("applicationId"))
        if not application_id:
            raise ValueError("applicationId is required to create an AdminManagementApplication.")

        path = _ADMIN_APPLICATIONS_PATH.format(app_id=application_id)
        response = await retry_with_backoff(
            lambda: self._client.raw.request("POST", path, api_version=_API_VERSION)
        )

        registered_id = (_extract_application_id(response) or application_id).lower()

        return CreateResponse(
            resource_id=registered_id,
            properties={"applicationId": PropertyValue(registered_id)},
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the registration state of the admin management application."""
        application_id = request.resource_id

        try:
            response = await retry_with_backoff(
                lambda: self._client.raw.request(
                    "GET",
                    _ADMIN_APPLICATIONS_PATH.format(app_id=application_id),
                    api_version=_API_VERSION,
                )
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        registered_id = (_extract_application_id(response) or application_id).lower()
        outputs = {"applicationId": PropertyValue(registered_id)}
        return ReadResponse(
            resource_id=registered_id,
            properties=outputs,
            inputs=outputs,
        )

    async def delete(self, request: DeleteRequest) -> None:
        """Unregister the service principal as an admin management application."""
        application_id = request.resource_id

        try:
            await retry_with_backoff(
                lambda: self._client.raw.request(
                    "DELETE",
                    _ADMIN_APPLICATIONS_PATH.format(app_id=application_id),
                    api_version=_API_VERSION,
                )
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return
            raise

    async def update(self, request: object) -> None:  # type: ignore[override]
        """AdminManagementApplication is fully immutable; updates are not supported.

        Diff always marks applicationId as UPDATE_REPLACE, so Pulumi should never
        call this method. It exists as a safeguard to produce a clear error if it
        is ever reached.
        """
        raise NotImplementedError(
            "AdminManagementApplication is fully immutable. "
            "Any change to applicationId requires resource replacement."
        )


def _extract_application_id(response: object) -> Optional[str]:
    """Extract applicationId from a BAP adminApplications API response."""
    if not isinstance(response, dict):
        return None
    for key in ("applicationId", "id", "name"):
        value = response.get(key)
        if isinstance(value, str) and _UUID_RE.match(value):
            return value
    props = response.get("properties")
    if isinstance(props, dict):
        for key in ("applicationId", "id"):
            value = props.get(key)
            if isinstance(value, str) and _UUID_RE.match(value):
                return value
    return None
