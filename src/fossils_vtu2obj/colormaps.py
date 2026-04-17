"""Colormap declarations and validation helpers."""

from __future__ import annotations

BUILTIN_COLORMAPS = (
    "rainbow",
    "cool_to_warm",
    "grayscale",
    "viridis_like",
)


def list_colormap_names() -> tuple[str, ...]:
    """Return the supported bootstrap colormap names."""
    return BUILTIN_COLORMAPS


def require_colormap_name(name: str) -> str:
    """Validate a colormap name and return it unchanged."""
    if name not in BUILTIN_COLORMAPS:
        raise ValueError(
            f"Unknown colormap '{name}'. Available colormaps: {BUILTIN_COLORMAPS}"
        )
    return name
