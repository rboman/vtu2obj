import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5")

from PyQt5 import QtCore, QtWidgets

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
    assert window.field_combo.findText("cell_stress_von_mises") != -1
    assert window.colormap_combo.count() >= 4
    assert window.n_colors_spin.value() == 256


def test_main_window_restores_persisted_settings(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings.ini"),
        QtCore.QSettings.IniFormat,
    )

    first_window = MainWindow(enable_vtk_view=False, settings=settings)
    first_window.load_file(sample_vtu_path, refresh=False)
    first_window.colormap_combo.setCurrentText("cool_to_warm")
    first_window.n_colors_spin.setValue(32)
    first_window.normals_checkbox.setChecked(False)
    first_window._save_settings()
    first_window.close()

    second_window = MainWindow(enable_vtk_view=False, settings=settings)
    second_window.load_file(sample_vtu_path, refresh=False)

    assert second_window.colormap_combo.currentText() == "cool_to_warm"
    assert second_window.n_colors_spin.value() == 32
    assert second_window.normals_checkbox.isChecked() is False
