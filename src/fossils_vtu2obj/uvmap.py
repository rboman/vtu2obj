"""Scalar-to-UV mapping helpers."""

from __future__ import annotations

import math

import vtk

DEFAULT_V_COORD = 0.5


def validate_color_bins(n_colors: int) -> int:
    """Validate the requested number of color bins."""
    if n_colors <= 1:
        raise ValueError("n_colors must be greater than 1.")
    return n_colors


def bin_center(bin_index: int, n_colors: int) -> float:
    """Return the normalized center of a discrete color bin."""
    validate_color_bins(n_colors)
    if not 0 <= bin_index < n_colors:
        raise ValueError("bin_index must lie inside the palette.")
    return (bin_index + 0.5) / n_colors


def resolve_scalar_range(
    scalar_array: vtk.vtkDataArray,
    vmin: float | None = None,
    vmax: float | None = None,
) -> tuple[float, float]:
    """Resolve the scalar range used for UV generation."""
    if scalar_array.GetNumberOfTuples() == 0:
        raise ValueError("Cannot derive a scalar range from an empty array.")

    auto_min, auto_max = scalar_array.GetRange()
    resolved_vmin = auto_min if vmin is None else float(vmin)
    resolved_vmax = auto_max if vmax is None else float(vmax)
    if resolved_vmin > resolved_vmax:
        raise ValueError("vmin must be less than or equal to vmax.")
    return resolved_vmin, resolved_vmax


def normalize_scalar(value: float, vmin: float, vmax: float) -> float:
    """Normalize and clamp a scalar value to the [0, 1] interval."""
    if not math.isfinite(value):
        raise ValueError("Scalar values must be finite.")
    if vmin == vmax:
        return 0.5

    normalized = (value - vmin) / (vmax - vmin)
    if normalized <= 0.0:
        return 0.0
    if normalized >= 1.0:
        return 1.0
    return normalized


def quantize_normalized_value(normalized_value: float, n_colors: int) -> int:
    """Quantize a normalized scalar into a discrete palette bin."""
    validate_color_bins(n_colors)
    if normalized_value <= 0.0:
        return 0
    if normalized_value >= 1.0:
        return n_colors - 1
    return int(normalized_value * n_colors)


def scalar_to_bin_index(value: float, vmin: float, vmax: float, n_colors: int) -> int:
    """Map a scalar value to a discrete palette bin index."""
    normalized = normalize_scalar(value, vmin, vmax)
    return quantize_normalized_value(normalized, n_colors)


def scalar_to_uv(
    value: float,
    vmin: float,
    vmax: float,
    n_colors: int,
    v_coord: float = DEFAULT_V_COORD,
) -> tuple[float, float]:
    """Convert a scalar value into a texture coordinate."""
    if not 0.0 <= v_coord <= 1.0:
        raise ValueError("v_coord must lie inside the [0, 1] interval.")

    bin_index = scalar_to_bin_index(value, vmin, vmax, n_colors)
    return bin_center(bin_index, n_colors), v_coord


def apply_scalar_uv_map(
    polydata: vtk.vtkPolyData,
    field_name: str,
    *,
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
    v_coord: float = DEFAULT_V_COORD,
) -> vtk.vtkPolyData:
    """Attach texture coordinates derived from scalar values."""
    if not isinstance(polydata, vtk.vtkPolyData):
        raise TypeError("apply_scalar_uv_map expects a vtkPolyData input.")

    scalar_array = polydata.GetPointData().GetArray(field_name)
    if scalar_array is None:
        raise ValueError(
            f"Unknown point-data field '{field_name}' on the surface mesh."
        )
    if scalar_array.GetNumberOfComponents() != 1:
        raise ValueError(
            f"Field '{field_name}' must be a scalar point-data array to generate UVs."
        )

    validate_color_bins(n_colors)
    resolved_vmin, resolved_vmax = resolve_scalar_range(
        scalar_array,
        vmin=vmin,
        vmax=vmax,
    )

    mapped_surface = vtk.vtkPolyData()
    mapped_surface.DeepCopy(polydata)
    mapped_array = mapped_surface.GetPointData().GetArray(field_name)

    texture_coordinates = vtk.vtkFloatArray()
    texture_coordinates.SetName("TextureCoordinates")
    texture_coordinates.SetNumberOfComponents(2)
    texture_coordinates.SetNumberOfTuples(mapped_surface.GetNumberOfPoints())

    for point_id in range(mapped_surface.GetNumberOfPoints()):
        scalar_value = float(mapped_array.GetTuple1(point_id))
        u_coord, mapped_v = scalar_to_uv(
            scalar_value,
            resolved_vmin,
            resolved_vmax,
            n_colors,
            v_coord=v_coord,
        )
        texture_coordinates.SetTuple2(point_id, u_coord, mapped_v)

    mapped_surface.GetPointData().SetTCoords(texture_coordinates)
    return mapped_surface
