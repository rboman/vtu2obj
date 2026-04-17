import pytest
import vtk

from fossils_vtu2obj.colormaps import (
    BUILTIN_COLORMAPS,
    build_lookup_table,
    list_colormap_names,
    require_colormap_name,
    sample_colormap,
    table_value_to_uint8,
)


def test_list_colormap_names_matches_builtin_tuple() -> None:
    assert list_colormap_names() == BUILTIN_COLORMAPS


def test_require_colormap_name_rejects_unknown_values() -> None:
    with pytest.raises(ValueError):
        require_colormap_name("unknown")


def test_build_lookup_table_creates_requested_number_of_entries() -> None:
    lookup_table = build_lookup_table("rainbow", n_colors=8)

    assert isinstance(lookup_table, vtk.vtkLookupTable)
    assert lookup_table.GetNumberOfTableValues() == 8


def test_grayscale_sampling_spans_black_to_white() -> None:
    palette = sample_colormap("grayscale", n_colors=4)

    assert palette[0] == (0, 0, 0)
    assert palette[-1] == (255, 255, 255)


def test_table_value_to_uint8_reads_lookup_table_colors() -> None:
    lookup_table = build_lookup_table("grayscale", n_colors=2)

    assert table_value_to_uint8(lookup_table, 0) == (0, 0, 0)


def test_extended_scientific_colormap_names_are_available() -> None:
    for name in (
        "plasma_like",
        "magma_like",
        "inferno_like",
        "turbo_like",
        "blue_to_red",
        "black_body",
    ):
        assert name in BUILTIN_COLORMAPS


def test_extended_colormaps_can_be_sampled() -> None:
    for name in (
        "plasma_like",
        "magma_like",
        "inferno_like",
        "turbo_like",
        "blue_to_red",
        "black_body",
    ):
        palette = sample_colormap(name, n_colors=4)
        assert len(palette) == 4
