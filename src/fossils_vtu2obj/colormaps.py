"""Colormap declarations and validation helpers."""

from __future__ import annotations

import vtk

from .defaults import DEFAULT_N_COLORS

BUILTIN_COLORMAPS = (
    "rainbow",
    "cool_to_warm",
    "grayscale",
    "viridis_like",
    "plasma_like",
    "magma_like",
    "inferno_like",
    "turbo_like",
    "blue_to_red",
    "black_body",
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
    "plasma_like": (
        (0.00, 0.050, 0.030, 0.528),
        (0.25, 0.494, 0.012, 0.658),
        (0.50, 0.798, 0.280, 0.469),
        (0.75, 0.973, 0.586, 0.252),
        (1.00, 0.940, 0.975, 0.131),
    ),
    "magma_like": (
        (0.00, 0.001, 0.000, 0.014),
        (0.25, 0.251, 0.038, 0.403),
        (0.50, 0.550, 0.161, 0.506),
        (0.75, 0.869, 0.288, 0.408),
        (1.00, 0.987, 0.991, 0.749),
    ),
    "inferno_like": (
        (0.00, 0.002, 0.001, 0.015),
        (0.25, 0.258, 0.039, 0.406),
        (0.50, 0.578, 0.148, 0.404),
        (0.75, 0.867, 0.320, 0.110),
        (1.00, 0.988, 0.998, 0.645),
    ),
    "turbo_like": (
        (0.00, 0.190, 0.072, 0.232),
        (0.20, 0.160, 0.480, 0.906),
        (0.40, 0.040, 0.761, 0.647),
        (0.60, 0.638, 0.991, 0.237),
        (0.80, 0.985, 0.592, 0.112),
        (1.00, 0.480, 0.016, 0.010),
    ),
    "blue_to_red": (
        (0.00, 0.082, 0.396, 0.753),
        (0.50, 0.950, 0.950, 0.950),
        (1.00, 0.706, 0.016, 0.149),
    ),
    "black_body": (
        (0.00, 0.000, 0.000, 0.000),
        (0.30, 0.650, 0.000, 0.000),
        (0.60, 0.950, 0.450, 0.000),
        (0.85, 1.000, 0.900, 0.400),
        (1.00, 1.000, 1.000, 1.000),
    ),
}

_DIVERGING_COLORMAPS = {
    "cool_to_warm",
    "blue_to_red",
}


def list_colormap_names() -> tuple[str, ...]:
    """Return the supported built-in colormap names."""
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
    if colormap_name in _DIVERGING_COLORMAPS:
        transfer_function.SetColorSpaceToDiverging()

    for x_value, red, green, blue in _COLORMAP_CONTROL_POINTS[colormap_name]:
        transfer_function.AddRGBPoint(x_value, red, green, blue)

    return transfer_function


def build_lookup_table(
    name: str,
    n_colors: int = DEFAULT_N_COLORS,
) -> vtk.vtkLookupTable:
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


def sample_colormap(
    name: str,
    n_colors: int = DEFAULT_N_COLORS,
) -> tuple[tuple[int, int, int], ...]:
    """Return a discrete RGB palette sampled from a named colormap."""
    lookup_table = build_lookup_table(name, n_colors=n_colors)
    return tuple(table_value_to_uint8(lookup_table, index) for index in range(n_colors))
