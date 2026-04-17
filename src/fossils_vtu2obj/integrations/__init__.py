"""Optional integrations for external projects such as fossils."""

from .fossils import NativeBridgeStatus, detect_native_bridge, load_native_bridge

__all__ = [
    "NativeBridgeStatus",
    "detect_native_bridge",
    "load_native_bridge",
]
