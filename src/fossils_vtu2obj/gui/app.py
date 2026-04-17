"""GUI application bootstrap."""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path


def launch_gui(initial_path: str | Path | None = None) -> None:
    """Launch the Qt application when GUI support is installed."""
    if find_spec("PyQt5") is None:
        raise RuntimeError(
            "PyQt5 is not installed. Install the package with the [gui] extra."
        )

    from PyQt5 import QtWidgets

    from .main_window import MainWindow

    application = QtWidgets.QApplication.instance()
    owns_application = application is None
    if application is None:
        application = QtWidgets.QApplication([])

    window = MainWindow(initial_path=initial_path)
    window.show()

    if owns_application:
        application.exec_()
