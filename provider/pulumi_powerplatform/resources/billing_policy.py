"""Billing Policy resource handler — full CRUD via the Power Platform Management SDK."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from mspp_management.models.billing_instrument_model import BillingInstrumentModel
from mspp_management.models.billing_policy_post_request_model import BillingPolicyPostRequestModel
from mspp_management.models.billing_policy_put_request_model import BillingPolicyPutRequestModel
from mspp_management.models.billing_policy_response_model import BillingPolicyResponseModel
from mspp_management.models.billing_policy_status import BillingPolicyStatus
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
from pulumi_powerplatform.utils import pv_to_comparable as _pv_to_comparable
from pulumi_powerplatform.utils import retry_with_backoff


class BillingPolicyResource:
    """Handles CRUD operations for powerplatform:index:BillingPolicy."""

    def __init__(self, client: PowerPlatformClient) -> None:
        self._client = client

    async def check(self, request: CheckRequest) -> CheckResponse:
        """Validate inputs for a billing policy."""
        failures: list[CheckFailure] = []
        inputs = dict(request.new_inputs)

        name = _pv_str(inputs.get("name"))
        if not name:
            failures.append(CheckFailure(property="name", reason="name is required and cannot be empty."))

        location = _pv_str(inputs.get("location"))
        if not location:
            failures.append(CheckFailure(property="location", reason="location is required and cannot be empty."))

        return CheckResponse(inputs=inputs, failures=failures if failures else None)

    async def diff(self, request: DiffRequest) -> DiffResponse:
        """Compute property-level diff for a billing policy."""
        diffs: list[str] = []
        detailed: dict[str, PropertyDiff] = {}
        replaces: list[str] = []

        old = request.old_state
        new = request.new_inputs

        # location and billingInstrument are immutable — changes require replacement.
        for prop in ("location", "billingInstrument"):
            old_val = old.get(prop)
            new_val = new.get(prop)
            if _pv_to_comparable(old_val) != _pv_to_comparable(new_val):
                diffs.append(prop)
                detailed[prop] = PropertyDiff(kind=PropertyDiffKind.UPDATE_REPLACE, input_diff=True)
                replaces.append(prop)

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
        """Create a new billing policy."""
        if request.preview:
            return CreateResponse(resource_id="preview-id", properties=request.properties)

        props = request.properties

        body = BillingPolicyPostRequestModel()
        body.name = _pv_str(props.get("name"))
        body.location = _pv_str(props.get("location"))
        body.status = _resolve_status(_pv_str(props.get("status")))
        body.billing_instrument = _resolve_billing_instrument(props.get("billingInstrument"))

        result = await retry_with_backoff(lambda: self._client.sdk.licensing.billing_policies.post(body))
        if result is None:
            raise RuntimeError("Failed to create billing policy: API returned no result.")

        policy_id = str(result.id) if result.id else ""
        return CreateResponse(
            resource_id=policy_id,
            properties=_billing_policy_to_outputs(result),
        )

    async def read(self, request: ReadRequest) -> ReadResponse:
        """Read the current state of a billing policy."""
        policy_id = request.resource_id
        result = await retry_with_backoff(
            lambda: self._client.sdk.licensing.billing_policies.by_billing_policy_id(policy_id).get()
        )

        if result is None:
            return ReadResponse(resource_id="", properties={}, inputs={})

        outputs = _billing_policy_to_outputs(result)
        inputs = {
            k: v for k, v in outputs.items() if k in ("name", "location", "status", "billingInstrument")
        }
        return ReadResponse(resource_id=policy_id, properties=outputs, inputs=inputs)

    async def update(self, request: UpdateRequest) -> UpdateResponse:
        """Update an existing billing policy."""
        if request.preview:
            return UpdateResponse(properties=request.news)

        policy_id = request.resource_id
        props = request.news

        body = BillingPolicyPutRequestModel()
        body.name = _pv_str(props.get("name"))
        body.status = _resolve_status(_pv_str(props.get("status")))

        result = await retry_with_backoff(
            lambda: self._client.sdk.licensing.billing_policies.by_billing_policy_id(policy_id).put(body)
        )
        if result is None:
            raise RuntimeError(f"Failed to update billing policy {policy_id}: API returned no result.")

        return UpdateResponse(properties=_billing_policy_to_outputs(result))

    async def delete(self, request: DeleteRequest) -> None:
        """Delete a billing policy."""
        policy_id = request.resource_id
        await retry_with_backoff(
            lambda: self._client.sdk.licensing.billing_policies.by_billing_policy_id(policy_id).delete()
        )


def _resolve_status(status_str: Optional[str]) -> BillingPolicyStatus:
    """Resolve a status string to a BillingPolicyStatus enum value."""
    if status_str and status_str.lower() == "disabled":
        return BillingPolicyStatus.Disabled
    return BillingPolicyStatus.Enabled


def _resolve_billing_instrument(pv: Optional[PropertyValue]) -> Optional[BillingInstrumentModel]:
    """Convert a PropertyValue object to a BillingInstrumentModel."""
    if pv is None or pv.value is None:
        return None

    obj: dict[str, PropertyValue] = pv.value
    instrument = BillingInstrumentModel()
    instrument.id = _pv_str(obj.get("id"))

    resource_group = _pv_str(obj.get("resourceGroup"))
    if resource_group:
        instrument.resource_group = resource_group

    subscription_id = _pv_str(obj.get("subscriptionId"))
    if subscription_id:
        instrument.subscription_id = UUID(subscription_id)

    return instrument


def _billing_policy_to_outputs(policy: BillingPolicyResponseModel) -> dict[str, PropertyValue]:
    """Convert a BillingPolicyResponseModel SDK model to a Pulumi property map."""
    outputs: dict[str, PropertyValue] = {}

    if policy.name is not None:
        outputs["name"] = PropertyValue(policy.name)
    if policy.location is not None:
        outputs["location"] = PropertyValue(policy.location)
    if policy.status is not None:
        status_val = policy.status.value if hasattr(policy.status, "value") else str(policy.status)
        outputs["status"] = PropertyValue(status_val)
    if policy.billing_instrument is not None:
        bi = policy.billing_instrument
        bi_map: dict[str, PropertyValue] = {}
        if bi.id is not None:
            bi_map["id"] = PropertyValue(bi.id)
        if bi.resource_group is not None:
            bi_map["resourceGroup"] = PropertyValue(bi.resource_group)
        if bi.subscription_id is not None:
            bi_map["subscriptionId"] = PropertyValue(str(bi.subscription_id))
        outputs["billingInstrument"] = PropertyValue(bi_map)
    if policy.created_on is not None:
        outputs["createdOn"] = PropertyValue(policy.created_on.isoformat())
    if policy.last_modified_on is not None:
        outputs["lastModifiedOn"] = PropertyValue(policy.last_modified_on.isoformat())

    return outputs
