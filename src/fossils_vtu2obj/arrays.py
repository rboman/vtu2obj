"""Array inspection helpers."""

from __future__ import annotations

from .defaults import DEFAULT_PREFERRED_SCALAR_FIELD_NAME
from .model import ArrayAssociation, ArrayInfo, DatasetSummary


def list_point_arrays(summary: DatasetSummary) -> tuple[ArrayInfo, ...]:
    """Return point-data arrays discovered on a dataset."""
    return summary.point_arrays


def list_cell_arrays(summary: DatasetSummary) -> tuple[ArrayInfo, ...]:
    """Return cell-data arrays discovered on a dataset."""
    return summary.cell_arrays


def array_names(arrays: tuple[ArrayInfo, ...]) -> tuple[str, ...]:
    """Return the array names in their current order."""
    return tuple(array.name for array in arrays)


def scalar_field_names(summary: DatasetSummary) -> tuple[str, ...]:
    """Return scalar field names, ordered as point scalars then cell scalars."""
    names = [
        array.name for array in summary.point_arrays if array.is_scalar
    ] + [
        array.name for array in summary.cell_arrays if array.is_scalar
    ]
    return tuple(names)


def preferred_scalar_field_name(
    summary: DatasetSummary,
    preferred_name: str = DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
) -> str | None:
    """Return the preferred scalar field when available, else the first scalar."""
    scalar_names = scalar_field_names(summary)
    if not scalar_names:
        return None
    if preferred_name in scalar_names:
        return preferred_name
    return scalar_names[0]


def find_array(
    summary: DatasetSummary,
    field_name: str,
    association: ArrayAssociation = "point",
) -> ArrayInfo | None:
    """Return an array descriptor when it exists."""
    haystack = summary.point_arrays if association == "point" else summary.cell_arrays
    for array in haystack:
        if array.name == field_name:
            return array
    return None


def require_array(
    summary: DatasetSummary,
    field_name: str,
    association: ArrayAssociation = "point",
) -> ArrayInfo:
    """Return an array descriptor or raise a clear validation error."""
    available_arrays = (
        summary.point_arrays if association == "point" else summary.cell_arrays
    )
    match = find_array(summary=summary, field_name=field_name, association=association)
    if match is None:
        raise ValueError(
            f"Unknown {association}-data field '{field_name}'. "
            f"Available fields: {array_names(available_arrays)}"
        )
    return match
