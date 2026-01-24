"""
Helper functions for data processing.
Adapted from open-mastr.
"""

from .constants import BULK_INCLUDE_TABLES_MAP


def data_to_include_tables(data: list, mapping: str = None) -> list:
    """
    Convert data parameter to list of tables to include.

    Parameters
    ----------
    data : list
        List of data types (e.g., ['wind', 'solar'])
    mapping : str
        Type of mapping to use

    Returns
    -------
    list
        List of table names to include
    """
    if mapping == "write_xml":
        include_tables = []
        for data_type in data:
            if data_type in BULK_INCLUDE_TABLES_MAP:
                include_tables.extend(BULK_INCLUDE_TABLES_MAP[data_type])
            else:
                # If not in map, assume it's already a table name
                include_tables.append(data_type)
        return include_tables

    return data


def transform_data_parameter(data, **kwargs):
    """
    Transform data parameter to standard format.

    Parameters
    ----------
    data : str, list, or None
        Data types to process

    Returns
    -------
    list
        Standardized list of data types
    """
    from .constants import BULK_DATA

    if data is None:
        return BULK_DATA
    elif isinstance(data, str):
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("data must be None, string, or list")
