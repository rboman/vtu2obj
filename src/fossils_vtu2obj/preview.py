"""VTK preview entry points."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import vtk

from .colormaps import build_lookup_table, require_colormap_name
from .export_obj import resolve_obj_bundle_paths
from .io_vtk import load_unstructured_grid
from .model import ArrayAssociation, MeshInfo, ObjBundlePaths
from .surface import extract_surface
from .texture import build_palette_texture
from .uvmap import apply_scalar_uv_map, ensure_point_scalar_field, resolve_scalar_range


@dataclass
class PreviewScene:
    """Keep the VTK objects that make up one preview scene alive."""

    renderer: vtk.vtkRenderer
    actor: vtk.vtkActor
    surface: vtk.vtkDataSet
    edge_actor: vtk.vtkActor | None = None
    lookup_table: vtk.vtkLookupTable | None = None
    scalar_bar: vtk.vtkScalarBarActor | None = None
    texture_image: vtk.vtkImageData | None = None
    texture: vtk.vtkTexture | None = None
    info: MeshInfo | None = None


def resolve_dataset_scalar_field(
    dataset: vtk.vtkDataSet,
    field_name: str,
) -> tuple[ArrayAssociation, vtk.vtkDataArray]:
    """Return the scalar array matching ``field_name`` and its association."""
    if not isinstance(dataset, vtk.vtkDataSet):
        raise TypeError("resolve_dataset_scalar_field expects a VTK dataset input.")

    point_array = dataset.GetPointData().GetArray(field_name)
    if point_array is not None:
        if point_array.GetNumberOfComponents() != 1:
            raise ValueError(
                f"Field '{field_name}' exists on points but is not scalar."
            )
        return "point", point_array

    cell_array = dataset.GetCellData().GetArray(field_name)
    if cell_array is not None:
        if cell_array.GetNumberOfComponents() != 1:
            raise ValueError(
                f"Field '{field_name}' exists on cells but is not scalar."
            )
        return "cell", cell_array

    raise ValueError(f"Unknown scalar field '{field_name}' on the dataset.")


def _build_base_renderer() -> vtk.vtkRenderer:
    """Create a renderer with the shared visual defaults."""
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0.3199969482, 0.3400015259, 0.4299992370)
    renderer.GradientBackgroundOff()
    return renderer


def _build_edge_actor(dataset: vtk.vtkDataSet) -> vtk.vtkActor:
    """Create a separate actor that renders the dataset edges."""
    edge_filter = vtk.vtkExtractEdges()
    edge_filter.SetInputData(dataset)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(edge_filter.GetOutputPort())
    mapper.ScalarVisibilityOff()
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    mapper.SetRelativeCoincidentTopologyLineOffsetParameters(0.0, -8.0)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetLighting(False)
    actor.GetProperty().SetLineWidth(1.8)
    actor.GetProperty().SetRenderLinesAsTubes(True)
    actor.SetVisibility(False)
    actor.SetPickable(False)
    return actor


def _build_scalar_bar(
    lookup_table: vtk.vtkLookupTable,
    title: str,
) -> vtk.vtkScalarBarActor:
    """Create a scalar bar actor tied to one lookup table."""
    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(lookup_table)
    scalar_bar.SetTitle(title)
    scalar_bar.SetNumberOfLabels(5)
    return scalar_bar


def describe_dataset_mesh(
    dataset: vtk.vtkDataSet,
    *,
    source_path: str | Path | None = None,
    field_name: str | None = None,
    field_association: ArrayAssociation | None = None,
    scalar_range: tuple[float, float] | None = None,
) -> MeshInfo:
    """Collect the dataset statistics shown in one GUI information panel."""
    resolved_path = None
    if source_path is not None:
        resolved_path = Path(source_path).expanduser().resolve(strict=False)

    return MeshInfo(
        source_path=resolved_path,
        n_points=dataset.GetNumberOfPoints(),
        n_cells=dataset.GetNumberOfCells(),
        point_arrays=dataset.GetPointData().GetNumberOfArrays(),
        cell_arrays=dataset.GetCellData().GetNumberOfArrays(),
        field_name=field_name,
        field_association=field_association,
        scalar_range=scalar_range,
        has_tcoords=dataset.GetPointData().GetTCoords() is not None,
        has_normals=dataset.GetPointData().GetNormals() is not None,
    )


def describe_obj_bundle_mesh(
    polydata: vtk.vtkPolyData,
    bundle: ObjBundlePaths,
) -> MeshInfo:
    """Collect the mesh and bundle details shown for one loaded OBJ scene."""
    return MeshInfo(
        source_path=bundle.obj_path,
        n_points=polydata.GetNumberOfPoints(),
        n_cells=polydata.GetNumberOfCells(),
        mtl_path=bundle.mtl_path,
        texture_path=bundle.texture_path,
        has_mtl=bundle.has_mtl,
        has_texture=bundle.has_texture,
        has_tcoords=polydata.GetPointData().GetTCoords() is not None,
        has_normals=polydata.GetPointData().GetNormals() is not None,
    )


def load_surface_for_preview(input_path: str | Path) -> vtk.vtkPolyData:
    """Load a VTU file and extract a triangulated surface for preview."""
    grid = load_unstructured_grid(input_path)
    return extract_surface(grid, triangulate=True)


def build_volume_preview_scene(
    dataset: vtk.vtkDataSet,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
    source_path: str | Path | None = None,
) -> PreviewScene:
    """Build a renderer for the original volume mesh colored by one scalar field."""
    require_colormap_name(colormap)
    association, scalar_array = resolve_dataset_scalar_field(dataset, field_name)
    scalar_range = resolve_scalar_range(scalar_array, vmin=vmin, vmax=vmax)
    lookup_table = build_lookup_table(colormap, n_colors=n_colors)

    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputData(dataset)
    mapper.SetLookupTable(lookup_table)
    mapper.SetScalarRange(*scalar_range)
    mapper.SelectColorArray(field_name)
    mapper.ScalarVisibilityOn()
    if association == "point":
        mapper.SetScalarModeToUsePointFieldData()
    else:
        mapper.SetScalarModeToUseCellFieldData()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    edge_actor = _build_edge_actor(dataset)
    scalar_bar = _build_scalar_bar(lookup_table, field_name)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.AddActor(edge_actor)
    renderer.AddViewProp(scalar_bar)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=dataset,
        edge_actor=edge_actor,
        lookup_table=lookup_table,
        scalar_bar=scalar_bar,
        info=describe_dataset_mesh(
            dataset,
            source_path=source_path,
            field_name=field_name,
            field_association=association,
            scalar_range=scalar_range,
        ),
    )


def build_scalar_preview_scene(
    surface: vtk.vtkPolyData,
    field_name: str,
    *,
    colormap: str = "rainbow",
    vmin: float | None = None,
    vmax: float | None = None,
    n_colors: int = 256,
    source_path: str | Path | None = None,
) -> PreviewScene:
    """Build a renderer that previews a scalar field with a lookup table."""
    require_colormap_name(colormap)
    association, _ = resolve_dataset_scalar_field(surface, field_name)
    preview_surface, scalar_array = ensure_point_scalar_field(surface, field_name)
    scalar_range = resolve_scalar_range(scalar_array, vmin=vmin, vmax=vmax)
    lookup_table = build_lookup_table(colormap, n_colors=n_colors)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(preview_surface)
    mapper.SetLookupTable(lookup_table)
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray(field_name)
    mapper.SetScalarRange(*scalar_range)
    mapper.ScalarVisibilityOn()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    edge_actor = _build_edge_actor(preview_surface)
    scalar_bar = _build_scalar_bar(lookup_table, field_name)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.AddActor(edge_actor)
    renderer.AddViewProp(scalar_bar)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=preview_surface,
        edge_actor=edge_actor,
        lookup_table=lookup_table,
        scalar_bar=scalar_bar,
        info=describe_dataset_mesh(
            preview_surface,
            source_path=source_path,
            field_name=field_name,
            field_association=association,
            scalar_range=scalar_range,
        ),
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
    source_path: str | Path | None = None,
) -> PreviewScene:
    """Build a renderer that previews the textured surface result."""
    require_colormap_name(colormap)
    association, _ = resolve_dataset_scalar_field(surface, field_name)

    mapped_surface = apply_scalar_uv_map(
        surface,
        field_name,
        vmin=vmin,
        vmax=vmax,
        n_colors=n_colors,
    )
    scalar_array = mapped_surface.GetPointData().GetArray(field_name)
    if scalar_array is None:
        raise RuntimeError(f"Mapped surface is missing field '{field_name}'.")

    scalar_range = resolve_scalar_range(scalar_array, vmin=vmin, vmax=vmax)
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

    edge_actor = _build_edge_actor(mapped_surface)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.AddActor(edge_actor)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=mapped_surface,
        edge_actor=edge_actor,
        texture_image=texture_image,
        texture=texture,
        info=describe_dataset_mesh(
            mapped_surface,
            source_path=source_path,
            field_name=field_name,
            field_association=association,
            scalar_range=scalar_range,
        ),
    )


def build_obj_bundle_preview_scene(
    bundle: ObjBundlePaths | str | Path,
) -> PreviewScene:
    """Build a renderer for one exported OBJ bundle on disk."""
    if isinstance(bundle, ObjBundlePaths):
        resolved_bundle = bundle
    else:
        resolved_bundle = resolve_obj_bundle_paths(bundle)

    reader = vtk.vtkOBJReader()
    reader.SetFileName(str(resolved_bundle.obj_path))
    reader.Update()

    polydata = vtk.vtkPolyData()
    polydata.ShallowCopy(reader.GetOutput())
    if polydata.GetNumberOfPoints() == 0:
        raise RuntimeError(f"Failed to load OBJ geometry: {resolved_bundle.obj_path}")

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    mapper.ScalarVisibilityOff()

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    texture_image: vtk.vtkImageData | None = None
    texture: vtk.vtkTexture | None = None
    if resolved_bundle.texture_path is not None:
        image_reader = vtk.vtkPNGReader()
        image_reader.SetFileName(str(resolved_bundle.texture_path))
        image_reader.Update()

        texture_image = vtk.vtkImageData()
        texture_image.ShallowCopy(image_reader.GetOutput())

        texture = vtk.vtkTexture()
        texture.SetInputData(texture_image)
        texture.InterpolateOff()
        texture.RepeatOff()
        actor.SetTexture(texture)

    edge_actor = _build_edge_actor(polydata)

    renderer = _build_base_renderer()
    renderer.AddActor(actor)
    renderer.AddActor(edge_actor)
    renderer.ResetCamera()

    return PreviewScene(
        renderer=renderer,
        actor=actor,
        surface=polydata,
        edge_actor=edge_actor,
        texture_image=texture_image,
        texture=texture,
        info=describe_obj_bundle_mesh(polydata, resolved_bundle),
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
    interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
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
        source_path=input_path,
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
        source_path=input_path,
    )
    show_preview_scene(scene, title=f"Textured Preview - {field_name}")
