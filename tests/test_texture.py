import pytest

from fossils_vtu2obj.texture import validate_texture_shape


def test_validate_texture_shape_returns_dimensions() -> None:
    assert validate_texture_shape(256, 16) == (256, 16)


def test_validate_texture_shape_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        validate_texture_shape(1, 16)
