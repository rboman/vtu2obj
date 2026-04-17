import pytest
import vtk

from fossils_vtu2obj.defaults import (
    DEFAULT_RENDERER_BACKGROUND,
    DEFAULT_SCALAR_BAR_LABEL_FONT_SIZE,
    DEFAULT_SCALAR_BAR_TITLE_FONT_SIZE,
    DEFAULT_SCALAR_BAR_WIDTH,
)
from fossils_vtu2obj.preview import (
    PreviewScene,
    build_obj_bundle_preview_scene,
    build_scalar_preview_scene,
    build_textured_preview_scene,
    build_volume_preview_scene,
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
    assert scene.edge_actor is not None
    assert scene.renderer.GetActors().GetNumberOfItems() == 2
    assert scene.renderer.GetGradientBackground() == 0
    assert scene.renderer.GetBackground() == pytest.approx(DEFAULT_RENDERER_BACKGROUND)
    assert scene.scalar_bar.GetWidth() == pytest.approx(DEFAULT_SCALAR_BAR_WIDTH)
    assert (
        scene.scalar_bar.GetTitleTextProperty().GetFontSize()
        == DEFAULT_SCALAR_BAR_TITLE_FONT_SIZE
    )
    assert (
        scene.scalar_bar.GetLabelTextProperty().GetFontSize()
        == DEFAULT_SCALAR_BAR_LABEL_FONT_SIZE
    )


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
    assert scene.edge_actor is not None


def test_build_scalar_preview_scene_supports_scalar_cell_data(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    surface = extract_surface(sample_unstructured_grid)
    scene = build_scalar_preview_scene(
        surface,
        "cell_stress_von_mises",
        colormap="cool_to_warm",
        n_colors=8,
    )

    assert isinstance(scene, PreviewScene)
    assert scene.surface.GetPointData().GetArray("cell_stress_von_mises") is not None


def test_build_volume_preview_scene_uses_volume_mesh_stats(
    sample_unstructured_grid: vtk.vtkUnstructuredGrid,
) -> None:
    scene = build_volume_preview_scene(
        sample_unstructured_grid,
        "cell_stress_von_mises",
        colormap="cool_to_warm",
        n_colors=8,
    )

    assert isinstance(scene, PreviewScene)
    assert scene.info is not None
    assert scene.info.n_points == sample_unstructured_grid.GetNumberOfPoints()
    assert scene.info.n_cells == sample_unstructured_grid.GetNumberOfCells()
    assert scene.info.field_association == "cell"
    assert scene.edge_actor is not None


def test_build_obj_bundle_preview_scene_loads_texture(sample_obj_bundle) -> None:
    scene = build_obj_bundle_preview_scene(sample_obj_bundle.obj_path)

    assert isinstance(scene, PreviewScene)
    assert scene.texture is not None
    assert scene.texture_image is not None
    assert scene.actor.GetTexture() is scene.texture
    assert scene.info is not None
    assert scene.info.has_texture is True
    assert scene.info.has_tcoords is True


def test_build_obj_bundle_preview_scene_falls_back_without_texture(
    sample_obj_bundle,
) -> None:
    sample_obj_bundle.texture_path.unlink()
    scene = build_obj_bundle_preview_scene(sample_obj_bundle.obj_path)

    assert isinstance(scene, PreviewScene)
    assert scene.texture is None
    assert scene.actor.GetTexture() is None
    assert scene.info is not None
    assert scene.info.has_mtl is True
    assert scene.info.has_texture is False
