"""Helpers for an optional future fossils native bridge."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from importlib.util import find_spec
from types import ModuleType

DEFAULT_NATIVE_MODULE_CANDIDATES = (
    "fossils_vtu2obj_native",
    "fossils_vtu2obj._native",
)


@dataclass(frozen=True)
class NativeBridgeStatus:
    """Describe whether an optional native bridge is available."""

    available: bool
    module_name: str | None
    detail: str


def detect_native_bridge(
    module_candidates: tuple[str, ...] = DEFAULT_NATIVE_MODULE_CANDIDATES,
) -> NativeBridgeStatus:
    """Inspect the Python environment for an installed native bridge."""
    for module_name in module_candidates:
        if find_spec(module_name) is not None:
            return NativeBridgeStatus(
                available=True,
                module_name=module_name,
                detail="Optional fossils native bridge detected.",
            )
    return NativeBridgeStatus(
        available=False,
        module_name=None,
        detail="Optional fossils native bridge is not installed.",
    )


def load_native_bridge(
    module_candidates: tuple[str, ...] = DEFAULT_NATIVE_MODULE_CANDIDATES,
) -> ModuleType | None:
    """Import and return the first available native bridge module."""
    status = detect_native_bridge(module_candidates=module_candidates)
    if not status.available or status.module_name is None:
        return None
    return import_module(status.module_name)
