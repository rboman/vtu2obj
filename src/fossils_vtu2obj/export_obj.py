"""OBJ, MTL, and texture export helpers."""

from __future__ import annotations

from pathlib import Path

import vtk

from .model import ExportBundle
from .texture import write_palette_texture


def expected_export_bundle(output_prefix: str | Path) -> ExportBundle:
    """Return the expected output file set for a given prefix."""
    prefix = Path(output_prefix)
    return ExportBundle(
        obj_path=prefix.with_suffix(".obj"),
        mtl_path=prefix.with_suffix(".mtl"),
        texture_path=prefix.with_suffix(".png"),
    )


def _write_mtl_fallback(path: Path, texture_name: str) -> None:
    """Write a minimal MTL file when VTK does not create one."""
    path.write_text(f"newmtl model\nmap_Kd {texture_name}\n", encoding="utf-8")


def export_obj_bundle(
    polydata: vtk.vtkPolyData,
    output_prefix: str | Path,
    texture_image: vtk.vtkImageData,
) -> ExportBundle:
    """Export the OBJ geometry, MTL file, and PNG texture."""
    if not isinstance(polydata, vtk.vtkPolyData):
        raise TypeError("export_obj_bundle expects a vtkPolyData input.")
    if polydata.GetPointData().GetTCoords() is None:
        raise ValueError(
            "PolyData must contain point texture coordinates before export."
        )
    if not isinstance(texture_image, vtk.vtkImageData):
        raise TypeError("export_obj_bundle expects a vtkImageData texture input.")

    bundle = expected_export_bundle(output_prefix)
    bundle.obj_path.parent.mkdir(parents=True, exist_ok=True)

    write_palette_texture(texture_image, bundle.texture_path)

    writer = vtk.vtkOBJWriter()
    writer.SetFileName(str(bundle.obj_path))
    writer.SetInputData(polydata)
    writer.SetTextureFileName(bundle.texture_path.name)
    writer.Write()
    if writer.GetErrorCode() != 0:
        raise RuntimeError(f"Failed to write OBJ bundle: {bundle.obj_path}")

    if not bundle.obj_path.is_file():
        raise RuntimeError(f"OBJ file was not created: {bundle.obj_path}")
    if not bundle.mtl_path.is_file():
        _write_mtl_fallback(bundle.mtl_path, bundle.texture_path.name)

    return bundle
