import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5")

from PyQt5 import QtWidgets

from fossils_vtu2obj.gui.main_window import MainWindow


@pytest.fixture(scope="module")
def qapplication() -> QtWidgets.QApplication:
    application = QtWidgets.QApplication.instance()
    if application is None:
        application = QtWidgets.QApplication([])
    return application


def test_main_window_loads_scalar_fields(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
) -> None:
    _ = qapplication
    window = MainWindow(enable_vtk_view=False)

    window.load_file(sample_vtu_path, refresh=False)

    assert window.current_file_path == sample_vtu_path.resolve(strict=False)
    assert window.field_combo.count() >= 1
    assert window.field_combo.findText("stress_von_mises") != -1
    assert window.colormap_combo.count() >= 4
    assert window.n_colors_spin.value() == 256
