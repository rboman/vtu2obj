"""Surface extraction helpers."""

from __future__ import annotations

import vtk

from .defaults import DEFAULT_NORMALS_FEATURE_ANGLE, DEFAULT_NORMALS_SPLITTING


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


def generate_surface_normals(
    polydata: vtk.vtkPolyData,
    *,
    splitting: bool = DEFAULT_NORMALS_SPLITTING,
    feature_angle: float = DEFAULT_NORMALS_FEATURE_ANGLE,
) -> vtk.vtkPolyData:
    """Generate point normals on a surface mesh."""
    if not isinstance(polydata, vtk.vtkPolyData):
        raise TypeError("generate_surface_normals expects a vtkPolyData input.")

    normals_filter = vtk.vtkPolyDataNormals()
    normals_filter.SetInputData(polydata)
    normals_filter.ComputePointNormalsOn()
    normals_filter.ComputeCellNormalsOff()
    normals_filter.SetFeatureAngle(feature_angle)
    if splitting:
        normals_filter.SplittingOn()
    else:
        normals_filter.SplittingOff()
    normals_filter.ConsistencyOn()
    normals_filter.AutoOrientNormalsOn()
    normals_filter.NonManifoldTraversalOff()
    normals_filter.Update()

    surface_with_normals = vtk.vtkPolyData()
    surface_with_normals.ShallowCopy(normals_filter.GetOutput())
    return surface_with_normals
