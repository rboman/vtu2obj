import pytest
import vtk

from fossils_vtu2obj.surface import extract_surface


def test_extract_surface_rejects_invalid_input() -> None:
    with pytest.raises(TypeError):
        extract_surface(object())


def test_extract_surface_returns_triangles_and_preserves_point_arrays(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    surface = extract_surface(sample_unstructured_grid)

    assert surface.GetNumberOfPoints() == 4
    assert surface.GetNumberOfCells() == 4
    assert surface.GetPointData().HasArray("stress_von_mises") == 1
    assert surface.GetCell(0).GetCellType() == vtk.VTK_TRIANGLE
