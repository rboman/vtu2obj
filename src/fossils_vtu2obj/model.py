"""Shared dataclasses for the conversion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .defaults import (
    DEFAULT_BACKGROUND_PRESET,
    DEFAULT_CAMERA_PRESET,
    DEFAULT_COLORMAP_NAME,
    DEFAULT_LIGHTING_INTENSITY,
    DEFAULT_LIGHTING_PRESET,
    DEFAULT_N_COLORS,
    DEFAULT_TEXTURE_HEIGHT,
)

ArrayAssociation = Literal["point", "cell"]
RgbColor = tuple[float, float, float]
BackgroundPreset = Literal[
    "current_solid",
    "paraview_dark_gradient",
    "black",
    "white",
]
LightingPreset = Literal["flat", "studio_soft", "studio_contrast"]
CameraPreset = Literal["3d_angled", "+X", "-X", "+Y", "-Y", "+Z", "-Z"]


@dataclass(frozen=True)
class ArrayInfo:
    """Describe a data array discovered on a VTK dataset."""

    name: str
    association: ArrayAssociation
    components: int
    tuples: int

    @property
    def is_scalar(self) -> bool:
        """Return ``True`` when the array has a single component."""
        return self.components == 1

    @property
    def is_vector(self) -> bool:
        """Return ``True`` when the array looks like a 3D vector."""
        return self.components == 3

    @property
    def is_tensor(self) -> bool:
        """Return ``True`` when the array looks like a tensor."""
        return self.components in {6, 9}


@dataclass(frozen=True)
class DatasetSummary:
    """Summarize a VTU dataset for inspection and validation."""

    source_path: Path
    n_points: int
    n_cells: int
    point_arrays: tuple[ArrayInfo, ...] = ()
    cell_arrays: tuple[ArrayInfo, ...] = ()


@dataclass(frozen=True)
class ScalarMappingOptions:
    """Hold scalar-to-color mapping parameters."""

    field_name: str
    colormap: str = DEFAULT_COLORMAP_NAME
    vmin: float | None = None
    vmax: float | None = None
    n_colors: int = DEFAULT_N_COLORS
    texture_height: int = DEFAULT_TEXTURE_HEIGHT


@dataclass(frozen=True)
class ExportBundle:
    """Group the three output files produced by conversion."""

    obj_path: Path
    mtl_path: Path
    texture_path: Path


@dataclass(frozen=True)
class ObjBundlePaths:
    """Describe an OBJ bundle that may or may not include MTL and texture files."""

    obj_path: Path
    mtl_path: Path | None = None
    texture_path: Path | None = None

    @property
    def has_mtl(self) -> bool:
        """Return ``True`` when the OBJ bundle resolved an MTL file."""
        return self.mtl_path is not None

    @property
    def has_texture(self) -> bool:
        """Return ``True`` when the OBJ bundle resolved a diffuse texture file."""
        return self.texture_path is not None


@dataclass(frozen=True)
class ViewDisplayOptions:
    """Control the auxiliary overlays shown in one VTK viewport."""

    show_edges: bool
    edge_color: RgbColor
    show_axes: bool
    show_bounding_box: bool = False
    background_preset: BackgroundPreset = DEFAULT_BACKGROUND_PRESET
    lighting_preset: LightingPreset = DEFAULT_LIGHTING_PRESET
    lighting_intensity: int = DEFAULT_LIGHTING_INTENSITY
    camera_preset: CameraPreset = DEFAULT_CAMERA_PRESET


@dataclass(frozen=True)
class MeshInfo:
    """Summarize the mesh and display state shown in one GUI viewport."""

    source_path: Path | None
    n_points: int
    n_cells: int
    point_arrays: int | None = None
    cell_arrays: int | None = None
    field_name: str | None = None
    field_association: ArrayAssociation | None = None
    scalar_range: tuple[float, float] | None = None
    mtl_path: Path | None = None
    texture_path: Path | None = None
    has_mtl: bool | None = None
    has_texture: bool | None = None
    has_tcoords: bool = False
    has_normals: bool = False
    texture_size: tuple[int, int] | None = None

    def as_lines(self) -> tuple[str, ...]:
        """Render the summary as stable, human-readable lines."""
        lines: list[str] = []
        if self.source_path is not None:
            lines.append(f"Source: {self.source_path}")

        lines.append(f"Points: {self.n_points}")
        lines.append(f"Cells: {self.n_cells}")

        if self.point_arrays is not None:
            lines.append(f"Point arrays: {self.point_arrays}")
        if self.cell_arrays is not None:
            lines.append(f"Cell arrays: {self.cell_arrays}")
        if self.field_name is not None:
            lines.append(f"Field: {self.field_name}")
        if self.field_association is not None:
            lines.append(f"Association: {self.field_association}")
        if self.scalar_range is not None:
            vmin, vmax = self.scalar_range
            lines.append(f"Scalar range: [{vmin:.6g}, {vmax:.6g}]")

        if self.has_mtl is not None:
            lines.append("MTL: present" if self.has_mtl else "MTL: missing")
            if self.mtl_path is not None:
                lines.append(f"MTL path: {self.mtl_path}")
        if self.has_texture is not None:
            lines.append(
                "Texture: present" if self.has_texture else "Texture: missing"
            )
            if self.texture_path is not None:
                lines.append(f"Texture path: {self.texture_path}")
            if self.texture_size is not None:
                width, height = self.texture_size
                lines.append(f"Texture size: {width} x {height} px")

        lines.append("UVs: present" if self.has_tcoords else "UVs: missing")
        lines.append("Normals: present" if self.has_normals else "Normals: missing")
        return tuple(lines)
