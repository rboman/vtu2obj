"""Shared test helpers."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import vtk

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture()
def sample_unstructured_grid() -> vtk.vtkUnstructuredGrid:
    """Return a tiny tetrahedral grid for future deterministic tests."""
    points = vtk.vtkPoints()
    points.InsertNextPoint(0.0, 0.0, 0.0)
    points.InsertNextPoint(1.0, 0.0, 0.0)
    points.InsertNextPoint(0.0, 1.0, 0.0)
    points.InsertNextPoint(0.0, 0.0, 1.0)

    tetra = vtk.vtkTetra()
    tetra.GetPointIds().SetId(0, 0)
    tetra.GetPointIds().SetId(1, 1)
    tetra.GetPointIds().SetId(2, 2)
    tetra.GetPointIds().SetId(3, 3)

    cells = vtk.vtkCellArray()
    cells.InsertNextCell(tetra)

    grid = vtk.vtkUnstructuredGrid()
    grid.SetPoints(points)
    grid.SetCells(vtk.VTK_TETRA, cells)

    point_scalar = vtk.vtkDoubleArray()
    point_scalar.SetName("stress_von_mises")
    for value in (1.0, 2.0, 3.0, 4.0):
        point_scalar.InsertNextValue(value)
    grid.GetPointData().AddArray(point_scalar)
    grid.GetPointData().SetScalars(point_scalar)

    point_vector = vtk.vtkDoubleArray()
    point_vector.SetName("displacement")
    point_vector.SetNumberOfComponents(3)
    for vector in (
        (0.0, 0.0, 0.0),
        (0.1, 0.0, 0.0),
        (0.0, 0.1, 0.0),
        (0.0, 0.0, 0.1),
    ):
        point_vector.InsertNextTuple3(*vector)
    grid.GetPointData().AddArray(point_vector)

    cell_scalar = vtk.vtkDoubleArray()
    cell_scalar.SetName("cell_stress_von_mises")
    cell_scalar.InsertNextValue(2.5)
    grid.GetCellData().AddArray(cell_scalar)

    return grid


@pytest.fixture()
def sample_vtu_path(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
    tmp_path: Path,
) -> Path:
    """Write the synthetic grid to a temporary VTU file."""
    path = tmp_path / "sample.vtu"
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(str(path))
    writer.SetInputData(sample_unstructured_grid)
    assert writer.Write() == 1
    return path
