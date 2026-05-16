"""Power Platform DataRecord resource and getDataRecords function."""

import re
from typing import Any, Optional

import pulumi


class DataRecord(pulumi.CustomResource):
    """Creates, updates, and deletes a single Dataverse record in any table.

    Columns are expressed as a plain Python dict whose values may be:

    * ``None`` — clear the column (sent as JSON null)
    * scalar (``str``, ``int``, ``float``, ``bool``) — stored directly
    * ``dict`` with ``tableLogicalName`` + ``dataRecordId`` keys — single-valued
      lookup, encoded as ``@odata.bind``
    * ``list`` of such dicts — many-to-many relationship, managed via ``$ref``
      operations

    When *disable_on_destroy* is ``True`` the record is first deactivated
    (``statecode=1``) before being deleted.  This is required for Dataverse
    tables whose rows cannot be deleted while active (e.g. workflow
    definitions).
    """

    environment_id: pulumi.Output[str]
    table_logical_name: pulumi.Output[str]
    columns: pulumi.Output[Any]
    disable_on_destroy: pulumi.Output[bool]
    data_record_id: pulumi.Output[str]

    def __init__(
        self,
        resource_name: str,
        environment_id: Optional[str] = None,
        table_logical_name: Optional[str] = None,
        columns: Optional[Any] = None,
        disable_on_destroy: Optional[bool] = None,
        opts: Optional[pulumi.ResourceOptions] = None,
    ):
        props = {
            "environment_id": environment_id,
            "table_logical_name": table_logical_name,
            "columns": columns,
            "disable_on_destroy": disable_on_destroy,
            "data_record_id": None,
        }
        super().__init__("powerplatform:index:DataRecord", resource_name, props, opts)

    def translate_input_property(self, prop: str) -> str:
        return re.sub(r'_([a-z])', lambda m: m.group(1).upper(), prop)

    def translate_output_property(self, prop: str) -> str:
        return re.sub(r'([A-Z])', lambda m: '_' + m.group(1).lower(), prop)


def get_data_records(
    environment_id: str,
    table_logical_name: str,
    filter: Optional[str] = None,
    select: Optional[list[str]] = None,
    orderby: Optional[str] = None,
    top: Optional[int] = None,
    expand: Optional[list[Any]] = None,
    opts: Optional[pulumi.InvokeOptions] = None,
) -> pulumi.Output[Any]:
    """Queries Dataverse records from *table_logical_name* using OData
    parameters.

    Returns the first page of matching records.  Use *top* to limit large
    result sets.

    :param environment_id: GUID of the Power Platform environment.
    :param table_logical_name: Logical name of the Dataverse table to query.
    :param filter: OData ``$filter`` expression.
    :param select: Column logical names to include in the response.
    :param orderby: OData ``$orderby`` expression.
    :param top: Maximum number of records to return.
    :param expand: Navigation properties to expand (list of dicts with
        ``navigationProperty``, optional ``select`` and ``filter``).
    """
    args: dict[str, Any] = {
        "environmentId": environment_id,
        "tableLogicalName": table_logical_name,
    }
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
