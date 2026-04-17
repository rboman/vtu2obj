"""Main window for the PyQt5 GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

from ..arrays import (
    preferred_scalar_field_name,
    scalar_field_names,
)
from ..colormaps import list_colormap_names
from ..defaults import (
    DEFAULT_BUNDLE_EDGE_COLOR,
    DEFAULT_BUNDLE_SHOW_AXES,
    DEFAULT_BUNDLE_SHOW_EDGES,
    DEFAULT_COLORMAP_NAME,
    DEFAULT_GITHUB_URL,
    DEFAULT_GUI_SPLITTER_SIZES,
    DEFAULT_N_COLORS,
    DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
    DEFAULT_SPINBOX_DECIMALS,
    DEFAULT_SPINBOX_MAX,
    DEFAULT_SPINBOX_MIN,
    DEFAULT_SPINBOX_STEP,
    DEFAULT_VOLUME_EDGE_COLOR,
    DEFAULT_VOLUME_SHOW_AXES,
    DEFAULT_VOLUME_SHOW_EDGES,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_TITLE,
    DEFAULT_WINDOW_WIDTH,
)
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
from .icons import create_app_icon, standard_icon
from .viewport_panel import MeshViewportPanel


class MainWindow(QtWidgets.QMainWindow):
    """GUI for inspecting VTU files and comparing them with exported OBJ bundles."""

    ORGANIZATION_NAME = "fossils"
    APPLICATION_NAME = "fossils-vtu2obj"
    GITHUB_URL = DEFAULT_GITHUB_URL
    VOLUME_DEFAULTS = ViewDisplayOptions(
        show_edges=DEFAULT_VOLUME_SHOW_EDGES,
        edge_color=DEFAULT_VOLUME_EDGE_COLOR,
        show_axes=DEFAULT_VOLUME_SHOW_AXES,
    )
    BUNDLE_DEFAULTS = ViewDisplayOptions(
        show_edges=DEFAULT_BUNDLE_SHOW_EDGES,
        edge_color=DEFAULT_BUNDLE_EDGE_COLOR,
        show_axes=DEFAULT_BUNDLE_SHOW_AXES,
    )

    def __init__(
        self,
        initial_path: str | Path | None = None,
        *,
        enable_vtk_view: bool = True,
        settings: QtCore.QSettings | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle(DEFAULT_WINDOW_TITLE)
        self.setWindowIcon(create_app_icon())
        self.resize(DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT)

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
        self._apply_default_gui_settings()
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
        self._build_actions()
        self._build_menus()

        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QtWidgets.QVBoxLayout(central_widget)

        self.main_splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal, self)
        self.main_splitter.setToolTip(
            "Resize the left VTU workflow panel and the right OBJ comparison "
            "panel independently."
        )
        root_layout.addWidget(self.main_splitter, stretch=1)

        left_container = QtWidgets.QWidget(self.main_splitter)
        left_layout = QtWidgets.QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self._build_vtu_controls_group())
        self.volume_panel = MeshViewportPanel(
            "Volume Mesh",
            default_display_options=self.VOLUME_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=left_container,
        )
        left_layout.addWidget(self.volume_panel, stretch=1)

        right_container = QtWidgets.QWidget(self.main_splitter)
        right_layout = QtWidgets.QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._build_obj_controls_group())
        self.bundle_panel = MeshViewportPanel(
            "Exported Surface Bundle",
            default_display_options=self.BUNDLE_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=right_container,
        )
        right_layout.addWidget(self.bundle_panel, stretch=1)

        self.main_splitter.addWidget(left_container)
        self.main_splitter.addWidget(right_container)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 1)

        self.statusBar().showMessage("Open a VTU file or an OBJ bundle to begin.")

    def _build_actions(self) -> None:
        """Create shared actions used by menus and buttons."""
        self.open_vtu_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_DialogOpenButton),
            "Open VTU...",
            self,
        )
        self.open_vtu_action.setToolTip(
            "Open a VTU results file and populate the conversion controls."
        )
        self.open_vtu_action.setStatusTip(self.open_vtu_action.toolTip())
        self.open_vtu_action.triggered.connect(self.open_file_dialog)

        self.open_obj_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_DirOpenIcon),
            "Open OBJ Bundle...",
            self,
        )
        self.open_obj_action.setToolTip(
            "Open an existing OBJ/MTL/PNG bundle on disk and display it in the "
            "right-hand viewport."
        )
        self.open_obj_action.setStatusTip(self.open_obj_action.toolTip())
        self.open_obj_action.triggered.connect(self.open_obj_bundle_dialog)

        self.export_bundle_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_DialogSaveButton),
            "Export OBJ/MTL/PNG...",
            self,
        )
        self.export_bundle_action.setToolTip(
            "Export the current VTU conversion settings as an OBJ/MTL/PNG bundle."
        )
        self.export_bundle_action.setStatusTip(self.export_bundle_action.toolTip())
        self.export_bundle_action.triggered.connect(self.export_current_bundle)

        self.reset_defaults_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_BrowserReload),
            "Reset GUI Defaults",
            self,
        )
        self.reset_defaults_action.setToolTip(
            "Forget persisted GUI preferences and restore the built-in default "
            "settings."
        )
        self.reset_defaults_action.setStatusTip(self.reset_defaults_action.toolTip())
        self.reset_defaults_action.triggered.connect(self.reset_gui_defaults)

        self.about_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_MessageBoxInformation),
            "About fossils-vtu2obj",
            self,
        )
        self.about_action.setToolTip(
            "Show a short description of the application and its main workflow."
        )
        self.about_action.setStatusTip(self.about_action.toolTip())
        self.about_action.triggered.connect(self.show_about_dialog)

        self.github_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_DirLinkIcon),
            "Open GitHub Repository",
            self,
        )
        self.github_action.setToolTip(
            "Open the GitHub repository of this project in your default web browser."
        )
        self.github_action.setStatusTip(self.github_action.toolTip())
        self.github_action.triggered.connect(self.open_github_repository)

        self.credits_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_FileDialogInfoView),
            "Show Credits",
            self,
        )
        self.credits_action.setToolTip(
            "Display the project credits for Romain Boman and OpenAI Codex."
        )
        self.credits_action.setStatusTip(self.credits_action.toolTip())
        self.credits_action.triggered.connect(self.show_credits_dialog)

    def _build_menus(self) -> None:
        """Create the application menus."""
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_vtu_action)
        file_menu.addAction(self.open_obj_action)
        file_menu.addSeparator()
        file_menu.addAction(self.export_bundle_action)

        settings_menu = menu_bar.addMenu("&Settings")
        settings_menu.addAction(self.reset_defaults_action)

        help_menu = menu_bar.addMenu("&Help")
        help_menu.addAction(self.about_action)
        help_menu.addAction(self.github_action)

        credits_menu = menu_bar.addMenu("&Credits")
        credits_menu.addAction(self.credits_action)

    def _build_vtu_controls_group(self) -> QtWidgets.QGroupBox:
        """Build the left-hand VTU and conversion controls."""
        group = QtWidgets.QGroupBox("VTU / Conversion", self)
        group.setToolTip(
            "Load a VTU file, choose the scalar-mapping settings, preview the "
            "volume mesh, and export the OBJ bundle."
        )
        layout = QtWidgets.QGridLayout(group)

        self.open_button = QtWidgets.QPushButton("Open VTU...")
        self.open_button.setIcon(self.open_vtu_action.icon())
        self.open_button.setToolTip(self.open_vtu_action.toolTip())
        self.open_button.clicked.connect(self.open_file_dialog)
        layout.addWidget(self.open_button, 0, 0)

        self.vtu_path_edit = QtWidgets.QLineEdit()
        self.vtu_path_edit.setReadOnly(True)
        self.vtu_path_edit.setPlaceholderText("No VTU file loaded")
        self.vtu_path_edit.setToolTip(
            "Absolute path of the VTU file currently loaded for preview and "
            "conversion."
        )
        layout.addWidget(self.vtu_path_edit, 0, 1, 1, 5)

        self.field_combo = QtWidgets.QComboBox()
        self.field_combo.setToolTip(
            "Choose the scalar array used to color the volume view and to drive "
            "the exported texture coordinates."
        )
        self.field_combo.currentIndexChanged.connect(self._handle_field_changed)
        field_label = QtWidgets.QLabel("Field")
        field_label.setToolTip(self.field_combo.toolTip())
        layout.addWidget(field_label, 1, 0)
        layout.addWidget(self.field_combo, 1, 1)

        self.colormap_combo = QtWidgets.QComboBox()
        for name in list_colormap_names():
            self.colormap_combo.addItem(name)
        self.colormap_combo.setToolTip(
            "Choose the discrete colormap used for scalar coloring and palette "
            "texture generation."
        )
        self.colormap_combo.currentIndexChanged.connect(self.refresh_preview)
        colormap_label = QtWidgets.QLabel("Colormap")
        colormap_label.setToolTip(self.colormap_combo.toolTip())
        layout.addWidget(colormap_label, 1, 2)
        layout.addWidget(self.colormap_combo, 1, 3)

        self.n_colors_spin = QtWidgets.QSpinBox()
        self.n_colors_spin.setRange(2, 4096)
        self.n_colors_spin.setValue(DEFAULT_N_COLORS)
        self.n_colors_spin.setToolTip(
            "Number of discrete palette bins used for preview, UV quantization, "
            "and the exported PNG texture."
        )
        n_colors_label = QtWidgets.QLabel("Color bins")
        n_colors_label.setToolTip(self.n_colors_spin.toolTip())
        layout.addWidget(n_colors_label, 1, 4)
        layout.addWidget(self.n_colors_spin, 1, 5)

        self.vmin_spin = QtWidgets.QDoubleSpinBox()
        self.vmax_spin = QtWidgets.QDoubleSpinBox()
        for spin_box in (self.vmin_spin, self.vmax_spin):
            spin_box.setDecimals(DEFAULT_SPINBOX_DECIMALS)
            spin_box.setRange(DEFAULT_SPINBOX_MIN, DEFAULT_SPINBOX_MAX)
            spin_box.setSingleStep(DEFAULT_SPINBOX_STEP)
        self.vmin_spin.setToolTip(
            "Lower bound of the scalar range mapped to the colormap and texture. "
            "Values below this limit are clamped."
        )
        self.vmax_spin.setToolTip(
            "Upper bound of the scalar range mapped to the colormap and texture. "
            "Values above this limit are clamped."
        )
        vmin_label = QtWidgets.QLabel("vmin")
        vmin_label.setToolTip(self.vmin_spin.toolTip())
        layout.addWidget(vmin_label, 2, 0)
        layout.addWidget(self.vmin_spin, 2, 1)
        vmax_label = QtWidgets.QLabel("vmax")
        vmax_label.setToolTip(self.vmax_spin.toolTip())
        layout.addWidget(vmax_label, 2, 2)
        layout.addWidget(self.vmax_spin, 2, 3)

        self.normals_checkbox = QtWidgets.QCheckBox("Generate normals")
        self.normals_checkbox.setChecked(True)
        self.normals_checkbox.setToolTip(
            "Generate and export point normals on the surface mesh so downstream "
            "tools can shade the OBJ more smoothly."
        )
        layout.addWidget(self.normals_checkbox, 2, 4, 1, 2)

        self.reset_range_button = QtWidgets.QPushButton("Use Data Range")
        self.reset_range_button.setIcon(
            standard_icon(self, QtWidgets.QStyle.SP_ArrowBack)
        )
        self.reset_range_button.setToolTip(
            "Reset vmin and vmax to the actual data range of the currently "
            "selected scalar field."
        )
        self.reset_range_button.clicked.connect(self.reset_current_range)
        layout.addWidget(self.reset_range_button, 3, 0, 1, 2)

        self.refresh_button = QtWidgets.QPushButton("Refresh Volume View")
        self.refresh_button.setIcon(
            standard_icon(self, QtWidgets.QStyle.SP_BrowserReload)
        )
        self.refresh_button.setToolTip(
            "Rebuild the left-hand volume preview using the current field, range, "
            "and colormap settings."
        )
        self.refresh_button.clicked.connect(self.refresh_preview)
        layout.addWidget(self.refresh_button, 3, 2, 1, 2)

        self.export_button = QtWidgets.QPushButton("Export OBJ/MTL/PNG...")
        self.export_button.setIcon(self.export_bundle_action.icon())
        self.export_button.setToolTip(self.export_bundle_action.toolTip())
        self.export_button.clicked.connect(self.export_current_bundle)
        layout.addWidget(self.export_button, 3, 4, 1, 2)

        return group

    def _build_obj_controls_group(self) -> QtWidgets.QGroupBox:
        """Build the right-hand OBJ bundle controls."""
        group = QtWidgets.QGroupBox("OBJ Bundle / Comparison", self)
        group.setToolTip(
            "Load an exported OBJ/MTL/PNG bundle and compare it against the VTU "
            "volume view."
        )
        layout = QtWidgets.QGridLayout(group)

        self.open_obj_button = QtWidgets.QPushButton("Open OBJ Bundle...")
        self.open_obj_button.setIcon(self.open_obj_action.icon())
        self.open_obj_button.setToolTip(self.open_obj_action.toolTip())
        self.open_obj_button.clicked.connect(self.open_obj_bundle_dialog)
        layout.addWidget(self.open_obj_button, 0, 0)

        self.obj_path_edit = QtWidgets.QLineEdit()
        self.obj_path_edit.setReadOnly(True)
        self.obj_path_edit.setPlaceholderText(
            "No OBJ bundle loaded yet (export one from the left panel or open one)"
        )
        self.obj_path_edit.setToolTip(
            "Absolute path of the OBJ file currently displayed in the right-hand "
            "comparison viewport."
        )
        layout.addWidget(self.obj_path_edit, 0, 1)

        hint_label = QtWidgets.QLabel(
            "The right panel shows the last exported bundle or any OBJ bundle you open."
        )
        hint_label.setWordWrap(True)
        hint_label.setToolTip(
            "The OBJ viewport can be updated automatically after export from the "
            "left panel, or manually by opening an existing bundle."
        )
        layout.addWidget(hint_label, 1, 0, 1, 2)

        return group

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
        self.export_bundle_action.setEnabled(enabled)

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
        colormap = str(self._settings.value("colormap", DEFAULT_COLORMAP_NAME))
        colormap_index = self.colormap_combo.findText(colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        self.n_colors_spin.setValue(int(self._settings.value("n_colors", DEFAULT_N_COLORS)))
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
                self.main_splitter.setSizes([int(value) for value in splitter_sizes])
            except (TypeError, ValueError):
                pass
        else:
            self.main_splitter.setSizes(list(DEFAULT_GUI_SPLITTER_SIZES))

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
        self._settings.setValue("splitter_sizes", self.main_splitter.sizes())
        self._save_viewport_settings("volume", self.volume_panel)
        self._save_viewport_settings("bundle", self.bundle_panel)
        self._settings.sync()

    def _apply_default_gui_settings(self) -> None:
        """Apply the built-in default settings to the current session."""
        self.colormap_combo.setCurrentText(DEFAULT_COLORMAP_NAME)
        self.n_colors_spin.setValue(DEFAULT_N_COLORS)
        self.normals_checkbox.setChecked(True)
        self.volume_panel.set_display_options(self.VOLUME_DEFAULTS)
        self.bundle_panel.set_display_options(self.BUNDLE_DEFAULTS)
        self.main_splitter.setSizes(list(DEFAULT_GUI_SPLITTER_SIZES))

    def _selected_startup_field_name(self) -> str | None:
        """Return the best field to select for the current dataset."""
        if self._current_summary is None:
            return None

        scalar_names = scalar_field_names(self._current_summary)
        if not scalar_names:
            return None

        last_field = str(self._settings.value("last_field", "")).strip()
        if last_field and last_field in scalar_names:
            return last_field
        return preferred_scalar_field_name(
            self._current_summary,
            preferred_name=DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
        )

    def reset_gui_defaults(self) -> None:
        """Forget persisted GUI settings and restore the built-in defaults."""
        self._settings.clear()
        self._settings.sync()
        self._apply_default_gui_settings()

        if self.field_combo.count() > 0:
            preferred_name = preferred_scalar_field_name(
                self._current_summary,
                preferred_name=DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
            )
            if preferred_name is not None:
                self.field_combo.setCurrentText(preferred_name)
            self.reset_current_range()
            self.refresh_preview()
        if self._current_bundle_scene is not None:
            self.bundle_panel.set_display_options(self.BUNDLE_DEFAULTS)

        self.statusBar().showMessage("GUI settings reset to defaults.")

    def _show_error(self, message: str) -> None:
        """Display an error dialog and mirror the message in the status bar."""
        self.statusBar().showMessage(message)
        QtWidgets.QMessageBox.critical(self, DEFAULT_WINDOW_TITLE, message)

    def show_about_dialog(self) -> None:
        """Show a compact description of the application."""
        QtWidgets.QMessageBox.about(
            self,
            "About fossils-vtu2obj",
            "\n".join(
                [
                    "fossils-vtu2obj converts VTU FEM results into a surface OBJ,",
                    "a PNG palette texture, and a matching MTL file.",
                    "",
                    "The left panel is dedicated to VTU inspection and conversion.",
                    "The right panel is dedicated to OBJ bundle comparison.",
                    "",
                    f"GitHub: {self.GITHUB_URL}",
                ]
            ),
        )

    def show_credits_dialog(self) -> None:
        """Show the project credits."""
        QtWidgets.QMessageBox.information(
            self,
            "Credits",
            "\n".join(
                [
                    "Project author: Romain Boman",
                    "Development assistance: OpenAI Codex",
                ]
            ),
        )

    def open_github_repository(self) -> None:
        """Open the GitHub repository in the default browser."""
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.GITHUB_URL))

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

        scalar_names = scalar_field_names(self._current_summary)
        if not scalar_names:
            raise ValueError(
                "The selected VTU file does not contain scalar point or cell data."
            )

        self.vtu_path_edit.setText(str(self.current_file_path))
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(list(scalar_names))
        startup_field = self._selected_startup_field_name()
        if startup_field is not None:
            self.field_combo.setCurrentText(startup_field)
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
        self.obj_path_edit.setText(str(bundle.obj_path))
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
        self.volume_panel.shutdown()
        self.bundle_panel.shutdown()
        super().closeEvent(event)
