"""VTK preview entry points."""

from __future__ import annotations


def preview_scalar_field(*args: object, **kwargs: object) -> None:
    """Open a preview window using scalar coloring."""
    raise NotImplementedError("Scalar preview will be implemented in step 4.")


def preview_textured_surface(*args: object, **kwargs: object) -> None:
    """Open a preview window using the generated texture."""
    raise NotImplementedError("Textured preview will be implemented in step 4.")
