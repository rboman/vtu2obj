from pathlib import Path

import vtk

from fossils_vtu2obj.export_obj import (
    expected_export_bundle,
    export_obj_bundle,
    read_mtl_diffuse_texture_reference,
    read_obj_mtllib_reference,
    resolve_obj_bundle_paths,
)
from fossils_vtu2obj.texture import build_palette_texture
from fossils_vtu2obj.uvmap import apply_scalar_uv_map


def test_expected_export_bundle_uses_output_prefix() -> None:
    bundle = expected_export_bundle(Path("out/model"))

    assert bundle.obj_path == Path("out/model.obj")
    assert bundle.mtl_path == Path("out/model.mtl")
    assert bundle.texture_path == Path("out/model.png")


def test_export_obj_bundle_writes_obj_mtl_and_png(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
    tmp_path: Path,
) -> None:
    polydata = vtk.vtkPolyData()
    polydata.SetPoints(sample_unstructured_grid.GetPoints())

    tetra = sample_unstructured_grid.GetCell(0)
    triangles = vtk.vtkCellArray()
    for face_id in range(tetra.GetNumberOfFaces()):
        face = tetra.GetFace(face_id)
        triangle = vtk.vtkTriangle()
        for point_id in range(3):
            triangle.GetPointIds().SetId(point_id, face.GetPointId(point_id))
        triangles.InsertNextCell(triangle)

    polydata.SetPolys(triangles)
    polydata.GetPointData().ShallowCopy(sample_unstructured_grid.GetPointData())

    mapped = apply_scalar_uv_map(polydata, "stress_von_mises", n_colors=8)
    texture_image = build_palette_texture("rainbow", n_colors=8, height=4)
    bundle = export_obj_bundle(mapped, tmp_path / "model", texture_image)

    assert bundle.obj_path.is_file()
    assert bundle.mtl_path.is_file()
    assert bundle.texture_path.is_file()
    assert "mtllib model.mtl" in bundle.obj_path.read_text(encoding="utf-8")
    assert "map_Kd model.png" in bundle.mtl_path.read_text(encoding="utf-8")


def test_resolve_obj_bundle_paths_reads_exported_bundle(sample_obj_bundle) -> None:
    resolved = resolve_obj_bundle_paths(sample_obj_bundle.obj_path)

    assert resolved.obj_path == sample_obj_bundle.obj_path.resolve(strict=False)
    assert resolved.mtl_path == sample_obj_bundle.mtl_path.resolve(strict=False)
    assert resolved.texture_path == sample_obj_bundle.texture_path.resolve(strict=False)


def test_bundle_reference_helpers_parse_obj_and_mtl(sample_obj_bundle) -> None:
    assert read_obj_mtllib_reference(sample_obj_bundle.obj_path) == "model.mtl"
    assert (
        read_mtl_diffuse_texture_reference(sample_obj_bundle.mtl_path) == "model.png"
    )


def test_resolve_obj_bundle_paths_tolerates_missing_texture(tmp_path: Path) -> None:
    obj_path = tmp_path / "model.obj"
    mtl_path = tmp_path / "model.mtl"
    obj_path.write_text("mtllib model.mtl\nv 0 0 0\n", encoding="utf-8")
    mtl_path.write_text("newmtl model\nmap_Kd missing.png\n", encoding="utf-8")

    resolved = resolve_obj_bundle_paths(obj_path)

    assert resolved.mtl_path == mtl_path.resolve(strict=False)
    assert resolved.texture_path is None
