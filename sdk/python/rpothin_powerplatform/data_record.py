"""Power Platform DataRecord resource and getDataRecords function."""

import re
from typing import Any, Optional

import pulumi

from .get_data_records import get_data_records  # noqa: F401 — re-exported for backwards compat


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
