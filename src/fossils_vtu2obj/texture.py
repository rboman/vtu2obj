"""Palette texture helpers."""

from __future__ import annotations

from pathlib import Path

import vtk

from .colormaps import require_colormap_name, sample_colormap
from .defaults import DEFAULT_N_COLORS, DEFAULT_TEXTURE_HEIGHT


def validate_texture_shape(
    n_colors: int,
    height: int = DEFAULT_TEXTURE_HEIGHT,
) -> tuple[int, int]:
    """Validate and return texture dimensions for a palette image."""
    if n_colors <= 1:
        raise ValueError("n_colors must be greater than 1.")
    if height <= 0:
        raise ValueError("Texture height must be positive.")
    return n_colors, height


def build_palette_texture(
    colormap: str,
    n_colors: int = DEFAULT_N_COLORS,
    height: int = DEFAULT_TEXTURE_HEIGHT,
) -> vtk.vtkImageData:
    """Build a VTK image containing the discrete palette texture."""
    require_colormap_name(colormap)
    width, texture_height = validate_texture_shape(n_colors, height)
    image = vtk.vtkImageData()
    image.SetDimensions(width, texture_height, 1)
    image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 3)

    scalars = vtk.vtkUnsignedCharArray.SafeDownCast(image.GetPointData().GetScalars())
    if scalars is None:
        raise RuntimeError("Failed to allocate image scalars for the palette texture.")

    palette = sample_colormap(colormap, n_colors=width)
    for row in range(texture_height):
        row_offset = row * width
        for column, (red, green, blue) in enumerate(palette):
            scalars.SetTuple3(row_offset + column, red, green, blue)

    return image


def write_palette_texture(
    image: vtk.vtkImageData,
    output_path: str | Path,
) -> Path:
    """Write a palette texture PNG using VTK."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(image)
    writer.Write()
    if writer.GetErrorCode() != 0 or not path.is_file():
        raise RuntimeError(f"Failed to write palette texture: {path}")

    return path
