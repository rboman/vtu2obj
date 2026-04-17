from fossils_vtu2obj.integrations.fossils import (
    detect_native_bridge,
    load_native_bridge,
)


def test_detect_native_bridge_is_safe_when_missing() -> None:
    status = detect_native_bridge()

    assert status.available is False
    assert status.module_name is None


def test_load_native_bridge_returns_none_when_missing() -> None:
    assert load_native_bridge() is None
