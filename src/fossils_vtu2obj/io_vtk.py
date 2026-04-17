"""VTK I/O entry points."""

from __future__ import annotations

from pathlib import Path

import vtk

from .model import ArrayAssociation, ArrayInfo, DatasetSummary


def normalize_input_path(path: str | Path) -> Path:
    """Return a normalized filesystem path."""
    return Path(path).expanduser().resolve(strict=False)


def _collect_array_info(
    attributes: vtk.vtkDataSetAttributes,
    association: ArrayAssociation,
) -> tuple[ArrayInfo, ...]:
    """Collect array descriptors from a VTK attribute container."""
    arrays: list[ArrayInfo] = []
    for index in range(attributes.GetNumberOfArrays()):
        array = attributes.GetAbstractArray(index)
        if array is None:
            continue

        name = array.GetName() or f"<unnamed_{index}>"
        arrays.append(
            ArrayInfo(
                name=name,
                association=association,
                components=array.GetNumberOfComponents(),
                tuples=array.GetNumberOfTuples(),
            )
        )
    return tuple(arrays)


def summarize_unstructured_grid(
    grid: vtk.vtkUnstructuredGrid,
    source_path: str | Path,
) -> DatasetSummary:
    """Build a dataset summary from an in-memory VTK unstructured grid."""
    normalized_path = normalize_input_path(source_path)
    return DatasetSummary(
        source_path=normalized_path,
        n_points=grid.GetNumberOfPoints(),
        n_cells=grid.GetNumberOfCells(),
        point_arrays=_collect_array_info(grid.GetPointData(), "point"),
        cell_arrays=_collect_array_info(grid.GetCellData(), "cell"),
    )


def load_unstructured_grid(path: str | Path) -> vtk.vtkUnstructuredGrid:
    """Load a VTU file into a VTK unstructured grid."""
    input_path = normalize_input_path(path)
    if not input_path.is_file():
        raise FileNotFoundError(f"VTU file not found: {input_path}")

    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(str(input_path))
    reader.Update()

    grid = vtk.vtkUnstructuredGrid()
    grid.ShallowCopy(reader.GetOutput())
    return grid


def inspect_dataset(path: str | Path) -> DatasetSummary:
    """Inspect a VTU file and summarize its arrays and topology."""
    input_path = normalize_input_path(path)
    grid = load_unstructured_grid(input_path)
    return summarize_unstructured_grid(grid=grid, source_path=input_path)
