"""OBJ, MTL, and texture export helpers."""

from __future__ import annotations

from pathlib import Path

import vtk

from .model import ExportBundle, ObjBundlePaths
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


def _read_first_directive_value(path: Path, directive: str) -> str | None:
    """Return the first raw value associated with a text directive."""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.split("#", 1)[0].strip()
        if not stripped or not stripped.startswith(f"{directive} "):
            continue
        value = stripped[len(directive) :].strip()
        if value:
            return value
    return None


def read_obj_mtllib_reference(obj_path: str | Path) -> str | None:
    """Return the first MTL reference declared by an OBJ file, when present."""
    path = Path(obj_path)
    return _read_first_directive_value(path, "mtllib")


def read_mtl_diffuse_texture_reference(mtl_path: str | Path) -> str | None:
    """Return the first diffuse texture reference declared by an MTL file."""
    path = Path(mtl_path)
    return _read_first_directive_value(path, "map_Kd")


def resolve_obj_bundle_paths(obj_path: str | Path) -> ObjBundlePaths:
    """Resolve the MTL and texture paths associated with an OBJ file."""
    normalized_obj = Path(obj_path).expanduser().resolve(strict=False)
    if not normalized_obj.is_file():
        raise FileNotFoundError(f"OBJ file not found: {normalized_obj}")

    mtl_candidates: list[Path] = []
    mtllib_reference = read_obj_mtllib_reference(normalized_obj)
    if mtllib_reference:
        mtl_candidates.append(
            (normalized_obj.parent / mtllib_reference).resolve(strict=False)
        )

    default_mtl = normalized_obj.with_suffix(".mtl")
    if default_mtl not in mtl_candidates:
        mtl_candidates.append(default_mtl)

    resolved_mtl = next((path for path in mtl_candidates if path.is_file()), None)

    resolved_texture: Path | None = None
    if resolved_mtl is not None:
        texture_reference = read_mtl_diffuse_texture_reference(resolved_mtl)
        if texture_reference:
            texture_candidate = (resolved_mtl.parent / texture_reference).resolve(
                strict=False
            )
            if texture_candidate.is_file():
                resolved_texture = texture_candidate

    return ObjBundlePaths(
        obj_path=normalized_obj,
        mtl_path=resolved_mtl,
        texture_path=resolved_texture,
    )


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
