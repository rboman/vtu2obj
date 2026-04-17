"""Command-line interface for fossils-vtu2obj."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .arrays import find_array, list_cell_arrays, list_point_arrays, require_array
from .colormaps import require_colormap_name
from .export_obj import export_obj_bundle
from .gui.app import launch_gui
from .integrations.fossils import detect_native_bridge
from .io_vtk import inspect_dataset, load_unstructured_grid
from .surface import extract_surface
from .texture import build_palette_texture
from .uvmap import apply_scalar_uv_map

app = typer.Typer(
    help=(
        "Convert VTU FEM results into extracted surface meshes, OBJ files, "
        "palette textures, and MTL files."
    ),
    invoke_without_command=True,
    no_args_is_help=True,
)

InputPathArgument = Annotated[
    Path,
    typer.Argument(
        ...,
        help="Path to the VTU file to inspect.",
    ),
]
PreviewInputPathArgument = Annotated[
    Path,
    typer.Argument(
        ...,
        help="Path to the VTU file to preview.",
    ),
]
ConvertInputPathArgument = Annotated[
    Path,
    typer.Argument(
        ...,
        help="Path to the VTU file to convert.",
    ),
]
OutputPrefixArgument = Annotated[
    Path,
    typer.Argument(
        ...,
        help="Output path prefix for OBJ, MTL, and PNG files.",
    ),
]
FieldOption = Annotated[
    str,
    typer.Option(
        ...,
        "--field",
        help="Scalar field used for coloring.",
    ),
]
ColormapOption = Annotated[
    str,
    typer.Option(
        "--colormap",
        help="Name of the colormap preset.",
    ),
]
VMinOption = Annotated[
    float | None,
    typer.Option(
        "--vmin",
        help="Optional lower bound for scalar mapping.",
    ),
]
VMaxOption = Annotated[
    float | None,
    typer.Option(
        "--vmax",
        help="Optional upper bound for scalar mapping.",
    ),
]
NColorsOption = Annotated[
    int,
    typer.Option(
        "--n-colors",
        min=2,
        help="Number of discrete color bins.",
    ),
]


def _version_callback(value: bool) -> None:
    """Print the version and exit when requested."""
    if value:
        typer.echo(__version__)
        raise typer.Exit()


def _pending_command(command_name: str, step_name: str) -> None:
    """Exit with a clear message for bootstrap-only commands."""
    typer.secho(
        f"The '{command_name}' command is reserved in the bootstrap and will be "
        f"implemented in {step_name}.",
        fg=typer.colors.YELLOW,
    )
    raise typer.Exit(code=1)


def _handle_cli_error(exc: Exception) -> None:
    """Render a recoverable CLI error and exit with status code 1."""
    typer.secho(str(exc), fg=typer.colors.RED)
    raise typer.Exit(code=1) from exc


def _array_kind_label(components: int) -> str:
    """Return a human-readable array kind from its component count."""
    if components == 1:
        return "scalar"
    if components == 3:
        return "vector"
    if components in {6, 9}:
        return "tensor"
    return "multi-component"


def _print_array_section(title: str, count: int, arrays: object) -> None:
    """Print one array section in a stable CLI format."""
    typer.echo(f"{title}: {count}")
    for array in arrays:
        kind = _array_kind_label(array.components)
        typer.echo(
            f"  - {array.name} [{kind}, components={array.components}, "
            f"tuples={array.tuples}]"
        )


def _print_summary(input_path: Path, include_counts_only: bool = False) -> None:
    """Inspect a VTU file and print a stable human-readable summary."""
    summary = inspect_dataset(input_path)
    point_arrays = list_point_arrays(summary)
    cell_arrays = list_cell_arrays(summary)

    typer.echo(f"File: {summary.source_path}")
    typer.echo(f"Points: {summary.n_points}")
    typer.echo(f"Cells: {summary.n_cells}")
    typer.echo(f"Point arrays: {len(point_arrays)}")
    typer.echo(f"Cell arrays: {len(cell_arrays)}")

    if include_counts_only:
        return

    _print_array_section("Point data arrays", len(point_arrays), point_arrays)
    _print_array_section("Cell data arrays", len(cell_arrays), cell_arrays)


def _validate_convert_field(input_path: Path, field_name: str) -> None:
    """Validate that a field is available for point-data conversion."""
    summary = inspect_dataset(input_path)
    point_array = find_array(summary, field_name, association="point")
    if point_array is not None:
        if not point_array.is_scalar:
            raise ValueError(
                f"Field '{field_name}' exists on points but is not scalar "
                f"(components={point_array.components})."
            )
        return

    cell_array = find_array(summary, field_name, association="cell")
    if cell_array is not None:
        raise ValueError(
            f"Field '{field_name}' currently exists only as cell data. "
            "Cell-data conversion is not implemented yet."
        )

    require_array(summary, field_name, association="point")


@app.callback()
def app_callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            is_eager=True,
            help="Show the package version and exit.",
        ),
    ] = False,
) -> None:
    """Run the CLI or display package metadata."""
    _ = version


@app.command("inspect")
def inspect_command(input_path: InputPathArgument) -> None:
    """Inspect a VTU dataset."""
    try:
        _print_summary(input_path, include_counts_only=True)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        _handle_cli_error(exc)


@app.command("list-arrays")
def list_arrays_command(input_path: InputPathArgument) -> None:
    """List point and cell arrays found in a VTU dataset."""
    try:
        _print_summary(input_path)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        _handle_cli_error(exc)


@app.command("preview")
def preview_command(
    input_path: PreviewInputPathArgument,
    field: FieldOption,
    colormap: ColormapOption = "rainbow",
) -> None:
    """Preview a scalar field or textured surface."""
    _ = (input_path, field, colormap)
    _pending_command("preview", "step 4")


@app.command("convert")
def convert_command(
    input_path: ConvertInputPathArgument,
    output_prefix: OutputPrefixArgument,
    field: FieldOption,
    colormap: ColormapOption = "rainbow",
    vmin: VMinOption = None,
    vmax: VMaxOption = None,
    n_colors: NColorsOption = 256,
) -> None:
    """Convert a VTU dataset into OBJ, MTL, and PNG outputs."""
    try:
        require_colormap_name(colormap)
        _validate_convert_field(input_path, field)

        grid = load_unstructured_grid(input_path)
        surface = extract_surface(grid, triangulate=True)
        textured_surface = apply_scalar_uv_map(
            surface,
            field,
            vmin=vmin,
            vmax=vmax,
            n_colors=n_colors,
        )
        texture_image = build_palette_texture(colormap, n_colors=n_colors)
        bundle = export_obj_bundle(textured_surface, output_prefix, texture_image)
    except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
        _handle_cli_error(exc)

    typer.echo(f"OBJ: {bundle.obj_path}")
    typer.echo(f"MTL: {bundle.mtl_path}")
    typer.echo(f"PNG: {bundle.texture_path}")


@app.command("gui")
def gui_command() -> None:
    """Launch the future GUI entry point."""
    try:
        launch_gui()
    except RuntimeError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc
    except NotImplementedError as exc:
        typer.secho(str(exc), fg=typer.colors.YELLOW)
        raise typer.Exit(code=1) from exc


@app.command("native-status")
def native_status_command() -> None:
    """Report the availability of the optional fossils native bridge."""
    status = detect_native_bridge()
    color = typer.colors.GREEN if status.available else typer.colors.BLUE
    typer.secho(status.detail, fg=color)
    if status.module_name:
        typer.echo(f"Module: {status.module_name}")


def main() -> None:
    """Console-script entry point."""
    app()
