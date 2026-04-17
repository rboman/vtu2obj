"""Palette texture helpers."""

from __future__ import annotations


def validate_texture_shape(n_colors: int, height: int = 16) -> tuple[int, int]:
    """Validate and return texture dimensions for a palette image."""
    if n_colors <= 1:
        raise ValueError("n_colors must be greater than 1.")
    if height <= 0:
        raise ValueError("Texture height must be positive.")
    return n_colors, height


def build_palette_texture(*args: object, **kwargs: object) -> object:
    """Build a VTK image containing the discrete palette texture."""
    raise NotImplementedError("Texture generation will be implemented in step 3.")
