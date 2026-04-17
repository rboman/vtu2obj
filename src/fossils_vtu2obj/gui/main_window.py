"""Main window for the minimal PyQt5 GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..arrays import list_cell_arrays, list_point_arrays
from ..colormaps import list_colormap_names
from ..export_obj import export_obj_bundle
from ..io_vtk import inspect_dataset, load_unstructured_grid
from ..preview import (
    PreviewScene,
    build_scalar_preview_scene,
    build_textured_preview_scene,
)
from ..surface import extract_surface, generate_surface_normals
from ..texture import build_palette_texture
from ..uvmap import apply_scalar_uv_map, ensure_point_scalar_field
from .vtk_view import VtkView


class MainWindow(QtWidgets.QMainWindow):
    """Minimal GUI for inspecting, previewing, and exporting VTU files."""

    ORGANIZATION_NAME = "fossils"
    APPLICATION_NAME = "fossils-vtu2obj"

    def __init__(
        self,
        initial_path: str | Path | None = None,
        *,
        enable_vtk_view: bool = True,
        settings: QtCore.QSettings | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("fossils-vtu2obj")
        self.resize(1400, 900)

        self.current_file_path: Path | None = None
        self._current_grid = None
        self._current_surface = None
        self._last_scene: PreviewScene | None = None
        self._enable_vtk_view = enable_vtk_view
        self.vtk_view: VtkView | None = None
        self._settings = settings or QtCore.QSettings(
            QtCore.QSettings.IniFormat,
            QtCore.QSettings.UserScope,
            self.ORGANIZATION_NAME,
            self.APPLICATION_NAME,
        )

        self._build_ui()
        self._restore_settings()
        self._set_controls_enabled(False)

        if initial_path is not None:
            self.load_file(initial_path, refresh=True)
        elif self._settings.value("last_file_path"):
            try:
                self.load_file(self._settings.value("last_file_path"), refresh=True)
            except (FileNotFoundError, TypeError, ValueError, RuntimeError):
                pass

    def _build_ui(self) -> None:
        """Create the window layout and interactive controls."""
        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QtWidgets.QVBoxLayout(central_widget)
        controls_layout = QtWidgets.QGridLayout()
        layout.addLayout(controls_layout)

        self.open_button = QtWidgets.QPushButton("Open VTU...")
        self.open_button.clicked.connect(self.open_file_dialog)
        controls_layout.addWidget(self.open_button, 0, 0)

        self.path_edit = QtWidgets.QLineEdit()
        self.path_edit.setReadOnly(True)
        controls_layout.addWidget(self.path_edit, 0, 1, 1, 5)

        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItem("Scalar preview", "scalar")
        self.mode_combo.addItem("Textured preview", "textured")
        self.mode_combo.currentIndexChanged.connect(self.refresh_preview)
        controls_layout.addWidget(QtWidgets.QLabel("Preview mode"), 1, 0)
        controls_layout.addWidget(self.mode_combo, 1, 1)

        self.field_combo = QtWidgets.QComboBox()
        self.field_combo.currentIndexChanged.connect(self._handle_field_changed)
        controls_layout.addWidget(QtWidgets.QLabel("Field"), 1, 2)
        controls_layout.addWidget(self.field_combo, 1, 3)

        self.colormap_combo = QtWidgets.QComboBox()
        for name in list_colormap_names():
            self.colormap_combo.addItem(name)
        self.colormap_combo.currentIndexChanged.connect(self.refresh_preview)
        controls_layout.addWidget(QtWidgets.QLabel("Colormap"), 1, 4)
        controls_layout.addWidget(self.colormap_combo, 1, 5)

        self.vmin_spin = QtWidgets.QDoubleSpinBox()
        self.vmax_spin = QtWidgets.QDoubleSpinBox()
        for spin_box in (self.vmin_spin, self.vmax_spin):
            spin_box.setDecimals(6)
            spin_box.setRange(-1.0e30, 1.0e30)
            spin_box.setSingleStep(0.1)
        controls_layout.addWidget(QtWidgets.QLabel("vmin"), 2, 0)
        controls_layout.addWidget(self.vmin_spin, 2, 1)
        controls_layout.addWidget(QtWidgets.QLabel("vmax"), 2, 2)
        controls_layout.addWidget(self.vmax_spin, 2, 3)

        self.n_colors_spin = QtWidgets.QSpinBox()
        self.n_colors_spin.setRange(2, 4096)
        self.n_colors_spin.setValue(256)
        controls_layout.addWidget(QtWidgets.QLabel("Color bins"), 2, 4)
        controls_layout.addWidget(self.n_colors_spin, 2, 5)

        self.normals_checkbox = QtWidgets.QCheckBox("Generate normals")
        self.normals_checkbox.setChecked(True)
        controls_layout.addWidget(self.normals_checkbox, 3, 4)

        self.reset_range_button = QtWidgets.QPushButton("Use Data Range")
        self.reset_range_button.clicked.connect(self.reset_current_range)
        controls_layout.addWidget(self.reset_range_button, 3, 0)

        self.refresh_button = QtWidgets.QPushButton("Refresh Preview")
        self.refresh_button.clicked.connect(self.refresh_preview)
        controls_layout.addWidget(self.refresh_button, 3, 1)

        self.export_button = QtWidgets.QPushButton("Export OBJ/MTL/PNG...")
        self.export_button.clicked.connect(self.export_current_bundle)
        controls_layout.addWidget(self.export_button, 3, 5)

        if self._enable_vtk_view:
            self.vtk_view = VtkView(self)
            layout.addWidget(self.vtk_view, stretch=1)
        else:
            placeholder = QtWidgets.QLabel(
                "VTK preview widget disabled for this session."
            )
            placeholder.setAlignment(QtCore.Qt.AlignCenter)
            layout.addWidget(placeholder, stretch=1)

        self.statusBar().showMessage("Open a VTU file to begin.")

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable controls that depend on a loaded dataset."""
        for widget in (
            self.mode_combo,
            self.field_combo,
            self.colormap_combo,
            self.vmin_spin,
            self.vmax_spin,
            self.n_colors_spin,
            self.reset_range_button,
            self.refresh_button,
            self.export_button,
        ):
            widget.setEnabled(enabled)

    def _restore_settings(self) -> None:
        """Restore a few lightweight GUI settings from persistent storage."""
        preview_mode = str(self._settings.value("preview_mode", "scalar"))
        mode_index = self.mode_combo.findData(preview_mode)
        if mode_index >= 0:
            self.mode_combo.setCurrentIndex(mode_index)

        colormap = str(self._settings.value("colormap", "rainbow"))
        colormap_index = self.colormap_combo.findText(colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        self.n_colors_spin.setValue(int(self._settings.value("n_colors", 256)))
        self.normals_checkbox.setChecked(
            str(self._settings.value("generate_normals", "true")).lower() != "false"
        )

    def _save_settings(self) -> None:
        """Persist the current lightweight GUI settings."""
        if self.current_file_path is not None:
            self._settings.setValue("last_file_path", str(self.current_file_path))
            self._settings.setValue("last_field", self._current_field())
        self._settings.setValue("preview_mode", self._current_preview_mode())
        self._settings.setValue("colormap", self.colormap_combo.currentText())
        self._settings.setValue("n_colors", self.n_colors_spin.value())
        self._settings.setValue("generate_normals", self.normals_checkbox.isChecked())
        self._settings.sync()

    def _show_error(self, message: str) -> None:
        """Display an error dialog and mirror the message in the status bar."""
        self.statusBar().showMessage(message)
        QtWidgets.QMessageBox.critical(self, "fossils-vtu2obj", message)

    def _scalar_field_names(self) -> list[str]:
        """Return the scalar field names available on the dataset."""
        if self.current_file_path is None:
            return []
        summary = inspect_dataset(self.current_file_path)
        scalar_fields = [
            array.name for array in list_point_arrays(summary) if array.is_scalar
        ]
        scalar_fields.extend(
            array.name for array in list_cell_arrays(summary) if array.is_scalar
        )
        return scalar_fields

    def _current_field(self) -> str:
        """Return the currently selected field name."""
        return self.field_combo.currentText()

    def _current_preview_mode(self) -> str:
        """Return the current preview mode identifier."""
        return str(self.mode_combo.currentData())

    def _current_mapping_kwargs(self) -> dict[str, object]:
        """Collect the current scalar-mapping settings from the widgets."""
        return {
            "colormap": self.colormap_combo.currentText(),
            "vmin": self.vmin_spin.value(),
            "vmax": self.vmax_spin.value(),
            "n_colors": self.n_colors_spin.value(),
        }

    def _current_field_range(self) -> tuple[float, float]:
        """Return the range of the selected surface scalar field."""
        if self._current_surface is None:
            raise RuntimeError("No surface is loaded.")

        _, array = ensure_point_scalar_field(
            self._current_surface,
            self._current_field(),
        )
        return tuple(float(value) for value in array.GetRange())

    def _build_current_scene(self) -> PreviewScene:
        """Create the preview scene that matches the current controls."""
        if self._current_surface is None:
            raise RuntimeError("No VTU file is currently loaded.")

        mapping_kwargs = self._current_mapping_kwargs()
        field_name = self._current_field()
        if self._current_preview_mode() == "textured":
            return build_textured_preview_scene(
                self._current_surface,
                field_name,
                **mapping_kwargs,
            )

        return build_scalar_preview_scene(
            self._current_surface,
            field_name,
            **mapping_kwargs,
        )

    def open_file_dialog(self) -> None:
        """Prompt the user for a VTU file and load it into the GUI."""
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open VTU file",
            "",
            "VTU Files (*.vtu);;All Files (*)",
        )
        if file_name:
            try:
                self.load_file(file_name, refresh=True)
            except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
                self._show_error(str(exc))

    def load_file(self, path: str | Path, *, refresh: bool = True) -> None:
        """Load a VTU file, populate controls, and optionally refresh the preview."""
        input_path = Path(path).expanduser()
        self.current_file_path = input_path.resolve(strict=False)
        self._current_grid = load_unstructured_grid(self.current_file_path)
        self._current_surface = extract_surface(self._current_grid, triangulate=True)

        scalar_fields = self._scalar_field_names()
        if not scalar_fields:
            raise ValueError(
                "The selected VTU file does not contain scalar point data."
            )

        self.path_edit.setText(str(self.current_file_path))
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(scalar_fields)
        previous_field = str(self._settings.value("last_field", ""))
        field_index = self.field_combo.findText(previous_field)
        if field_index >= 0:
            self.field_combo.setCurrentIndex(field_index)
        self.field_combo.blockSignals(False)

        self._set_controls_enabled(True)
        self.reset_current_range()
        self.statusBar().showMessage(f"Loaded {self.current_file_path.name}")
        self._save_settings()

        if refresh:
            self.refresh_preview()

    def _handle_field_changed(self) -> None:
        """Synchronize the range with the selected field and update the preview."""
        if self.field_combo.count() == 0:
            return
        try:
            self.reset_current_range()
            self.refresh_preview()
        except (TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def reset_current_range(self) -> None:
        """Reset the min/max widgets to the selected field data range."""
        vmin, vmax = self._current_field_range()
        self.vmin_spin.setValue(vmin)
        self.vmax_spin.setValue(vmax)

    def refresh_preview(self) -> None:
        """Rebuild the preview and display it in the embedded VTK widget."""
        if self._current_surface is None or self.field_combo.count() == 0:
            return

        try:
            scene = self._build_current_scene()
            self._last_scene = scene
            if self.vtk_view is not None:
                self.vtk_view.set_scene(scene)
                self.statusBar().showMessage(
                    f"Preview updated for field '{self._current_field()}'."
                )
            else:
                self.statusBar().showMessage(
                    f"Preview scene prepared for field '{self._current_field()}'."
                )
            self._save_settings()
        except (TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def export_current_bundle(self) -> None:
        """Export the current conversion settings to OBJ, MTL, and PNG."""
        if self._current_surface is None or self.current_file_path is None:
            raise RuntimeError("No VTU file is currently loaded.")

        suggested_name = self.current_file_path.with_suffix(".obj").name
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export OBJ bundle",
            suggested_name,
            "OBJ Files (*.obj);;All Files (*)",
        )
        if not file_name:
            return

        try:
            output_prefix = Path(file_name).with_suffix("")
            mapping_kwargs = self._current_mapping_kwargs()
            textured_surface = apply_scalar_uv_map(
                self._current_surface,
                self._current_field(),
                vmin=float(mapping_kwargs["vmin"]),
                vmax=float(mapping_kwargs["vmax"]),
                n_colors=int(mapping_kwargs["n_colors"]),
            )
            texture_image = build_palette_texture(
                str(mapping_kwargs["colormap"]),
                n_colors=int(mapping_kwargs["n_colors"]),
            )
            if self.normals_checkbox.isChecked():
                textured_surface = generate_surface_normals(textured_surface)
            bundle = export_obj_bundle(textured_surface, output_prefix, texture_image)
        except (TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))
            return

        self.statusBar().showMessage(f"Exported bundle to {bundle.obj_path.parent}")
        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            "\n".join(
                [
                    f"OBJ: {bundle.obj_path}",
                    f"MTL: {bundle.mtl_path}",
                    f"PNG: {bundle.texture_path}",
                ]
            ),
        )
        self._save_settings()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Persist settings when the window closes."""
        self._save_settings()
        super().closeEvent(event)
