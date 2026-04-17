import pytest

from fossils_vtu2obj.surface import extract_surface


def test_extract_surface_is_reserved_for_step_two() -> None:
    with pytest.raises(NotImplementedError):
        extract_surface(object())
