"""Scalar-to-UV mapping helpers."""


DEFAULT_V_COORD = 0.5


def validate_color_bins(n_colors: int) -> int:
    """Validate the requested number of color bins."""
    if n_colors <= 1:
        raise ValueError("n_colors must be greater than 1.")
    return n_colors


def bin_center(bin_index: int, n_colors: int) -> float:
    """Return the normalized center of a discrete color bin."""
    validate_color_bins(n_colors)
    if not 0 <= bin_index < n_colors:
        raise ValueError("bin_index must lie inside the palette.")
    return (bin_index + 0.5) / n_colors


def apply_scalar_uv_map(*args: object, **kwargs: object) -> object:
    """Attach texture coordinates derived from scalar values."""
    raise NotImplementedError("UV mapping will be implemented in step 3.")
