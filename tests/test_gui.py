import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt5")

from PyQt5 import QtCore, QtWidgets

import fossils_vtu2obj.gui.main_window as main_window_module
from fossils_vtu2obj.defaults import DEFAULT_N_COLORS
from fossils_vtu2obj.gui.main_window import (
    MainWindow,
    _format_file_size,
    _OperationCancelled,
    _OperationProgressDialog,
)
from fossils_vtu2obj.model import ViewDisplayOptions
from fossils_vtu2obj.preview import PreviewScene


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
    assert window.settings_menu.title() == "&Settings"
    assert hasattr(window, "reset_defaults_action")
    assert not hasattr(window, "reset_defaults_button")


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
    assert window.clear_views_action.text() == "Clear Views"
    assert window.recent_vtu_menu.title() == "Recent &VTU Files"
    assert window.recent_obj_menu.title() == "Recent &OBJ Bundles"


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


def test_main_window_remembers_last_dialog_directories(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    sample_obj_bundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings_dialogs.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)
    window.load_file(sample_vtu_path, refresh=False)

    chosen_vtu = tmp_path / "imports" / "mesh.vtu"
    chosen_obj = tmp_path / "bundles" / "model.obj"
    chosen_export = tmp_path / "exports" / "out.obj"
    chosen_vtu.parent.mkdir(parents=True, exist_ok=True)
    chosen_obj.parent.mkdir(parents=True, exist_ok=True)
    chosen_export.parent.mkdir(parents=True, exist_ok=True)

    captured_vtu_dirs: list[str] = []
    captured_obj_dirs: list[str] = []
    captured_export_paths: list[str] = []

    def fake_get_open_file_name(parent, title, directory, file_filter):
        if title == "Open VTU file":
            captured_vtu_dirs.append(directory)
            return str(chosen_vtu), file_filter
        captured_obj_dirs.append(directory)
        return str(chosen_obj), file_filter

    def fake_get_save_file_name(parent, title, directory, file_filter):
        captured_export_paths.append(directory)
        return str(chosen_export), file_filter

    monkeypatch.setattr(
        window,
        "load_file",
        lambda path, **kwargs: window._remember_directory("last_vtu_directory", path),
    )
    monkeypatch.setattr(
        window,
        "load_obj_bundle",
        lambda path, **kwargs: window._remember_directory(
            "last_obj_bundle_directory",
            path,
        ),
    )
    window._current_bundle = sample_obj_bundle
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        fake_get_open_file_name,
    )
    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getSaveFileName",
        fake_get_save_file_name,
    )
    monkeypatch.setattr(QtWidgets.QMessageBox, "information", lambda *args, **kwargs: 0)

    window.open_file_dialog()
    window.open_obj_bundle_dialog()
    window.export_current_bundle()

    assert settings.value("last_vtu_directory") == str(
        chosen_vtu.parent.resolve(strict=False)
    )
    assert settings.value("last_obj_bundle_directory") == str(
        chosen_export.parent.resolve(strict=False)
    )
    assert settings.value("last_export_directory") == str(
        chosen_export.parent.resolve(strict=False)
    )
    assert captured_vtu_dirs == [
        str(sample_vtu_path.parent.resolve(strict=False))
    ]
    assert captured_obj_dirs == [
        str(sample_obj_bundle.obj_path.parent.resolve(strict=False))
    ]
    assert captured_export_paths == [
        str(
            (
                sample_vtu_path.parent / sample_vtu_path.with_suffix(".obj").name
            ).resolve(strict=False)
        )
    ]


def test_refresh_preview_preserves_camera_state(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = qapplication
    window = MainWindow(enable_vtk_view=False)
    window.load_file(sample_vtu_path, refresh=False, show_progress=False)

    preserved_state = {"position": (1.0, 2.0, 3.0)}
    captured: dict[str, object] = {}
    fake_scene = PreviewScene(
        renderer=object(),  # type: ignore[arg-type]
        actor=object(),  # type: ignore[arg-type]
        surface=object(),  # type: ignore[arg-type]
    )

    monkeypatch.setattr(window.volume_panel, "camera_state", lambda: preserved_state)
    monkeypatch.setattr(
        main_window_module,
        "build_volume_preview_scene",
        lambda *args, **kwargs: fake_scene,
    )
    monkeypatch.setattr(
        window.volume_panel,
        "set_scene",
        lambda scene, preserve_camera_state=None: captured.update(
            scene=scene,
            preserve_camera_state=preserve_camera_state,
        ),
    )

    window.refresh_preview()

    assert captured["scene"] is fake_scene
    assert captured["preserve_camera_state"] == preserved_state


def test_load_file_uses_progress_dialog_for_long_operation(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = qapplication
    window = MainWindow(enable_vtk_view=False)
    progress_calls: list[tuple[str, int]] = []

    class FakeProgressDialog:
        def __init__(self) -> None:
            self._maximum = 4

        def maximum(self) -> int:
            return self._maximum

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        window,
        "_create_progress_dialog",
        lambda label_text, maximum, **kwargs: (
            progress_calls.append((label_text, maximum)) or FakeProgressDialog()
        ),
    )
    monkeypatch.setattr(
        window,
        "_update_progress",
        lambda dialog, value, label_text: None,
    )

    window.load_file(sample_vtu_path, refresh=True, show_progress=True)

    assert progress_calls == [("Loading VTU file...", 4)]


def test_progress_dialog_displays_file_metadata(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
) -> None:
    _ = qapplication
    parent = QtWidgets.QWidget()
    dialog = _OperationProgressDialog(
        parent,
        title="Test Progress",
        label_text="Loading VTU file...",
        maximum=4,
        subject_path=sample_vtu_path,
    )

    assert dialog.width() >= 700
    assert dialog.file_name_value.text() == sample_vtu_path.name
    assert dialog.file_path_value.text().endswith(sample_vtu_path.name)
    assert dialog.file_size_value.text() == _format_file_size(
        sample_vtu_path.stat().st_size
    )


def test_update_progress_raises_when_cancel_requested(
    qapplication: QtWidgets.QApplication,
) -> None:
    _ = qapplication
    parent = QtWidgets.QWidget()
    dialog = _OperationProgressDialog(
        parent,
        title="Test Progress",
        label_text="Working...",
        maximum=4,
        subject_path=None,
    )

    dialog._request_cancel()

    with pytest.raises(_OperationCancelled):
        MainWindow._update_progress(dialog, 1, "Still working...")


def test_clear_views_unloads_current_meshes(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    sample_obj_bundle,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings_clear.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)
    window.load_file(sample_vtu_path, refresh=False, show_progress=False)
    window.load_obj_bundle(sample_obj_bundle.obj_path, show_progress=False)
    window._save_settings()

    window.clear_views()

    assert window.current_file_path is None
    assert window._current_grid is None
    assert window._current_surface is None
    assert window._current_summary is None
    assert window._current_bundle is None
    assert window._current_volume_scene is None
    assert window._current_bundle_scene is None
    assert window.vtu_path_edit.text() == ""
    assert window.obj_path_edit.text() == ""
    assert window.field_combo.count() == 0
    assert window.volume_panel.info_text_edit.toPlainText() == "No mesh loaded."
    assert window.bundle_panel.info_text_edit.toPlainText() == "No mesh loaded."
    assert window.export_button.isEnabled() is False
    assert settings.value("last_file_path") is None
    assert settings.value("last_obj_bundle_path") is None


def test_recent_files_lists_are_persisted_and_restored(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    sample_obj_bundle,
    tmp_path: Path,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings_recent.ini"),
        QtCore.QSettings.IniFormat,
    )
    first_window = MainWindow(enable_vtk_view=False, settings=settings)
    first_window.load_file(sample_vtu_path, refresh=False, show_progress=False)
    first_window.load_obj_bundle(sample_obj_bundle.obj_path, show_progress=False)
    first_window.close()

    second_window = MainWindow(enable_vtk_view=False, settings=settings)

    assert str(sample_vtu_path.resolve(strict=False)) in second_window._recent_files(
        "recent_vtu_files"
    )
    assert str(
        sample_obj_bundle.obj_path.resolve(strict=False)
    ) in second_window._recent_files("recent_obj_files")
    assert second_window.recent_vtu_menu.actions()
    assert second_window.recent_obj_menu.actions()


def test_recent_file_menu_action_opens_selected_file(
    qapplication: QtWidgets.QApplication,
    sample_vtu_path: Path,
    sample_obj_bundle,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ = qapplication
    settings = QtCore.QSettings(
        str(tmp_path / "gui_settings_recent_menu.ini"),
        QtCore.QSettings.IniFormat,
    )
    window = MainWindow(enable_vtk_view=False, settings=settings)
    window._set_recent_files(
        "recent_vtu_files",
        [str(sample_vtu_path.resolve(strict=False))],
    )
    window._set_recent_files(
        "recent_obj_files",
        [str(sample_obj_bundle.obj_path.resolve(strict=False))],
    )
    window._refresh_recent_file_menus()

    captured: dict[str, str] = {}
    monkeypatch.setattr(
        window,
        "start_load_file_async",
        lambda path, **kwargs: captured.update(vtu=str(path)),
    )
    monkeypatch.setattr(
        window,
        "start_load_obj_bundle_async",
        lambda path, **kwargs: captured.update(obj=str(path)),
    )

    window.recent_vtu_menu.actions()[0].trigger()
    window.recent_obj_menu.actions()[0].trigger()

    assert captured["vtu"] == str(sample_vtu_path.resolve(strict=False))
    assert captured["obj"] == str(sample_obj_bundle.obj_path.resolve(strict=False))
