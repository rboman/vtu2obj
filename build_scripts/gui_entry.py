"""PyInstaller entry point for the GUI executable."""

from __future__ import annotations

import sys
from pathlib import Path

from fossils_vtu2obj.gui.app import launch_gui


def _initial_path_from_argv() -> Path | None:
    """Return an optional VTU path passed as first positional argument."""
    if len(sys.argv) <= 1:
        return None
    candidate = Path(sys.argv[1]).expanduser().resolve()
    return candidate


if __name__ == "__main__":
    launch_gui(initial_path=_initial_path_from_argv())
