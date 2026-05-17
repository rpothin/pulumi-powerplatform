"""Power Platform getDataRecords function."""

from typing import Any, Optional

import pulumi


def get_data_records(
    environment_id: str,
    entity_collection: str,
    apply: Optional[str] = None,
    filter: Optional[str] = None,
    select: Optional[list[str]] = None,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    expand: Optional[list[Any]] = None,
    opts: Optional[pulumi.InvokeOptions] = None,
) -> pulumi.Output[Any]:
    """Queries Dataverse records from *entity_collection* using OData parameters.

    Returns the first page of matching records.  Use *top* to limit large
    result sets.

    :param environment_id: GUID of the Power Platform environment.
    :param entity_collection: Plural OData collection name (e.g. ``"accounts"``).
    :param apply: OData ``$apply`` aggregation expression.  When set,
        ``totalRowsCount`` will be ``0`` and ``$count`` is not sent to
        Dataverse (the two are semantically incompatible).
    :param filter: OData ``$filter`` expression.
    :param select: Column logical names to include in the response.
    :param orderby: OData ``$orderby`` expression.
    :param top: Maximum number of records to return.
    :param expand: Navigation properties to expand (list of dicts with
        ``navigationProperty``, optional ``select`` and ``filter``).

    The result dict contains:

    * ``records`` — list of matching records.
    * ``totalRowsCount`` — total matching records (from ``@odata.count``).
      Returns ``0`` when ``apply`` is used.
    * ``totalRowsCountLimitExceeded`` — True when the CRM count limit was hit.
    """
    args: dict[str, Any] = {
        "environmentId": environment_id,
        "entityCollection": entity_collection,
    }
    if apply is not None:
        args["apply"] = apply
    if filter is not None:
        args["filter"] = filter
    if select is not None:
        args["select"] = select
    if orderby is not None:
        args["orderby"] = orderby
    if top is not None:
        args["top"] = top
    if expand is not None:
        args["expand"] = expand

    return pulumi.runtime.invoke("powerplatform:index:getDataRecords", args, opts)
