"""Colormap declarations and validation helpers."""

from __future__ import annotations

import vtk

BUILTIN_COLORMAPS = (
    "rainbow",
    "cool_to_warm",
    "grayscale",
    "viridis_like",
)

_COLORMAP_CONTROL_POINTS = {
    "rainbow": (
        (0.00, 0.0, 0.0, 1.0),
        (0.25, 0.0, 1.0, 1.0),
        (0.50, 0.0, 1.0, 0.0),
        (0.75, 1.0, 1.0, 0.0),
        (1.00, 1.0, 0.0, 0.0),
    ),
    "cool_to_warm": (
        (0.00, 0.231, 0.298, 0.753),
        (0.50, 0.865, 0.865, 0.865),
        (1.00, 0.706, 0.016, 0.149),
    ),
    "grayscale": (
        (0.00, 0.0, 0.0, 0.0),
        (1.00, 1.0, 1.0, 1.0),
    ),
    "viridis_like": (
        (0.00, 0.267, 0.005, 0.329),
        (0.25, 0.230, 0.322, 0.546),
        (0.50, 0.129, 0.567, 0.551),
        (0.75, 0.369, 0.789, 0.383),
        (1.00, 0.993, 0.906, 0.144),
    ),
}


def list_colormap_names() -> tuple[str, ...]:
    """Return the supported bootstrap colormap names."""
    return BUILTIN_COLORMAPS


def require_colormap_name(name: str) -> str:
    """Validate a colormap name and return it unchanged."""
    if name not in BUILTIN_COLORMAPS:
        raise ValueError(
            f"Unknown colormap '{name}'. Available colormaps: {BUILTIN_COLORMAPS}"
        )
    return name


def build_color_transfer_function(name: str) -> vtk.vtkColorTransferFunction:
    """Build a VTK color transfer function for a named preset."""
    colormap_name = require_colormap_name(name)
    transfer_function = vtk.vtkColorTransferFunction()
    if colormap_name == "cool_to_warm":
        transfer_function.SetColorSpaceToDiverging()

    for x_value, red, green, blue in _COLORMAP_CONTROL_POINTS[colormap_name]:
        transfer_function.AddRGBPoint(x_value, red, green, blue)

    return transfer_function


def build_lookup_table(name: str, n_colors: int = 256) -> vtk.vtkLookupTable:
    """Build a discrete lookup table sampled from a named colormap."""
    if n_colors <= 1:
        raise ValueError("n_colors must be greater than 1.")

    transfer_function = build_color_transfer_function(name)
    lookup_table = vtk.vtkLookupTable()
    lookup_table.SetNumberOfTableValues(n_colors)
    lookup_table.SetRange(0.0, 1.0)
    lookup_table.Build()

    for index in range(n_colors):
        x_value = index / (n_colors - 1)
        red, green, blue = transfer_function.GetColor(x_value)
        lookup_table.SetTableValue(index, red, green, blue, 1.0)

    return lookup_table


def table_value_to_uint8(
    lookup_table: vtk.vtkLookupTable,
    index: int,
) -> tuple[int, int, int]:
    """Return one lookup-table color as 8-bit RGB values."""
    red, green, blue, _ = lookup_table.GetTableValue(index)
    return (
        int(round(red * 255)),
        int(round(green * 255)),
        int(round(blue * 255)),
    )


def sample_colormap(name: str, n_colors: int = 256) -> tuple[tuple[int, int, int], ...]:
    """Return a discrete RGB palette sampled from a named colormap."""
    lookup_table = build_lookup_table(name, n_colors=n_colors)
    return tuple(table_value_to_uint8(lookup_table, index) for index in range(n_colors))
