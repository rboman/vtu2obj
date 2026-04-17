from pathlib import Path

import pytest
import vtk

from fossils_vtu2obj.texture import (
    build_palette_texture,
    validate_texture_shape,
    write_palette_texture,
)


def test_validate_texture_shape_returns_dimensions() -> None:
    assert validate_texture_shape(256, 16) == (256, 16)


def test_validate_texture_shape_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        validate_texture_shape(1, 16)


def test_build_palette_texture_repeats_palette_on_each_row() -> None:
    image = build_palette_texture("grayscale", n_colors=4, height=3)
    scalars = vtk.vtkUnsignedCharArray.SafeDownCast(image.GetPointData().GetScalars())

    assert image.GetDimensions() == (4, 3, 1)
    assert scalars.GetTuple3(0) == (0.0, 0.0, 0.0)
    assert scalars.GetTuple3(3) == (255.0, 255.0, 255.0)
    assert scalars.GetTuple3(0) == scalars.GetTuple3(4)


def test_write_palette_texture_writes_png_file(tmp_path: Path) -> None:
    image = build_palette_texture("rainbow", n_colors=8, height=2)
    output_path = write_palette_texture(image, tmp_path / "palette.png")

    assert output_path.is_file()
