"""EnvironmentApplicationAdmin resource handler.

Adds a service principal as System Administrator in a Dataverse environment by
creating a ``systemuser`` record.  Uses two API surfaces:

- BAP admin API for the initial ``addAppUser`` registration.
- Dataverse Web API (OData) for read and delete operations.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Optional
from urllib.parse import urlparse

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
from rpothin_powerplatform.raw_api import RawApiClient
from rpothin_powerplatform.utils import HttpError, resolve_dataverse_url
from rpothin_powerplatform.utils import pv_str as _pv_str

logger = logging.getLogger(__name__)

_BAP_ADD_APP_USER_VERSION = "2020-10-01"
_ADD_APP_USER_PATH = (
    "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/{env_id}/addAppUser"
)

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class EnvironmentApplicationAdminResource:
    """Handles CRUD for powerplatform:index:EnvironmentApplicationAdmin."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs and that the target environment has a Dataverse instance."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        env_id = _pv_str(inputs.get("environmentId"))
        app_id = _pv_str(inputs.get("applicationId"))

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
            env_id = env_id.lower()

        if not app_id:
            failures.append(
                CheckFailure(
                    property="applicationId",
                    reason="applicationId is required and cannot be empty.",
                )
            )
        elif not _UUID_RE.match(app_id):
            failures.append(
                CheckFailure(
                    property="applicationId",
                    reason=f"applicationId must be a valid UUID/GUID, got: {app_id!r}.",
                )
            )
        else:
            inputs["applicationId"] = PropertyValue(app_id.lower())

        # When format checks pass and the client is available, verify the environment
        # has a Dataverse instance.  Skip silently on transient errors (e.g. network
        # unavailable during preview) — create() will surface any problem.
        if not failures and self._client is not None:
            try:
                instance_url = await resolve_dataverse_url(self._client.raw, env_id)  # type: ignore[arg-type]
                if not instance_url:
                    failures.append(
                        CheckFailure(
                            property="environmentId",
                            reason="The specified environment does not have a Dataverse instance.",
                        )
                    )
            except Exception:
                logger.debug(
                    "Skipping Dataverse validation during check (transient error).",
                    exc_info=True,
                )

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Both environmentId and applicationId are immutable — changes trigger replacement."""
        old_env_id = _pv_str(request.old_state.get("environmentId"))
        new_env_id = _pv_str(request.new_inputs.get("environmentId"))
        old_app_id = _pv_str(request.old_state.get("applicationId"))
        new_app_id = _pv_str(request.new_inputs.get("applicationId"))

        diffs: list[str] = []
        detailed_diff: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        if old_env_id != new_env_id:
            diffs.append("environmentId")
            replaces.append("environmentId")
            detailed_diff["environmentId"] = PropertyDiff(
                kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True
            )

        if old_app_id != new_app_id:
            diffs.append("applicationId")
            replaces.append("applicationId")
            detailed_diff["applicationId"] = PropertyDiff(
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

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Register the service principal as a System Administrator in the environment."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        env_id = _pv_str(request.properties.get("environmentId"))
        app_id = _pv_str(request.properties.get("applicationId"))

        if not env_id or not app_id:
            raise ValueError("environmentId and applicationId are required.")

        # Register via BAP admin API.
        path = _ADD_APP_USER_PATH.format(env_id=env_id)
        await self._client.raw.request(
            "POST",
            path,
            body={"servicePrincipalAppId": app_id},
            api_version=_BAP_ADD_APP_USER_VERSION,
        )

        # Resolve Dataverse URL and retrieve the created systemuser record.
        instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        if not instance_url:
            raise RuntimeError(
                f"Environment {env_id!r} does not have a Dataverse instance. "
                "EnvironmentApplicationAdmin requires a Dataverse-enabled environment."
            )

        dv_client = self._make_dataverse_client(instance_url)
        system_user_id = await self._fetch_system_user_id(dv_client, app_id)
        if not system_user_id:
            raise RuntimeError(
                f"Application user for {app_id!r} was not found in Dataverse after "
                "registration. The addAppUser call succeeded but the systemuser record "
                "is not yet visible — retry the operation or check the environment."
            )

        resource_id = f"{env_id}/{app_id}"
        return CreateResponse(
            resource_id=resource_id,
            properties={
                "environmentId": PropertyValue(env_id),
                "applicationId": PropertyValue(app_id),
                "systemUserId": PropertyValue(system_user_id),
            },
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the application admin registration from Dataverse."""
        env_id, app_id = _parse_resource_id(request.resource_id)

        try:
            instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return ReadResponse(resource_id="", properties={}, inputs={})
            raise

        if not instance_url:
            return ReadResponse(resource_id="", properties={}, inputs={})

        dv_client = self._make_dataverse_client(instance_url)
        system_user_id = await self._fetch_system_user_id(dv_client, app_id, max_attempts=1)
        if not system_user_id:
            return ReadResponse(resource_id="", properties={}, inputs={})

        resource_id = f"{env_id}/{app_id}"
        outputs = {
            "environmentId": PropertyValue(env_id),
            "applicationId": PropertyValue(app_id),
            "systemUserId": PropertyValue(system_user_id),
        }
        return ReadResponse(
            resource_id=resource_id,
            properties=outputs,
            inputs={
                "environmentId": PropertyValue(env_id),
                "applicationId": PropertyValue(app_id),
            },
        )

    async def delete(self, request: DeleteRequest) -> None:
        """Deactivate and remove the application admin from the Dataverse environment."""
        env_id, app_id = _parse_resource_id(request.resource_id)
        system_user_id = _pv_str(request.properties.get("systemUserId"))

        try:
            instance_url = await resolve_dataverse_url(self._client.raw, env_id)
        except HttpError as exc:
            if exc.status_code == 404:
                return  # Environment gone — nothing to delete.
            raise

        if not instance_url:
            return  # No Dataverse instance — nothing to delete.

        dv_client = self._make_dataverse_client(instance_url)

        # Resolve systemUserId from Dataverse if missing from state.
        if not system_user_id:
            system_user_id = await self._fetch_system_user_id(dv_client, app_id, max_attempts=1)

        if not system_user_id:
            return  # User already gone.

        # Deactivate the user before deletion (required by Dataverse for app users).
        try:
            await dv_client.request(
                "PATCH",
                f"/api/data/v9.2/systemusers({system_user_id})",
                body={"isdisabled": True},
                api_version=None,
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return  # Already deleted.
            raise

        # Remove the system user record.
        try:
            await dv_client.request(
                "DELETE",
                f"/api/data/v9.2/systemusers({system_user_id})",
                api_version=None,
            )
        except HttpError as exc:
            if exc.status_code == 404:
                return  # Already deleted.
            raise

    async def update(self, request: object) -> None:  # type: ignore[override]
        """EnvironmentApplicationAdmin is fully immutable; updates are not supported.

        Diff always marks both fields as UPDATE_REPLACE, so Pulumi should never
        call this method.  It exists as a safeguard to produce a clear error.
        """
        raise NotImplementedError(
            "EnvironmentApplicationAdmin is fully immutable. "
            "Any change to environmentId or applicationId requires resource replacement."
        )

    def _make_dataverse_client(self, instance_url: str) -> RawApiClient:
        """Create a RawApiClient scoped to the given Dataverse instance URL."""
        parsed = urlparse(instance_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return RawApiClient(
            token_provider=self._client.credential,
            base_url=base,
            scope=f"{base}/.default",
        )

    async def _fetch_system_user_id(
        self,
        dv_client: RawApiClient,
        app_id: str,
        *,
        max_attempts: int = 5,
    ) -> Optional[str]:
        """Query Dataverse for the systemuser record GUID of the given application.

        Retries up to ``max_attempts`` times with a 2-second delay between
        attempts to handle propagation lag after ``addAppUser``.
        """
        path = (
            f"/api/data/v9.2/systemusers"
            f"?$select=systemuserid&$filter=applicationid eq {app_id}"
        )
        for attempt in range(max_attempts):
            response = await dv_client.request("GET", path, api_version=None)
            users = (response or {}).get("value", [])
            if users:
                return str(users[0]["systemuserid"])
            if attempt < max_attempts - 1:
                await asyncio.sleep(2.0)
        return None


def _parse_resource_id(resource_id: str) -> tuple[str, str]:
    """Split a resource ID of the form ``'{environmentId}/{applicationId}'``."""
    env_id, _, app_id = resource_id.partition("/")
    return env_id, app_id
