import pytest

from fossils_vtu2obj.colormaps import (
    BUILTIN_COLORMAPS,
    list_colormap_names,
    require_colormap_name,
)


def test_list_colormap_names_matches_builtin_tuple() -> None:
    assert list_colormap_names() == BUILTIN_COLORMAPS


def test_require_colormap_name_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        require_colormap_name("unknown")
