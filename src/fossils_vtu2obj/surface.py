"""Surface extraction helpers."""

from __future__ import annotations

import vtk


def extract_surface(
    dataset: vtk.vtkDataSet,
    triangulate: bool = True,
) -> vtk.vtkPolyData:
    """Extract a surface mesh from a VTK dataset."""
    if not isinstance(dataset, vtk.vtkDataSet):
        raise TypeError("extract_surface expects a VTK dataset input.")

    surface_filter = vtk.vtkDataSetSurfaceFilter()
    surface_filter.SetInputData(dataset)

    if triangulate:
        triangle_filter = vtk.vtkTriangleFilter()
        triangle_filter.SetInputConnection(surface_filter.GetOutputPort())
        triangle_filter.Update()

        surface = vtk.vtkPolyData()
        surface.ShallowCopy(triangle_filter.GetOutput())
        return surface

    surface_filter.Update()
    surface = vtk.vtkPolyData()
    surface.ShallowCopy(surface_filter.GetOutput())
    return surface
