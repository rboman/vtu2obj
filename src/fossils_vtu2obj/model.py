"""Shared dataclasses for the conversion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

ArrayAssociation = Literal["point", "cell"]


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
    colormap: str = "rainbow"
    vmin: float | None = None
    vmax: float | None = None
    n_colors: int = 256
    texture_height: int = 16


@dataclass(frozen=True)
class ExportBundle:
    """Group the three output files produced by conversion."""

    obj_path: Path
    mtl_path: Path
    texture_path: Path
