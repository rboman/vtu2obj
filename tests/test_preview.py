import vtk

from fossils_vtu2obj.preview import (
    PreviewScene,
    build_scalar_preview_scene,
    build_textured_preview_scene,
)
from fossils_vtu2obj.surface import extract_surface


def test_build_scalar_preview_scene_returns_renderer_and_scalar_bar(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    surface = extract_surface(sample_unstructured_grid)
    scene = build_scalar_preview_scene(
        surface,
        "stress_von_mises",
        colormap="rainbow",
        n_colors=8,
    )

    assert isinstance(scene, PreviewScene)
    assert isinstance(scene.renderer, vtk.vtkRenderer)
    assert scene.scalar_bar is not None
    assert scene.lookup_table is not None
    assert scene.renderer.GetActors().GetNumberOfItems() == 1


def test_build_textured_preview_scene_adds_texture_to_actor(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    surface = extract_surface(sample_unstructured_grid)
    scene = build_textured_preview_scene(
        surface,
        "stress_von_mises",
        colormap="rainbow",
        n_colors=8,
    )

    assert isinstance(scene, PreviewScene)
    assert scene.texture_image is not None
    assert scene.texture is not None
    assert scene.actor.GetTexture() is scene.texture
    assert scene.surface.GetPointData().GetTCoords() is not None
