"""ISV Contract resource handler — full CRUD via the Power Platform Management SDK."""

from __future__ import annotations

from typing import Optional

from mspp_management.models.billing_policy_status import BillingPolicyStatus
from mspp_management.models.isv_contract_post_request_model import IsvContractPostRequestModel
from mspp_management.models.isv_contract_response_model import IsvContractResponseModel
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
    UpdateRequest,
    UpdateResponse,
)

from pulumi_powerplatform.client import PowerPlatformClient
from pulumi_powerplatform.utils import pv_str as _pv_str


class IsvContractResource:
    """Handles CRUD operations for powerplatform:index:IsvContract."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for an ISV contract."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        name = _pv_str(inputs.get("name"))
        if not name:
            failures.append(CheckFailure(property="name", reason="name is required and cannot be empty."))

        geo = _pv_str(inputs.get("geo"))
        if not geo:
            failures.append(CheckFailure(property="geo", reason="geo is required and cannot be empty."))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for an ISV contract."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        old = request.old_state
        new = request.new_inputs

        # geo is immutable — changes require replacement.
        old_geo = _pv_str(old.get("geo"))
        new_geo = _pv_str(new.get("geo"))
        if old_geo != new_geo:
            diffs.append("geo")
            detailed["geo"] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)
            replaces.append("geo")

        # name and status can be updated in-place.
        for prop in ("name", "status"):
            old_val = _pv_str(old.get(prop))
            new_val = _pv_str(new.get(prop))
            if old_val != new_val:
                diffs.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE, input_diff=True)

        return DiffResponse(
            changes=bool(diffs),
            diffs=diffs,
            detailed_diff=detailed,
            replaces=replaces if replaces else None,
        )

    async def create(self, request: CreateRequest) -> CreateResponse:
        """Create a new ISV contract."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties

        body = IsvContractPostRequestModel()
        body.name = _pv_str(props.get("name"))
        body.geo = _pv_str(props.get("geo"))
        body.status = _resolve_status(_pv_str(props.get("status")))

        result = await self._client.sdk.licensing.isv_contracts.post(body)
        if result is None:
            raise RuntimeError("Failed to create ISV contract: API returned no result.")

        contract_id = str(result.id) if result.id else ""
        return CreateResponse(
            resource_id=contract_id,
            properties=_isv_contract_to_outputs(result),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of an ISV contract."""
        contract_id = request.resource_id
        result = await self._client.sdk.licensing.isv_contracts.by_isv_contract_id(contract_id).get()

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _isv_contract_to_outputs(result)
        inputs = {k: v for k, v in outputs.items() if k in ("name", "geo", "status")}
        return ReadResponse(resource_id=contract_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update an existing ISV contract."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        contract_id = request.resource_id
        props = request.news

        body = IsvContractPostRequestModel()
        body.name = _pv_str(props.get("name"))
        body.geo = _pv_str(props.get("geo"))
        body.status = _resolve_status(_pv_str(props.get("status")))

        result = await self._client.sdk.licensing.isv_contracts.by_isv_contract_id(contract_id).put(body)
        if result is None:
            raise RuntimeError(f"Failed to update ISV contract {contract_id}: API returned no result.")

        return UpdateResponse(properties=_isv_contract_to_outputs(result))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete an ISV contract."""
        contract_id = request.resource_id
        await self._client.sdk.licensing.isv_contracts.by_isv_contract_id(contract_id).delete()


def _resolve_status(status_str: Optional[str]) -> BillingPolicyStatus:
    """Resolve a status string to a BillingPolicyStatus enum value."""
    if status_str and status_str.lower() == "disabled":
        return BillingPolicyStatus.Disabled
    return BillingPolicyStatus.Enabled


def _isv_contract_to_outputs(contract: IsvContractResponseModel) -> dict[str, PropertyValue]:
    """Convert an IsvContractResponseModel SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}

    if contract.name is not None:
        outputs["name"] = PropertyValue(contract.name)
    if contract.geo is not None:
        outputs["geo"] = PropertyValue(contract.geo)
    if contract.status is not None:
        status_val = contract.status.value if hasattr(contract.status, "value") else str(contract.status)
        outputs["status"] = PropertyValue(status_val)
    if contract.created_on is not None:
        outputs["createdOn"] = PropertyValue(contract.created_on.isoformat())
    if contract.last_modified_on is not None:
        outputs["lastModifiedOn"] = PropertyValue(contract.last_modified_on.isoformat())

    return outputs
