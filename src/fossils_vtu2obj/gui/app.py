"""GUI application bootstrap."""

from __future__ import annotations

from importlib.util import find_spec


def launch_gui() -> None:
    """Launch the Qt application when GUI support is installed."""
    if find_spec("PyQt5") is None:
        raise RuntimeError(
            "PyQt5 is not installed. Install the package with the [gui] extra."
        )
    raise NotImplementedError("The GUI will be implemented in step 4.")
