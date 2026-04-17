import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5")

from PyQt5 import QtCore, QtWidgets

from fossils_vtu2obj.defaults import DEFAULT_N_COLORS
from fossils_vtu2obj.gui.main_window import MainWindow
from fossils_vtu2obj.model import ViewDisplayOptions


@pytest.fixture(scope="module")
def qapplication() -> QtWidgets.QApplication:
    application = QtWidgets.QApplication.instance()
    if application is None:
        application = QtWidgets.QApplication([])
    return application


def test_main_window_loads_scalar_fields(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)

    window.load_file(sample_vtu_path, refresh=False)

    assert window.current_file_path == sample_vtu_path.resolve(strict=False)
    assert window.field_combo.count() >= 1
    assert window.field_combo.findText("stress_von_mises") != -1
    assert window.field_combo.findText("cell_stress_von_mises") != -1
    assert window.field_combo.currentText() == "stress_von_mises"
    assert window.colormap_combo.count() >= 10
    assert window.n_colors_spin.value() == DEFAULT_N_COLORS
    assert window.volume_panel.title_label.text() == "Volume Mesh"
    assert window.bundle_panel.title_label.text() == "Exported Surface Bundle"
    assert window.volume_panel.info_text_edit.toPlainText() == "No mesh loaded."
    assert window.volume_panel.show_edges_checkbox.isChecked() is False
    assert window.volume_panel.show_axes_checkbox.isChecked() is True
    assert window.bundle_panel.show_edges_checkbox.isChecked() is False
    assert window.bundle_panel.show_axes_checkbox.isChecked() is True
    assert window.open_button.toolTip()
    assert window.export_button.toolTip()
    assert window.field_combo.toolTip()
    assert window.open_button.icon().isNull() is False
    assert window.export_button.icon().isNull() is False
    assert window.windowIcon().isNull() is False
    assert hasattr(window, "settings_menu")
    assert hasattr(window, "reset_defaults_action")


def test_main_window_restores_persisted_settings(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    sample_obj_bundle,
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
    first_window.main_splitter.setSizes([420, 780])
    first_window.volume_panel.set_display_options(
        ViewDisplayOptions(
            show_edges=False,
            edge_color=(0.2, 0.4, 0.6),
            show_axes=True,
        )
    )
    first_window.bundle_panel.set_display_options(
        ViewDisplayOptions(
            show_edges=True,
            edge_color=(0.7, 0.3, 0.2),
            show_axes=False,
        )
    )
    first_window.load_obj_bundle(sample_obj_bundle.obj_path)
    first_window._save_settings()
    first_window.close()

    second_window = MainWindow(enable_vtk_view=False, settings=settings)
    second_window.load_file(sample_vtu_path, refresh=False)

    assert second_window.colormap_combo.currentText() == "cool_to_warm"
    assert second_window.n_colors_spin.value() == 32
    assert second_window.normals_checkbox.isChecked() is False
    assert second_window.vtu_path_edit.text().endswith("sample.vtu")
    assert second_window.volume_panel.show_edges_checkbox.isChecked() is False
    assert second_window.bundle_panel.show_edges_checkbox.isChecked() is True
    assert second_window.bundle_panel.show_axes_checkbox.isChecked() is False
    assert second_window._current_bundle is not None
    assert second_window._current_bundle.obj_path == sample_obj_bundle.obj_path
    assert second_window.obj_path_edit.text().endswith(".obj")


def test_main_window_can_load_obj_bundle(
    qapplication: QtWidgets.QApplication,
    sample_obj_bundle,
) -> None:
    _ = qapplication
    window = MainWindow(enable_vtk_view=False)

    window.load_obj_bundle(sample_obj_bundle.obj_path)

    assert window._current_bundle is not None
    assert window._current_bundle.obj_path == sample_obj_bundle.obj_path
    assert window.obj_path_edit.text().endswith(".obj")
    info_text = window.bundle_panel.info_text_edit.toPlainText()
    assert "Texture: present" in info_text
    assert "UVs: present" in info_text


def test_main_window_export_reloads_bundle_panel(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = qapplication
    window = MainWindow(enable_vtk_view=False)
    window.load_file(sample_vtu_path, refresh=False)

    export_path = tmp_path / "exported" / "model.obj"
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: (str(export_path), "OBJ Files (*.obj)"),
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args, **kwargs: 0)

    window.export_current_bundle()

    assert export_path.is_file()
    assert window._current_bundle is not None
    assert window._current_bundle.obj_path == export_path
    assert "Texture: present" in window.bundle_panel.info_text_edit.toPlainText()


def test_reset_gui_defaults_clears_persisted_settings(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)
    window.load_file(sample_vtu_path, refresh=False)
    window.colormap_combo.setCurrentText("cool_to_warm")
    window.n_colors_spin.setValue(32)
    window.normals_checkbox.setChecked(False)
    window.volume_panel.set_display_options(
        ViewDisplayOptions(
            show_edges=True,
            edge_color=(0.3, 0.2, 0.1),
            show_axes=False,
        )
    )
    window._save_settings()

    window.reset_gui_defaults()

    assert window.colormap_combo.currentText() == "rainbow"
    assert window.n_colors_spin.value() == DEFAULT_N_COLORS
    assert window.normals_checkbox.isChecked() is True
    assert window.field_combo.currentText() == "stress_von_mises"
    assert window.volume_panel.show_edges_checkbox.isChecked() is False
    assert window.volume_panel.show_axes_checkbox.isChecked() is True
    assert window.bundle_panel.show_edges_checkbox.isChecked() is False
    assert window.bundle_panel.show_axes_checkbox.isChecked() is True
    assert settings.value("colormap") == "rainbow"


def test_main_window_exposes_help_and_credits_actions(
    qapplication: QtWidgets.QApplication,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)

    assert window.about_action.text() == "About fossils-vtu2obj"
    assert window.github_action.text() == "Open GitHub Repository"
    assert window.credits_action.text() == "Show Credits"
    assert window.about_action.toolTip()
    assert window.github_action.toolTip()
    assert window.credits_action.toolTip()
    assert window.reset_defaults_action.text() == "Reset GUI Defaults"


def test_main_window_prefers_stress_von_mises_on_doli(
    qapplication: QtWidgets.QApplication,
    doli_vtu_path: Path,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings_doli.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)

    window.load_file(doli_vtu_path, refresh=False)

    assert window.field_combo.currentText() == "stress_von_mises"
