import pytest
import vtk

from fossils_vtu2obj.surface import extract_surface
from fossils_vtu2obj.uvmap import (
    DEFAULT_V_COORD,
    apply_scalar_uv_map,
    bin_center,
    normalize_scalar,
    quantize_normalized_value,
    resolve_scalar_range,
)


def test_bin_center_returns_middle_of_bin() -> None:
    assert bin_center(0, 4) == 0.125
    assert bin_center(3, 4) == 0.875
    assert DEFAULT_V_COORD == 0.5


def test_bin_center_rejects_invalid_index() -> None:
    with pytest.raises(ValueError):
        bin_center(4, 4)


def test_normalize_scalar_clamps_values() -> None:
    assert normalize_scalar(-1.0, 0.0, 10.0) == 0.0
    assert normalize_scalar(12.0, 0.0, 10.0) == 1.0
    assert normalize_scalar(5.0, 0.0, 10.0) == 0.5


def test_quantize_normalized_value_uses_last_bin_for_one() -> None:
    assert quantize_normalized_value(1.0, 4) == 3


def test_resolve_scalar_range_uses_array_range(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    scalar_array = sample_unstructured_grid.GetPointData().GetArray("stress_von_mises")

    assert resolve_scalar_range(scalar_array) == (1.0, 4.0)


def test_apply_scalar_uv_map_sets_tcoords_on_surface(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    surface = extract_surface(sample_unstructured_grid)
    mapped = apply_scalar_uv_map(
        surface,
        "stress_von_mises",
        n_colors=4,
    )

    tcoords = mapped.GetPointData().GetTCoords()
    assert tcoords is not None
    uv_values = sorted(
        tcoords.GetTuple2(index) for index in range(tcoords.GetNumberOfTuples())
    )

    assert uv_values == [(0.125, 0.5), (0.375, 0.5), (0.625, 0.5), (0.875, 0.5)]
