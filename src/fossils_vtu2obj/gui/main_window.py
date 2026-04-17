"""Main window for the PyQt5 GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..arrays import list_cell_arrays, list_point_arrays
from ..colormaps import list_colormap_names
from ..export_obj import export_obj_bundle, resolve_obj_bundle_paths
from ..io_vtk import load_unstructured_grid, summarize_unstructured_grid
from ..model import DatasetSummary, ViewDisplayOptions
from ..preview import (
    build_obj_bundle_preview_scene,
    build_volume_preview_scene,
    resolve_dataset_scalar_field,
)
from ..surface import extract_surface, generate_surface_normals
from ..texture import build_palette_texture
from ..uvmap import apply_scalar_uv_map
from .viewport_panel import MeshViewportPanel


class MainWindow(QtWidgets.QMainWindow):
    """GUI for inspecting VTU files and comparing them with exported OBJ bundles."""

    ORGANIZATION_NAME = "fossils"
    APPLICATION_NAME = "fossils-vtu2obj"
    VOLUME_DEFAULTS = ViewDisplayOptions(
        show_edges=True,
        edge_color=(0.78, 0.80, 0.84),
        show_axes=True,
    )
    BUNDLE_DEFAULTS = ViewDisplayOptions(
        show_edges=False,
        edge_color=(0.90, 0.90, 0.92),
        show_axes=True,
    )

    def __init__(
        self,
        initial_path: str | Path | None = None,
        *,
        enable_vtk_view: bool = True,
        settings: QtCore.QSettings | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("fossils-vtu2obj")
        self.resize(1600, 900)

        self.current_file_path: Path | None = None
        self._current_grid = None
        self._current_surface = None
        self._current_summary: DatasetSummary | None = None
        self._current_volume_scene = None
        self._current_bundle = None
        self._current_bundle_scene = None
        self._enable_vtk_view = enable_vtk_view
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
        else:
            last_file = self._settings.value("last_file_path")
            if last_file:
                try:
                    self.load_file(last_file, refresh=True)
                except (FileNotFoundError, TypeError, ValueError, RuntimeError):
                    pass

        last_obj_bundle_path = self._settings.value("last_obj_bundle_path")
        if last_obj_bundle_path:
            try:
                self.load_obj_bundle(last_obj_bundle_path)
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
        controls_layout.addWidget(self.path_edit, 0, 1, 1, 4)

        self.open_obj_button = QtWidgets.QPushButton("Open OBJ Bundle...")
        self.open_obj_button.clicked.connect(self.open_obj_bundle_dialog)
        controls_layout.addWidget(self.open_obj_button, 0, 5)

        self.export_button = QtWidgets.QPushButton("Export OBJ/MTL/PNG...")
        self.export_button.clicked.connect(self.export_current_bundle)
        controls_layout.addWidget(self.export_button, 0, 6)

        self.field_combo = QtWidgets.QComboBox()
        self.field_combo.currentIndexChanged.connect(self._handle_field_changed)
        controls_layout.addWidget(QtWidgets.QLabel("Field"), 1, 0)
        controls_layout.addWidget(self.field_combo, 1, 1)

        self.colormap_combo = QtWidgets.QComboBox()
        for name in list_colormap_names():
            self.colormap_combo.addItem(name)
        self.colormap_combo.currentIndexChanged.connect(self.refresh_preview)
        controls_layout.addWidget(QtWidgets.QLabel("Colormap"), 1, 2)
        controls_layout.addWidget(self.colormap_combo, 1, 3)

        self.n_colors_spin = QtWidgets.QSpinBox()
        self.n_colors_spin.setRange(2, 4096)
        self.n_colors_spin.setValue(256)
        controls_layout.addWidget(QtWidgets.QLabel("Color bins"), 1, 4)
        controls_layout.addWidget(self.n_colors_spin, 1, 5)

        self.normals_checkbox = QtWidgets.QCheckBox("Generate normals")
        self.normals_checkbox.setChecked(True)
        controls_layout.addWidget(self.normals_checkbox, 1, 6)

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

        self.reset_range_button = QtWidgets.QPushButton("Use Data Range")
        self.reset_range_button.clicked.connect(self.reset_current_range)
        controls_layout.addWidget(self.reset_range_button, 2, 4)

        self.refresh_button = QtWidgets.QPushButton("Refresh Volume View")
        self.refresh_button.clicked.connect(self.refresh_preview)
        controls_layout.addWidget(self.refresh_button, 2, 5, 1, 2)

        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.volume_panel = MeshViewportPanel(
            "Volume Mesh",
            default_display_options=self.VOLUME_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=self.splitter,
        )
        self.bundle_panel = MeshViewportPanel(
            "Exported Surface Bundle",
            default_display_options=self.BUNDLE_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=self.splitter,
        )
        self.splitter.addWidget(self.volume_panel)
        self.splitter.addWidget(self.bundle_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter, stretch=1)

        self.statusBar().showMessage("Open a VTU file or an OBJ bundle to begin.")

    def _set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable controls that depend on a loaded VTU dataset."""
        for widget in (
            self.field_combo,
            self.colormap_combo,
            self.n_colors_spin,
            self.normals_checkbox,
            self.vmin_spin,
            self.vmax_spin,
            self.reset_range_button,
            self.refresh_button,
            self.export_button,
        ):
            widget.setEnabled(enabled)

    @staticmethod
    def _setting_to_bool(value: object, default: bool) -> bool:
        """Convert one persisted setting value to a boolean."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() not in {"0", "false", "no", "off"}

    @staticmethod
    def _rgb_to_hex(color: tuple[float, float, float]) -> str:
        """Serialize one normalized RGB triplet as a Qt color string."""
        return QtGui.QColor.fromRgbF(*color).name()

    @staticmethod
    def _hex_to_rgb(
        value: object,
        default: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """Deserialize one persisted Qt color string."""
        color = QtGui.QColor(str(value))
        if not color.isValid():
            return default
        return (color.redF(), color.greenF(), color.blueF())

    def _restore_viewport_settings(
        self,
        prefix: str,
        panel: MeshViewportPanel,
        defaults: ViewDisplayOptions,
    ) -> None:
        """Restore one viewport display-options block from persistent storage."""
        panel.set_display_options(
            ViewDisplayOptions(
                show_edges=self._setting_to_bool(
                    self._settings.value(f"{prefix}_show_edges"),
                    defaults.show_edges,
                ),
                edge_color=self._hex_to_rgb(
                    self._settings.value(f"{prefix}_edge_color"),
                    defaults.edge_color,
                ),
                show_axes=self._setting_to_bool(
                    self._settings.value(f"{prefix}_show_axes"),
                    defaults.show_axes,
                ),
            )
        )

    def _restore_settings(self) -> None:
        """Restore GUI state from persistent storage."""
        colormap = str(self._settings.value("colormap", "rainbow"))
        colormap_index = self.colormap_combo.findText(colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        self.n_colors_spin.setValue(int(self._settings.value("n_colors", 256)))
        self.normals_checkbox.setChecked(
            self._setting_to_bool(self._settings.value("generate_normals"), True)
        )

        self._restore_viewport_settings(
            "volume",
            self.volume_panel,
            self.VOLUME_DEFAULTS,
        )
        self._restore_viewport_settings(
            "bundle",
            self.bundle_panel,
            self.BUNDLE_DEFAULTS,
        )

        splitter_sizes = self._settings.value("splitter_sizes")
        if splitter_sizes:
            try:
                self.splitter.setSizes([int(value) for value in splitter_sizes])
            except (TypeError, ValueError):
                pass

    def _save_viewport_settings(self, prefix: str, panel: MeshViewportPanel) -> None:
        """Persist one viewport display-options block."""
        options = panel.display_options()
        self._settings.setValue(f"{prefix}_show_edges", options.show_edges)
        self._settings.setValue(
            f"{prefix}_edge_color",
            self._rgb_to_hex(options.edge_color),
        )
        self._settings.setValue(f"{prefix}_show_axes", options.show_axes)

    def _save_settings(self) -> None:
        """Persist the current lightweight GUI settings."""
        if self.current_file_path is not None:
            self._settings.setValue("last_file_path", str(self.current_file_path))
            self._settings.setValue("last_field", self._current_field())
        if self._current_bundle is not None:
            self._settings.setValue(
                "last_obj_bundle_path",
                str(self._current_bundle.obj_path),
            )

        self._settings.setValue("colormap", self.colormap_combo.currentText())
        self._settings.setValue("n_colors", self.n_colors_spin.value())
        self._settings.setValue("generate_normals", self.normals_checkbox.isChecked())
        self._settings.setValue("splitter_sizes", self.splitter.sizes())
        self._save_viewport_settings("volume", self.volume_panel)
        self._save_viewport_settings("bundle", self.bundle_panel)
        self._settings.sync()

    def _show_error(self, message: str) -> None:
        """Display an error dialog and mirror the message in the status bar."""
        self.statusBar().showMessage(message)
        QtWidgets.QMessageBox.critical(self, "fossils-vtu2obj", message)

    def _scalar_field_names(self) -> list[str]:
        """Return the scalar field names available on the current dataset."""
        if self._current_summary is None:
            return []

        scalar_fields = [
            array.name
            for array in list_point_arrays(self._current_summary)
            if array.is_scalar
        ]
        scalar_fields.extend(
            array.name
            for array in list_cell_arrays(self._current_summary)
            if array.is_scalar
        )
        return scalar_fields

    def _current_field(self) -> str:
        """Return the currently selected field name."""
        return self.field_combo.currentText()

    def _current_mapping_kwargs(self) -> dict[str, object]:
        """Collect the current scalar-mapping settings from the widgets."""
        return {
            "colormap": self.colormap_combo.currentText(),
            "vmin": self.vmin_spin.value(),
            "vmax": self.vmax_spin.value(),
            "n_colors": self.n_colors_spin.value(),
        }

    def _current_field_range(self) -> tuple[float, float]:
        """Return the range of the selected dataset scalar field."""
        if self._current_grid is None:
            raise RuntimeError("No VTU file is currently loaded.")

        _, array = resolve_dataset_scalar_field(
            self._current_grid,
            self._current_field(),
        )
        return tuple(float(value) for value in array.GetRange())

    def open_file_dialog(self) -> None:
        """Prompt the user for a VTU file and load it into the GUI."""
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open VTU file",
            "",
            "VTU Files (*.vtu);;All Files (*)",
        )
        if not file_name:
            return
        try:
            self.load_file(file_name, refresh=True)
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def open_obj_bundle_dialog(self) -> None:
        """Prompt the user for an OBJ bundle and load it into the right viewport."""
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open OBJ bundle",
            "",
            "OBJ Files (*.obj);;All Files (*)",
        )
        if not file_name:
            return
        try:
            self.load_obj_bundle(file_name)
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def load_file(self, path: str | Path, *, refresh: bool = True) -> None:
        """Load a VTU file, populate controls, and optionally refresh the view."""
        input_path = Path(path).expanduser()
        self.current_file_path = input_path.resolve(strict=False)
        self._current_grid = load_unstructured_grid(self.current_file_path)
        self._current_summary = summarize_unstructured_grid(
            self._current_grid,
            self.current_file_path,
        )
        self._current_surface = extract_surface(self._current_grid, triangulate=True)

        scalar_fields = self._scalar_field_names()
        if not scalar_fields:
            raise ValueError(
                "The selected VTU file does not contain scalar point or cell data."
            )

        self.path_edit.setText(str(self.current_file_path))
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(scalar_fields)
        previous_field = str(self._settings.value("last_field", ""))
        field_index = self.field_combo.findText(previous_field)
        if field_index >= 0:
            self.field_combo.setCurrentIndex(field_index)
        elif self.field_combo.count() > 0:
            self.field_combo.setCurrentIndex(0)
        self.field_combo.blockSignals(False)

        self._set_controls_enabled(True)
        self.reset_current_range()
        self.statusBar().showMessage(f"Loaded {self.current_file_path.name}")
        self._save_settings()

        if refresh:
            self.refresh_preview()

    def load_obj_bundle(self, path: str | Path) -> None:
        """Load an OBJ/MTL/PNG bundle into the right viewport."""
        bundle = resolve_obj_bundle_paths(path)
        scene = build_obj_bundle_preview_scene(bundle)
        self._current_bundle = bundle
        self._current_bundle_scene = scene
        self.bundle_panel.set_scene(scene)
        self.statusBar().showMessage(f"Loaded OBJ bundle {bundle.obj_path.name}")
        self._save_settings()

    def _handle_field_changed(self) -> None:
        """Synchronize the range with the selected field and update the volume view."""
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
        """Rebuild the left volume scene and display it in the GUI."""
        if self._current_grid is None or self.field_combo.count() == 0:
            return

        try:
            scene = build_volume_preview_scene(
                self._current_grid,
                self._current_field(),
                source_path=self.current_file_path,
                **self._current_mapping_kwargs(),
            )
            self._current_volume_scene = scene
            self.volume_panel.set_scene(scene)
            self.statusBar().showMessage(
                f"Volume view updated for field '{self._current_field()}'."
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
            self.load_obj_bundle(bundle.obj_path)
        except (TypeError, ValueError, RuntimeError, FileNotFoundError) as exc:
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
