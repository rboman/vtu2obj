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

    import vtk
    from PyQt5 import QtWidgets

    from .icons import create_app_icon
    from .main_window import MainWindow

    output_window = vtk.vtkOutputWindow()
    output_window.SetDisplayModeToNever()
    output_window.PromptUserOff()
    vtk.vtkOutputWindow.SetInstance(output_window)

    application = QtWidgets.QApplication.instance()
    owns_application = application is None
    if application is None:
        application = QtWidgets.QApplication([])
    application.setWindowIcon(create_app_icon())

    window = MainWindow(initial_path=initial_path)
    window.show()

    if owns_application:
        application.exec_()
