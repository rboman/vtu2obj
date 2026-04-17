"""VTK preview entry points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import vtk

from .colormaps import build_lookup_table, require_colormap_name
from .io_vtk import load_unstructured_grid
from .surface import extract_surface
from .texture import build_palette_texture
from .uvmap import apply_scalar_uv_map, resolve_scalar_range


@dataclass
class PreviewScene:
    """Keep the VTK objects that make up one preview scene alive."""

    renderer: vtk.vtkRenderer
    actor: vtk.vtkActor
    surface: vtk.vtkPolyData
    lookup_table: vtk.vtkLookupTable | None = None
    scalar_bar: vtk.vtkScalarBarActor | None = None
    texture_image: vtk.vtkImageData | None = None
    texture: vtk.vtkTexture | None = None


def _require_scalar_point_array(
    surface: vtk.vtkPolyData,
    field_name: str,
) -> vtk.vtkDataArray:
    """Return a scalar point-data array or raise a clear validation error."""
    scalar_array = surface.GetPointData().GetArray(field_name)
    if scalar_array is None:
        raise ValueError(
            f"Unknown point-data field '{field_name}' on the surface mesh."
        )
    if scalar_array.GetNumberOfComponents() != 1:
        raise ValueError(
            f"Field '{field_name}' must be a scalar point-data array for preview."
        )
    return scalar_array


def _build_base_renderer() -> vtk.vtkRenderer:
    """Create a renderer with the shared visual defaults."""
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.10, 0.12, 0.16)
    renderer.SetBackground2(0.22, 0.25, 0.32)
    renderer.GradientBackgroundOn()
    return renderer


def load_surface_for_preview(input_path: str | Path) -> vtk.vtkPolyData:
    """Load a VTU file and extract a triangulated surface for preview."""
    grid = load_unstructured_grid(input_path)
    return extract_surface(grid, triangulate=True)


def build_scalar_preview_scene(
    surface: vtk.vtkPolyData,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
) -> PreviewScene:
    """Build a renderer that previews a scalar field with a lookup table."""
    require_colormap_name(colormap)
    scalar_array = _require_scalar_point_array(surface, field_name)
    scalar_range = resolve_scalar_range(scalar_array, vmin=vmin, vmax=vmax)
    lookup_table = build_lookup_table(colormap, n_colors=n_colors)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(surface)
    mapper.SetLookupTable(lookup_table)
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray(field_name)
    mapper.SetScalarRange(*scalar_range)
    mapper.ScalarVisibilityOn()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(lookup_table)
    scalar_bar.SetTitle(field_name)
    scalar_bar.SetNumberOfLabels(5)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.AddViewProp(scalar_bar)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=surface,
        lookup_table=lookup_table,
        scalar_bar=scalar_bar,
    )


def build_textured_preview_scene(
    surface: vtk.vtkPolyData,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
    texture_height: int = 16,
) -> PreviewScene:
    """Build a renderer that previews the textured surface result."""
    require_colormap_name(colormap)
    _require_scalar_point_array(surface, field_name)

    mapped_surface = apply_scalar_uv_map(
        surface,
        field_name,
        vmin=vmin,
        vmax=vmax,
        n_colors=n_colors,
    )
    texture_image = build_palette_texture(
        colormap,
        n_colors=n_colors,
        height=texture_height,
    )

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(mapped_surface)
    mapper.ScalarVisibilityOff()

    texture = vtk.vtkTexture()
    texture.SetInputData(texture_image)
    texture.InterpolateOff()
    texture.RepeatOff()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.SetTexture(texture)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=mapped_surface,
        texture_image=texture_image,
        texture=texture,
    )


def show_preview_scene(
    scene: PreviewScene,
    *,
    title: str = "fossils-vtu2obj preview",
    window_size: tuple[int, int] = (1280, 800),
) -> vtk.vtkRenderWindow:
    """Open a VTK render window for a prepared preview scene."""
    render_window = vtk.vtkRenderWindow()
    render_window.SetWindowName(title)
    render_window.SetSize(*window_size)
    render_window.AddRenderer(scene.renderer)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.Initialize()
    render_window.Render()
    interactor.Start()
    return render_window


def preview_scalar_field(
    input_path: str | Path,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
) -> None:
    """Open a preview window using scalar coloring."""
    surface = load_surface_for_preview(input_path)
    scene = build_scalar_preview_scene(
        surface,
        field_name,
        colormap=colormap,
        vmin=vmin,
        vmax=vmax,
        n_colors=n_colors,
    )
    show_preview_scene(scene, title=f"Scalar Preview - {field_name}")


def preview_textured_surface(
    input_path: str | Path,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
    texture_height: int = 16,
) -> None:
    """Open a preview window using the generated texture."""
    surface = load_surface_for_preview(input_path)
    scene = build_textured_preview_scene(
        surface,
        field_name,
        colormap=colormap,
        vmin=vmin,
        vmax=vmax,
        n_colors=n_colors,
        texture_height=texture_height,
    )
    show_preview_scene(scene, title=f"Textured Preview - {field_name}")
