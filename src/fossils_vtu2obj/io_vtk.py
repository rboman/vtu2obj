"""VTK I/O entry points."""

from __future__ import annotations

from pathlib import Path

from .model import DatasetSummary


def normalize_input_path(path: str | Path) -> Path:
    """Return a normalized filesystem path."""
    return Path(path).expanduser()


def load_unstructured_grid(path: str | Path) -> object:
    """Load a VTU file into a VTK unstructured grid."""
    raise NotImplementedError("VTU loading will be implemented in step 2.")


def inspect_dataset(path: str | Path) -> DatasetSummary:
    """Inspect a VTU file and summarize its arrays and topology."""
    raise NotImplementedError("Dataset inspection will be implemented in step 2.")
