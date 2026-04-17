import pytest

from fossils_vtu2obj.uvmap import DEFAULT_V_COORD, bin_center


def test_bin_center_returns_middle_of_bin() -> None:
    assert bin_center(0, 4) == 0.125
    assert bin_center(3, 4) == 0.875
    assert DEFAULT_V_COORD == 0.5


def test_bin_center_rejects_invalid_index() -> None:
    with pytest.raises(ValueError):
        bin_center(4, 4)
