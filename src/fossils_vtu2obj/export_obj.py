"""OBJ, MTL, and texture export helpers."""

from __future__ import annotations

from pathlib import Path

from .model import ExportBundle


def expected_export_bundle(output_prefix: str | Path) -> ExportBundle:
    """Return the expected output file set for a given prefix."""
    prefix = Path(output_prefix)
    return ExportBundle(
        obj_path=prefix.with_suffix(".obj"),
        mtl_path=prefix.with_suffix(".mtl"),
        texture_path=prefix.with_suffix(".png"),
    )


def export_obj_bundle(*args: object, **kwargs: object) -> ExportBundle:
    """Export the OBJ geometry, MTL file, and PNG texture."""
    raise NotImplementedError("OBJ export will be implemented in step 3.")
