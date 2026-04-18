"""Main window for the PyQt5 GUI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from PyQt5 import QtCore, QtGui, QtWidgets

from ..arrays import (
    preferred_scalar_field_name,
    scalar_field_names,
)
from ..colormaps import list_colormap_names
from ..defaults import (
    DEFAULT_BACKGROUND_PRESET,
    DEFAULT_BUNDLE_EDGE_COLOR,
    DEFAULT_BUNDLE_SHOW_AXES,
    DEFAULT_BUNDLE_SHOW_BOUNDING_BOX,
    DEFAULT_BUNDLE_SHOW_EDGES,
    DEFAULT_CAMERA_PRESET,
    DEFAULT_COLORMAP_NAME,
    DEFAULT_GENERATE_NORMALS,
    DEFAULT_GITHUB_URL,
    DEFAULT_LIGHTING_INTENSITY,
    DEFAULT_LIGHTING_PRESET,
    DEFAULT_N_COLORS,
    DEFAULT_N_COLORS_MAX,
    DEFAULT_N_COLORS_MIN,
    DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
    DEFAULT_SPINBOX_DECIMALS,
    DEFAULT_SPINBOX_MAX,
    DEFAULT_SPINBOX_MIN,
    DEFAULT_SPINBOX_STEP,
    DEFAULT_TEXTURE_PREVIEW_SIZE,
    DEFAULT_VOLUME_EDGE_COLOR,
    DEFAULT_VOLUME_SHOW_AXES,
    DEFAULT_VOLUME_SHOW_BOUNDING_BOX,
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


@dataclass(frozen=True)
class _LoadedFileResult:
    """Hold the data produced by one VTU loading task."""

    current_file_path: Path
    grid: object
    summary: DatasetSummary
    surface: object
    scalar_names: tuple[str, ...]
    selected_field: str
    field_range: tuple[float, float]
    scene: object | None = None


@dataclass(frozen=True)
class _LoadedObjBundleResult:
    """Hold the data produced by one OBJ bundle loading task."""

    bundle: object
    scene: object


@dataclass(frozen=True)
class _ExportBundleResult:
    """Hold the data produced by one OBJ export task."""

    bundle: object
    scene: object


class _BackgroundTaskWorker(QtCore.QObject):
    """Run one long-running callable in a dedicated Qt thread."""

    progress = QtCore.pyqtSignal(int, str)
    succeeded = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal()

    def __init__(
        self,
        task_fn: Callable[[Callable[[int, str], None]], object],
    ) -> None:
        super().__init__()
        self._task_fn = task_fn

    @QtCore.pyqtSlot()
    def run(self) -> None:
        """Execute the background callable and emit its outcome."""
        try:
            result = self._task_fn(self._emit_progress)
        except Exception as exc:  # pragma: no cover - defensive GUI path
            self.failed.emit(str(exc))
        else:
            self.succeeded.emit(result)
        finally:
            self.finished.emit()

    def _emit_progress(self, value: int, label_text: str) -> None:
        """Forward one progress update to the GUI thread."""
        self.progress.emit(value, label_text)


class _OperationCancelled(Exception):
    """Raised when the user cancels one long-running GUI operation."""


def _format_file_size(num_bytes: int) -> str:
    """Render one byte count with a compact human-readable unit."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{num_bytes} B"


class _OperationProgressDialog(QtWidgets.QDialog):
    """Large progress dialog used for long synchronous GUI operations."""

    def __init__(
        self,
        parent: QtWidgets.QWidget,
        *,
        title: str,
        label_text: str,
        maximum: int,
        subject_path: str | Path | None = None,
        can_cancel: bool = True,
    ) -> None:
        super().__init__(parent)
        self._cancel_requested = False
        self._elapsed = QtCore.QElapsedTimer()
        self._elapsed.start()
        self._elapsed_timer = QtCore.QTimer(self)
        self._elapsed_timer.setInterval(200)
        self._elapsed_timer.timeout.connect(self._refresh_elapsed_label)

        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.resize(700, 250)
        self.setMinimumSize(700, 250)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        self.message_label = QtWidgets.QLabel(label_text, self)
        self.message_label.setWordWrap(True)
        message_font = self.message_label.font()
        message_font.setBold(True)
        self.message_label.setFont(message_font)
        layout.addWidget(self.message_label)

        details_box = QtWidgets.QGroupBox("Operation Details", self)
        details_layout = QtWidgets.QGridLayout(details_box)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setHorizontalSpacing(12)
        details_layout.setVerticalSpacing(6)

        self.file_name_value = QtWidgets.QLabel("-", details_box)
        self.file_path_value = QtWidgets.QLabel("-", details_box)
        self.file_path_value.setWordWrap(True)
        self.file_size_value = QtWidgets.QLabel("-", details_box)
        self.file_modified_value = QtWidgets.QLabel("-", details_box)
        self.elapsed_value = QtWidgets.QLabel("0.0 s", details_box)

        for row, (label, value_widget) in enumerate(
            (
                ("File", self.file_name_value),
                ("Path", self.file_path_value),
                ("Size", self.file_size_value),
                ("Modified", self.file_modified_value),
                ("Elapsed", self.elapsed_value),
            )
        ):
            details_layout.addWidget(QtWidgets.QLabel(label, details_box), row, 0)
            details_layout.addWidget(value_widget, row, 1)
        layout.addWidget(details_box)

        self.progress_bar = QtWidgets.QProgressBar(self)
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.activity_bar = QtWidgets.QProgressBar(self)
        self.activity_bar.setRange(0, 0)
        self.activity_bar.setTextVisible(False)
        layout.addWidget(self.activity_bar)

        self.hint_label = QtWidgets.QLabel(
            "Large VTK operations may block repainting for several seconds on very "
            "large meshes. The operation is still running even if the main progress "
            "bar appears paused.",
            self,
        )
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch(1)
        self.cancel_button = QtWidgets.QPushButton("Cancel", self)
        self.cancel_button.setEnabled(can_cancel)
        self.cancel_button.clicked.connect(self._request_cancel)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self._set_subject_path(subject_path)
        self._elapsed_timer.start()

    def set_message(self, text: str) -> None:
        """Update the main operation message."""
        self.message_label.setText(text)

    def set_progress(self, value: int) -> None:
        """Update the determinate progress bar."""
        self.progress_bar.setValue(value)

    def maximum(self) -> int:
        """Return the maximum value of the determinate progress bar."""
        return self.progress_bar.maximum()

    def cancel_requested(self) -> bool:
        """Return whether the user asked to cancel this operation."""
        return self._cancel_requested

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Stop the local timer when the dialog closes."""
        self._elapsed_timer.stop()
        super().closeEvent(event)

    def _request_cancel(self) -> None:
        """Record a cancellation request from the user."""
        self._cancel_requested = True
        self.cancel_button.setEnabled(False)
        self.cancel_button.setText("Cancelling...")
        self.hint_label.setText(
            "Cancellation will happen at the next safe stage boundary. "
            "An active VTK call cannot be interrupted immediately."
        )

    def _set_subject_path(self, subject_path: str | Path | None) -> None:
        """Display file metadata for the current long-running operation."""
        if subject_path is None:
            return

        path = Path(subject_path).expanduser().resolve(strict=False)
        self.file_name_value.setText(path.name)
        self.file_path_value.setText(str(path))
        if path.exists():
            try:
                self.file_size_value.setText(_format_file_size(path.stat().st_size))
                modified = datetime.fromtimestamp(path.stat().st_mtime)
                self.file_modified_value.setText(
                    modified.strftime("%Y-%m-%d %H:%M:%S")
                )
            except OSError:
                self.file_size_value.setText("Unavailable")
                self.file_modified_value.setText("Unavailable")
        else:
            self.file_size_value.setText("File does not exist yet")
            self.file_modified_value.setText("-")

    def _refresh_elapsed_label(self) -> None:
        """Update the elapsed-time label while the dialog is visible."""
        self.elapsed_value.setText(f"{self._elapsed.elapsed() / 1000.0:.1f} s")


class MainWindow(QtWidgets.QMainWindow):
    """GUI for inspecting VTU files and comparing them with exported OBJ bundles."""

    ORGANIZATION_NAME = "fossils"
    APPLICATION_NAME = "fossils-vtu2obj"
    MAX_RECENT_FILES = 10
    GITHUB_URL = DEFAULT_GITHUB_URL
    VOLUME_DEFAULTS = ViewDisplayOptions(
        show_edges=DEFAULT_VOLUME_SHOW_EDGES,
        edge_color=DEFAULT_VOLUME_EDGE_COLOR,
        show_axes=DEFAULT_VOLUME_SHOW_AXES,
        show_bounding_box=DEFAULT_VOLUME_SHOW_BOUNDING_BOX,
        background_preset=DEFAULT_BACKGROUND_PRESET,
        lighting_preset=DEFAULT_LIGHTING_PRESET,
        lighting_intensity=DEFAULT_LIGHTING_INTENSITY,
        camera_preset=DEFAULT_CAMERA_PRESET,
    )
    BUNDLE_DEFAULTS = ViewDisplayOptions(
        show_edges=DEFAULT_BUNDLE_SHOW_EDGES,
        edge_color=DEFAULT_BUNDLE_EDGE_COLOR,
        show_axes=DEFAULT_BUNDLE_SHOW_AXES,
        show_bounding_box=DEFAULT_BUNDLE_SHOW_BOUNDING_BOX,
        background_preset=DEFAULT_BACKGROUND_PRESET,
        lighting_preset=DEFAULT_LIGHTING_PRESET,
        lighting_intensity=DEFAULT_LIGHTING_INTENSITY,
        camera_preset=DEFAULT_CAMERA_PRESET,
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
        self._active_thread: QtCore.QThread | None = None
        self._active_worker: _BackgroundTaskWorker | None = None
        self._active_progress_dialog: QtWidgets.QProgressDialog | None = None
        self._startup_file_path: str | Path | None = None
        self._startup_bundle_path: str | Path | None = None
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
            self._startup_file_path = initial_path
        else:
            last_file = self._settings.value("last_file_path")
            if last_file:
                self._startup_file_path = last_file

        last_obj_bundle_path = self._settings.value("last_obj_bundle_path")
        if last_obj_bundle_path:
            self._startup_bundle_path = last_obj_bundle_path

        if self._startup_file_path is not None or self._startup_bundle_path is not None:
            QtCore.QTimer.singleShot(0, self._start_deferred_startup_tasks)

    def _build_ui(self) -> None:
        """Create the window layout and interactive controls."""
        self._build_actions()
        self._build_menus()

        central_widget = QtWidgets.QWidget(self)
        self.setCentralWidget(central_widget)
        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        panels_grid = QtWidgets.QGridLayout()
        panels_grid.setSpacing(8)
        panels_grid.setColumnStretch(0, 1)
        panels_grid.setColumnStretch(1, 1)
        root_layout.addLayout(panels_grid, stretch=1)

        self.volume_panel = MeshViewportPanel(
            "Volume Mesh",
            default_display_options=self.VOLUME_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=central_widget,
        )
        self.bundle_panel = MeshViewportPanel(
            "Exported Surface Bundle",
            default_display_options=self.BUNDLE_DEFAULTS,
            enable_vtk_view=self._enable_vtk_view,
            parent=central_widget,
        )
        panels_grid.addWidget(self.volume_panel, 0, 0)
        panels_grid.addWidget(self.bundle_panel, 0, 1)

        self.vtu_controls_group = self._build_vtu_controls_group()
        self.volume_panel.insert_tab(
            self.vtu_controls_group,
            "Controls",
            tooltip=(
                "VTU loading, scalar mapping, and export controls for the left "
                "viewport."
            ),
        )

        self.obj_controls_group = self._build_obj_controls_group()
        self.bundle_panel.insert_tab(
            self.obj_controls_group,
            "Controls",
            tooltip=(
                "OBJ bundle loading and texture-preview controls for the right "
                "viewport."
            ),
        )

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
            standard_icon(self, QtWidgets.QStyle.SP_DialogOpenButton),
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
        self.export_bundle_action.setStatusTip(
            self.export_bundle_action.toolTip())
        self.export_bundle_action.triggered.connect(
            self.start_export_current_bundle_async
        )

        self.clear_views_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_DialogResetButton),
            "Clear Views",
            self,
        )
        self.clear_views_action.setToolTip(
            "Unload the currently displayed VTU and OBJ scenes and reset both "
            "viewports to an empty state."
        )
        self.clear_views_action.setStatusTip(self.clear_views_action.toolTip())
        self.clear_views_action.triggered.connect(self.clear_views)

        self.reset_defaults_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_BrowserReload),
            "Reset GUI Defaults",
            self,
        )
        self.reset_defaults_action.setToolTip(
            "Forget persisted GUI preferences and restore the built-in default "
            "settings."
        )
        self.reset_defaults_action.setStatusTip(
            self.reset_defaults_action.toolTip())
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

        self.show_qsettings_action = QtWidgets.QAction(
            standard_icon(self, QtWidgets.QStyle.SP_FileDialogDetailedView),
            "Show QSettings",
            self,
        )
        self.show_qsettings_action.setToolTip(
            "Display all QSettings values and the file where they are stored."
        )
        self.show_qsettings_action.setStatusTip(self.show_qsettings_action.toolTip())
        self.show_qsettings_action.triggered.connect(self.show_qsettings_dialog)

    def _build_menus(self) -> None:
        """Create the application menus."""
        menu_bar = self.menuBar()

        self.file_menu = menu_bar.addMenu("&File")
        self.file_menu.addAction(self.open_vtu_action)
        self.recent_vtu_menu = self.file_menu.addMenu("Recent &VTU Files")
        self.file_menu.addAction(self.open_obj_action)
        self.recent_obj_menu = self.file_menu.addMenu("Recent &OBJ Bundles")
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.export_bundle_action)
        self.file_menu.addAction(self.clear_views_action)
        self._refresh_recent_file_menus()

        self.settings_menu = menu_bar.addMenu("&Settings")
        self.settings_menu.addAction(self.reset_defaults_action)

        self.help_menu = menu_bar.addMenu("&Help")
        self.help_menu.addAction(self.about_action)
        self.help_menu.addAction(self.github_action)
        self.help_menu.addAction(self.credits_action)

        self.debug_menu = menu_bar.addMenu("&Debug")
        self.debug_menu.addAction(self.show_qsettings_action)

    def _build_vtu_controls_group(self) -> QtWidgets.QGroupBox:
        """Build the left-hand VTU and conversion controls."""
        group = QtWidgets.QGroupBox("VTU / Conversion", self)
        group.setToolTip(
            "Load a VTU file, choose the scalar-mapping settings, preview the "
            "volume mesh, and export the OBJ bundle."
        )
        layout = QtWidgets.QVBoxLayout(group)

        open_row = QtWidgets.QHBoxLayout()
        self.open_button = QtWidgets.QPushButton("Open VTU...")
        self.open_button.setIcon(self.open_vtu_action.icon())
        self.open_button.setToolTip(self.open_vtu_action.toolTip())
        self.open_button.clicked.connect(self.open_file_dialog)
        open_row.addWidget(self.open_button)

        self.vtu_path_edit = QtWidgets.QLineEdit()
        self.vtu_path_edit.setReadOnly(True)
        self.vtu_path_edit.setPlaceholderText("No VTU file loaded")
        self.vtu_path_edit.setToolTip(
            "Absolute path of the VTU file currently loaded for preview and "
            "conversion."
        )
        open_row.addWidget(self.vtu_path_edit, stretch=1)
        layout.addLayout(open_row)

        display_group = QtWidgets.QGroupBox("Display / Color Mapping", group)
        display_layout = QtWidgets.QGridLayout(display_group)

        self.field_combo = QtWidgets.QComboBox()
        self.field_combo.setToolTip(
            "Choose the scalar array used to color the volume view and to drive "
            "the exported texture coordinates."
        )
        self.field_combo.currentIndexChanged.connect(
            self._handle_field_changed)
        field_label = QtWidgets.QLabel("Field")
        field_label.setToolTip(self.field_combo.toolTip())
        display_layout.addWidget(field_label, 0, 0)
        display_layout.addWidget(self.field_combo, 0, 1)

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
        display_layout.addWidget(colormap_label, 0, 2)
        display_layout.addWidget(self.colormap_combo, 0, 3)

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
        display_layout.addWidget(vmin_label, 1, 0)
        display_layout.addWidget(self.vmin_spin, 1, 1)
        vmax_label = QtWidgets.QLabel("vmax")
        vmax_label.setToolTip(self.vmax_spin.toolTip())
        display_layout.addWidget(vmax_label, 1, 2)
        display_layout.addWidget(self.vmax_spin, 1, 3)

        self.reset_range_button = QtWidgets.QPushButton("Use Data Range")
        self.reset_range_button.setIcon(
            standard_icon(self, QtWidgets.QStyle.SP_ArrowBack)
        )
        self.reset_range_button.setToolTip(
            "Reset vmin and vmax to the actual data range of the currently "
            "selected scalar field."
        )
        self.reset_range_button.clicked.connect(self.reset_current_range)
        display_layout.addWidget(self.reset_range_button, 2, 0, 1, 2)

        self.refresh_button = QtWidgets.QPushButton("Refresh Volume View")
        self.refresh_button.setIcon(
            standard_icon(self, QtWidgets.QStyle.SP_BrowserReload)
        )
        self.refresh_button.setToolTip(
            "Rebuild the left-hand volume preview using the current field, range, "
            "and colormap settings."
        )
        self.refresh_button.clicked.connect(self.refresh_preview)
        display_layout.addWidget(self.refresh_button, 2, 2, 1, 2)
        layout.addWidget(display_group)

        export_group = QtWidgets.QGroupBox("Export", group)
        export_layout = QtWidgets.QGridLayout(export_group)

        self.normals_checkbox = QtWidgets.QCheckBox("Generate normals")
        self.normals_checkbox.setChecked(DEFAULT_GENERATE_NORMALS)
        self.normals_checkbox.setToolTip(
            "Generate and export point normals on the surface mesh so downstream "
            "tools can shade the OBJ more smoothly."
        )
        export_layout.addWidget(self.normals_checkbox, 0, 0)

        self.n_colors_spin = QtWidgets.QSpinBox()
        self.n_colors_spin.setRange(DEFAULT_N_COLORS_MIN, DEFAULT_N_COLORS_MAX)
        self.n_colors_spin.setValue(DEFAULT_N_COLORS)
        self.n_colors_spin.setToolTip(
            "Number of discrete palette bins used for preview, UV quantization, "
            "and the exported PNG texture."
        )
        n_colors_label = QtWidgets.QLabel("Color bins")
        n_colors_label.setToolTip(self.n_colors_spin.toolTip())
        export_layout.addWidget(n_colors_label, 0, 1)
        export_layout.addWidget(self.n_colors_spin, 0, 2)

        self.export_button = QtWidgets.QPushButton("Export OBJ/MTL/PNG...")
        self.export_button.setIcon(self.export_bundle_action.icon())
        self.export_button.setToolTip(self.export_bundle_action.toolTip())
        self.export_button.clicked.connect(self.start_export_current_bundle_async)
        export_layout.addWidget(self.export_button, 0, 3)
        export_layout.setColumnStretch(3, 1)
        layout.addWidget(export_group)

        return group

    def _build_obj_controls_group(self) -> QtWidgets.QGroupBox:
        """Build the right-hand OBJ bundle controls."""
        group = QtWidgets.QGroupBox("OBJ Bundle / Comparison", self)
        group.setToolTip(
            "Load an exported OBJ/MTL/PNG bundle and compare it against the VTU "
            "volume view."
        )
        layout = QtWidgets.QVBoxLayout(group)

        open_row = QtWidgets.QHBoxLayout()

        self.open_obj_button = QtWidgets.QPushButton("Open OBJ Bundle...")
        self.open_obj_button.setIcon(self.open_obj_action.icon())
        self.open_obj_button.setToolTip(self.open_obj_action.toolTip())
        self.open_obj_button.clicked.connect(self.open_obj_bundle_dialog)
        open_row.addWidget(self.open_obj_button)

        self.obj_path_edit = QtWidgets.QLineEdit()
        self.obj_path_edit.setReadOnly(True)
        self.obj_path_edit.setPlaceholderText(
            "No OBJ bundle loaded yet (export one from the left panel or open one)"
        )
        self.obj_path_edit.setToolTip(
            "Absolute path of the OBJ file currently displayed in the right-hand "
            "comparison viewport."
        )
        open_row.addWidget(self.obj_path_edit, stretch=1)
        layout.addLayout(open_row)

        hint_label = QtWidgets.QLabel(
            "The right panel shows the last exported bundle or any OBJ bundle you open."
        )
        hint_label.setWordWrap(True)
        hint_label.setToolTip(
            "The OBJ viewport can be updated automatically after export from the "
            "left panel, or manually by opening an existing bundle."
        )
        layout.addWidget(hint_label)

        texture_group = QtWidgets.QGroupBox("Texture Preview", group)
        texture_layout = QtWidgets.QGridLayout(texture_group)
        self.texture_preview_label = QtWidgets.QLabel(
            "No texture loaded",
            texture_group,
        )
        self.texture_preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.texture_preview_label.setMinimumSize(*DEFAULT_TEXTURE_PREVIEW_SIZE)
        self.texture_preview_label.setToolTip(
            "Quick preview of the texture associated with the currently loaded "
            "OBJ bundle."
        )
        self.texture_dimensions_label = QtWidgets.QLabel("Size: -", texture_group)
        self.texture_dimensions_label.setToolTip(
            "Dimensions in pixels of the currently loaded texture."
        )
        self.texture_path_label = QtWidgets.QLabel("Path: -", texture_group)
        self.texture_path_label.setWordWrap(True)
        self.texture_path_label.setToolTip(
            "Filesystem path of the currently loaded texture, when present."
        )
        texture_layout.addWidget(self.texture_preview_label, 0, 0, 3, 1)
        texture_layout.addWidget(self.texture_dimensions_label, 0, 1)
        texture_layout.addWidget(self.texture_path_label, 1, 1)
        texture_layout.setColumnStretch(1, 1)
        layout.addWidget(texture_group)

        self._update_texture_preview()

        return group

    def _clear_texture_preview(self) -> None:
        """Reset the lightweight OBJ texture preview widgets."""
        self.texture_preview_label.setPixmap(QtGui.QPixmap())
        self.texture_preview_label.setText("No texture loaded")
        self.texture_dimensions_label.setText("Size: -")
        self.texture_path_label.setText("Path: -")

    def _update_texture_preview(
        self,
        texture_path: str | Path | None = None,
        texture_size: tuple[int, int] | None = None,
    ) -> None:
        """Refresh the lightweight texture preview shown above the OBJ viewport."""
        if texture_path is None:
            if (
                self._current_bundle is None
                or self._current_bundle.texture_path is None
            ):
                self._clear_texture_preview()
                return
            texture_path = self._current_bundle.texture_path

        resolved_path = Path(texture_path).expanduser().resolve(strict=False)
        if not resolved_path.is_file():
            self._clear_texture_preview()
            self.texture_preview_label.setText("Texture file missing")
            self.texture_path_label.setText(f"Path: {resolved_path}")
            return

        pixmap = QtGui.QPixmap(str(resolved_path))
        if pixmap.isNull():
            self._clear_texture_preview()
            self.texture_preview_label.setText("Texture preview unavailable")
            self.texture_path_label.setText(f"Path: {resolved_path}")
            return

        preview_width, preview_height = DEFAULT_TEXTURE_PREVIEW_SIZE
        scaled_pixmap = pixmap.scaled(
            preview_width,
            preview_height,
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.texture_preview_label.setText("")
        self.texture_preview_label.setPixmap(scaled_pixmap)
        if texture_size is None:
            texture_size = (pixmap.width(), pixmap.height())
        self.texture_dimensions_label.setText(
            f"Size: {texture_size[0]} x {texture_size[1]} px"
        )
        self.texture_path_label.setText(f"Path: {resolved_path}")

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

    def clear_views(self) -> None:
        """Unload the currently displayed meshes and clear both viewports."""
        self.current_file_path = None
        self._current_grid = None
        self._current_surface = None
        self._current_summary = None
        self._current_volume_scene = None
        self._current_bundle = None
        self._current_bundle_scene = None
        self._startup_file_path = None
        self._startup_bundle_path = None

        self.vtu_path_edit.clear()
        self.obj_path_edit.clear()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.blockSignals(False)
        self.volume_panel.clear_scene()
        self.bundle_panel.clear_scene()
        self._clear_texture_preview()
        self._set_controls_enabled(False)

        self._settings.remove("last_file_path")
        self._settings.remove("last_obj_bundle_path")
        self._settings.remove("last_field")
        self._settings.sync()
        self.statusBar().showMessage("Views cleared.")

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
                show_bounding_box=self._setting_to_bool(
                    self._settings.value(f"{prefix}_show_bounding_box"),
                    defaults.show_bounding_box,
                ),
                background_preset=str(
                    self._settings.value(
                        f"{prefix}_background_preset",
                        defaults.background_preset,
                    )
                ),
                lighting_preset=str(
                    self._settings.value(
                        f"{prefix}_lighting_preset",
                        defaults.lighting_preset,
                    )
                ),
                lighting_intensity=max(
                    0,
                    min(
                        200,
                        int(
                            self._settings.value(
                                f"{prefix}_lighting_intensity",
                                defaults.lighting_intensity,
                            )
                        ),
                    ),
                ),
                camera_preset=str(
                    self._settings.value(
                        f"{prefix}_camera_preset",
                        defaults.camera_preset,
                    )
                ),
            )
        )

    def _restore_settings(self) -> None:
        """Restore GUI state from persistent storage."""
        colormap = str(self._settings.value("colormap", DEFAULT_COLORMAP_NAME))
        colormap_index = self.colormap_combo.findText(colormap)
        if colormap_index >= 0:
            self.colormap_combo.setCurrentIndex(colormap_index)

        restored_n_colors = int(self._settings.value("n_colors", DEFAULT_N_COLORS))
        restored_n_colors = max(
            DEFAULT_N_COLORS_MIN,
            min(DEFAULT_N_COLORS_MAX, restored_n_colors),
        )
        self.n_colors_spin.setValue(restored_n_colors)
        self.normals_checkbox.setChecked(
            self._setting_to_bool(
                self._settings.value("generate_normals"), DEFAULT_GENERATE_NORMALS)
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

    def _save_viewport_settings(self, prefix: str, panel: MeshViewportPanel) -> None:
        """Persist one viewport display-options block."""
        options = panel.display_options()
        self._settings.setValue(f"{prefix}_show_edges", options.show_edges)
        self._settings.setValue(
            f"{prefix}_edge_color",
            self._rgb_to_hex(options.edge_color),
        )
        self._settings.setValue(f"{prefix}_show_axes", options.show_axes)
        self._settings.setValue(
            f"{prefix}_show_bounding_box",
            options.show_bounding_box,
        )
        self._settings.setValue(
            f"{prefix}_background_preset",
            options.background_preset,
        )
        self._settings.setValue(
            f"{prefix}_lighting_preset",
            options.lighting_preset,
        )
        self._settings.setValue(
            f"{prefix}_lighting_intensity",
            options.lighting_intensity,
        )
        self._settings.setValue(f"{prefix}_camera_preset", options.camera_preset)

    def _save_settings(self) -> None:
        """Persist the current lightweight GUI settings."""
        if self.current_file_path is not None:
            self._settings.setValue(
                "last_file_path", str(self.current_file_path))
            self._settings.setValue("last_field", self._current_field())
        if self._current_bundle is not None:
            self._settings.setValue(
                "last_obj_bundle_path",
                str(self._current_bundle.obj_path),
            )

        self._settings.setValue("colormap", self.colormap_combo.currentText())
        self._settings.setValue("n_colors", self.n_colors_spin.value())
        self._settings.setValue(
            "generate_normals", self.normals_checkbox.isChecked())
        self._save_viewport_settings("volume", self.volume_panel)
        self._save_viewport_settings("bundle", self.bundle_panel)
        self._settings.sync()

    def _apply_default_gui_settings(self) -> None:
        """Apply the built-in default settings to the current session."""
        self.colormap_combo.setCurrentText(DEFAULT_COLORMAP_NAME)
        self.n_colors_spin.setValue(DEFAULT_N_COLORS)
        self.normals_checkbox.setChecked(DEFAULT_GENERATE_NORMALS)
        self.volume_panel.set_display_options(self.VOLUME_DEFAULTS)
        self.bundle_panel.set_display_options(self.BUNDLE_DEFAULTS)

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

    def _last_directory(self, key: str, fallback: Path | None = None) -> str:
        """Return one remembered directory for a file dialog."""
        stored_value = str(self._settings.value(key, "")).strip()
        if stored_value:
            stored_path = Path(stored_value).expanduser()
            if stored_path.exists() and stored_path.is_dir():
                return str(stored_path)

        if fallback is not None:
            fallback_path = fallback.expanduser()
            if fallback_path.is_file():
                fallback_path = fallback_path.parent
            if fallback_path.exists():
                return str(fallback_path.resolve(strict=False))

        return ""

    def _remember_directory(self, key: str, path: str | Path) -> None:
        """Persist the parent directory of one selected file path."""
        selected_path = Path(path).expanduser()
        directory = selected_path.parent if selected_path.suffix else selected_path
        self._settings.setValue(key, str(directory.resolve(strict=False)))

    def _recent_files(self, key: str) -> list[str]:
        """Return the persisted recent-file list for one category."""
        raw_value = self._settings.value(key, [])
        if isinstance(raw_value, str):
            values = [raw_value]
        elif raw_value is None:
            values = []
        else:
            values = list(raw_value)

        recent_files: list[str] = []
        for value in values:
            normalized = str(value).strip()
            if normalized and normalized not in recent_files:
                recent_files.append(normalized)
        return recent_files

    def _set_recent_files(self, key: str, paths: list[str]) -> None:
        """Persist one cleaned recent-file list."""
        self._settings.setValue(key, paths[: self.MAX_RECENT_FILES])

    def _add_recent_file(self, key: str, path: str | Path) -> None:
        """Push one existing file path to the top of a recent-file list."""
        normalized_path = str(Path(path).expanduser().resolve(strict=False))
        recent_files = [
            item for item in self._recent_files(key) if item != normalized_path
        ]
        recent_files.insert(0, normalized_path)
        self._set_recent_files(key, recent_files)
        self._refresh_recent_file_menus()

    def _remove_recent_file(self, key: str, path: str | Path) -> None:
        """Remove one path from a recent-file list."""
        normalized_path = str(Path(path).expanduser().resolve(strict=False))
        recent_files = [
            item for item in self._recent_files(key) if item != normalized_path
        ]
        self._set_recent_files(key, recent_files)
        self._refresh_recent_file_menus()

    def _populate_recent_menu(
        self,
        menu: QtWidgets.QMenu,
        key: str,
        callback: Callable[[str], None],
    ) -> None:
        """Populate one recent-files menu from persisted settings."""
        menu.clear()
        recent_files = self._recent_files(key)
        existing_files: list[str] = []
        for item in recent_files:
            path = Path(item).expanduser().resolve(strict=False)
            if path.is_file():
                existing_files.append(str(path))

        if existing_files != recent_files:
            self._set_recent_files(key, existing_files)

        if not existing_files:
            empty_action = menu.addAction("No recent files")
            empty_action.setEnabled(False)
            return

        for item in existing_files:
            path = Path(item)
            action = menu.addAction(path.name)
            action.setToolTip(item)
            action.setStatusTip(item)
            action.triggered.connect(
                lambda checked=False, selected=item: callback(selected)
            )

    def _refresh_recent_file_menus(self) -> None:
        """Refresh both recent-file menus from persisted settings."""
        if not hasattr(self, "recent_vtu_menu") or not hasattr(self, "recent_obj_menu"):
            return
        self._populate_recent_menu(
            self.recent_vtu_menu,
            "recent_vtu_files",
            self._open_recent_vtu_file,
        )
        self._populate_recent_menu(
            self.recent_obj_menu,
            "recent_obj_files",
            self._open_recent_obj_bundle,
        )

    def _open_recent_vtu_file(self, path: str) -> None:
        """Open one recent VTU file when it still exists."""
        candidate = Path(path).expanduser().resolve(strict=False)
        if not candidate.is_file():
            self._remove_recent_file("recent_vtu_files", candidate)
            self._show_error(f"Recent VTU file not found: {candidate}")
            return
        self.start_load_file_async(candidate, refresh=True)

    def _open_recent_obj_bundle(self, path: str) -> None:
        """Open one recent OBJ bundle when it still exists."""
        candidate = Path(path).expanduser().resolve(strict=False)
        if not candidate.is_file():
            self._remove_recent_file("recent_obj_files", candidate)
            self._show_error(f"Recent OBJ bundle not found: {candidate}")
            return
        self.start_load_obj_bundle_async(candidate)

    def _set_busy_state(self, busy: bool) -> None:
        """Enable or disable user actions while one background task is running."""
        is_dataset_ready = (
            self._current_grid is not None and self.field_combo.count() > 0
        )

        self.open_button.setEnabled(not busy)
        self.open_obj_button.setEnabled(not busy)
        self.open_vtu_action.setEnabled(not busy)
        self.open_obj_action.setEnabled(not busy)
        self.reset_defaults_action.setEnabled(not busy)

        self.field_combo.setEnabled(not busy and is_dataset_ready)
        self.colormap_combo.setEnabled(not busy and is_dataset_ready)
        self.n_colors_spin.setEnabled(not busy and is_dataset_ready)
        self.normals_checkbox.setEnabled(not busy and is_dataset_ready)
        self.vmin_spin.setEnabled(not busy and is_dataset_ready)
        self.vmax_spin.setEnabled(not busy and is_dataset_ready)
        self.reset_range_button.setEnabled(not busy and is_dataset_ready)
        self.refresh_button.setEnabled(not busy and is_dataset_ready)
        self.export_button.setEnabled(not busy and is_dataset_ready)
        self.export_bundle_action.setEnabled(not busy and is_dataset_ready)

        if busy:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _create_progress_dialog(
        self,
        label_text: str,
        maximum: int,
        *,
        subject_path: str | Path | None = None,
        can_cancel: bool = True,
    ) -> _OperationProgressDialog:
        """Create a modal progress dialog for one long-running GUI operation."""
        dialog = _OperationProgressDialog(
            self,
            title=DEFAULT_WINDOW_TITLE,
            label_text=label_text,
            maximum=maximum,
            subject_path=subject_path,
            can_cancel=can_cancel,
        )
        dialog.show()
        QtWidgets.QApplication.processEvents()
        return dialog

    @staticmethod
    def _update_progress(
        dialog: _OperationProgressDialog,
        value: int,
        label_text: str,
    ) -> None:
        """Advance one progress dialog and flush pending UI repaints."""
        dialog.set_message(label_text)
        dialog.set_progress(value)
        QtWidgets.QApplication.processEvents()
        if value < dialog.progress_bar.maximum() and dialog.cancel_requested():
            raise _OperationCancelled("Operation cancelled by the user.")

    @staticmethod
    def _load_file_task(
        path: str | Path,
        *,
        refresh: bool,
        last_field: str,
        colormap: str,
        n_colors: int,
        progress: Callable[[int, str], None],
    ) -> _LoadedFileResult:
        """Load one VTU file and optionally prepare the first volume scene."""
        current_file_path = Path(path).expanduser().resolve(strict=False)
        progress(0, "Reading VTU file...")
        grid = load_unstructured_grid(current_file_path)

        progress(1, "Inspecting dataset arrays...")
        summary = summarize_unstructured_grid(grid, current_file_path)

        progress(2, "Extracting surface mesh...")
        surface = extract_surface(grid, triangulate=True)

        scalar_names = scalar_field_names(summary)
        if not scalar_names:
            raise ValueError(
                "The selected VTU file does not contain scalar point or cell data."
            )

        if last_field and last_field in scalar_names:
            selected_field = last_field
        else:
            selected_field = preferred_scalar_field_name(
                summary,
                preferred_name=DEFAULT_PREFERRED_SCALAR_FIELD_NAME,
            )
            if selected_field is None:
                raise RuntimeError("Failed to resolve a default scalar field.")

        _, scalar_array = resolve_dataset_scalar_field(grid, selected_field)
        field_range = tuple(float(value) for value in scalar_array.GetRange())

        scene = None
        if refresh:
            progress(3, "Building volume preview...")
            scene = build_volume_preview_scene(
                grid,
                selected_field,
                source_path=current_file_path,
                colormap=colormap,
                n_colors=n_colors,
            )

        return _LoadedFileResult(
            current_file_path=current_file_path,
            grid=grid,
            summary=summary,
            surface=surface,
            scalar_names=scalar_names,
            selected_field=selected_field,
            field_range=field_range,
            scene=scene,
        )

    @staticmethod
    def _load_obj_bundle_task(
        path: str | Path,
        *,
        progress: Callable[[int, str], None],
    ) -> _LoadedObjBundleResult:
        """Load one OBJ/MTL/PNG bundle and prepare its preview scene."""
        progress(0, "Resolving OBJ, MTL, and texture files...")
        bundle = resolve_obj_bundle_paths(path)
        progress(1, "Building textured OBJ preview...")
        scene = build_obj_bundle_preview_scene(bundle)
        return _LoadedObjBundleResult(bundle=bundle, scene=scene)

    @staticmethod
    def _export_bundle_task(
        surface: object,
        field_name: str,
        output_prefix: str | Path,
        *,
        colormap: str,
        vmin: float,
        vmax: float,
        n_colors: int,
        generate_normals: bool,
        progress: Callable[[int, str], None],
    ) -> _ExportBundleResult:
        """Export one OBJ bundle and prepare the bundle preview scene."""
        progress(0, "Generating scalar UV coordinates...")
        textured_surface = apply_scalar_uv_map(
            surface,
            field_name,
            vmin=vmin,
            vmax=vmax,
            n_colors=n_colors,
        )

        progress(1, "Building palette texture PNG...")
        texture_image = build_palette_texture(
            colormap,
            n_colors=n_colors,
        )

        progress(2, "Preparing surface for OBJ export...")
        if generate_normals:
            textured_surface = generate_surface_normals(textured_surface)

        progress(3, "Writing OBJ, MTL, and PNG files...")
        bundle = export_obj_bundle(textured_surface, output_prefix, texture_image)

        progress(4, "Building textured preview of the exported bundle...")
        scene = build_obj_bundle_preview_scene(bundle.obj_path)
        return _ExportBundleResult(bundle=bundle, scene=scene)

    def _run_background_task(
        self,
        *,
        title: str,
        maximum: int,
        task_fn: Callable[[Callable[[int, str], None]], object],
        on_success: Callable[[object], None],
    ) -> None:
        """Run one background task and wire its lifecycle to the GUI."""
        if self._active_thread is not None:
            self.statusBar().showMessage(
                "Please wait for the current operation to finish."
            )
            return

        progress_dialog = self._create_progress_dialog(
            title,
            maximum,
            can_cancel=True,
        )
        thread = QtCore.QThread(self)
        worker = _BackgroundTaskWorker(task_fn)
        worker.moveToThread(thread)

        self._active_thread = thread
        self._active_worker = worker
        self._active_progress_dialog = progress_dialog
        self._set_busy_state(True)

        thread.started.connect(worker.run)
        worker.progress.connect(
            lambda value, label: self._update_progress(progress_dialog, value, label)
        )
        worker.succeeded.connect(on_success)
        worker.failed.connect(self._show_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(progress_dialog.close)
        worker.finished.connect(lambda: self._set_busy_state(False))
        worker.finished.connect(lambda: setattr(self, "_active_worker", None))
        worker.finished.connect(lambda: setattr(self, "_active_progress_dialog", None))
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: setattr(self, "_active_thread", None))
        thread.start()

    def _start_deferred_startup_tasks(self) -> None:
        """Kick off any deferred startup loading after the main window appears."""
        startup_file = self._startup_file_path
        startup_bundle = self._startup_bundle_path
        self._startup_file_path = None
        self._startup_bundle_path = None

        if startup_file is not None:
            self.start_load_file_async(
                startup_file,
                refresh=True,
                startup_bundle_path=startup_bundle,
            )
            return

        if startup_bundle is not None:
            self.start_load_obj_bundle_async(startup_bundle)

    def start_load_file_async(
        self,
        path: str | Path,
        *,
        refresh: bool = True,
        startup_bundle_path: str | Path | None = None,
    ) -> None:
        """Defer one VTU load until after the GUI is visible, then run it safely."""
        try:
            self.load_file(path, refresh=refresh, show_progress=True)
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))
            return

        if startup_bundle_path is not None:
            QtCore.QTimer.singleShot(
                0,
                lambda: self.start_load_obj_bundle_async(startup_bundle_path),
            )

    def start_load_obj_bundle_async(self, path: str | Path) -> None:
        """Defer one OBJ bundle load and execute it with GUI feedback."""
        try:
            self.load_obj_bundle(path, show_progress=True)
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def start_export_current_bundle_async(self) -> None:
        """Export the current bundle with progress feedback on the GUI thread."""
        try:
            self.export_current_bundle()
        except (FileNotFoundError, TypeError, ValueError, RuntimeError) as exc:
            self._show_error(str(exc))

    def _handle_loaded_file_result(
        self,
        result: object,
        *,
        startup_bundle_path: str | Path | None = None,
    ) -> None:
        """Apply one completed VTU loading task to the GUI."""
        self._apply_loaded_file_result(result)
        if startup_bundle_path is not None:
            QtCore.QTimer.singleShot(
                0,
                lambda: self.start_load_obj_bundle_async(startup_bundle_path),
            )

    def _apply_loaded_file_result(
        self,
        result: object,
        *,
        preserve_camera_state: dict[str, object] | None = None,
    ) -> None:
        """Apply one file-loading result to the current GUI state."""
        if not isinstance(result, _LoadedFileResult):
            raise TypeError("Unexpected VTU loading result.")

        self.current_file_path = result.current_file_path
        self._current_grid = result.grid
        self._current_summary = result.summary
        self._current_surface = result.surface
        self._current_volume_scene = result.scene

        self.vtu_path_edit.setText(str(self.current_file_path))
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(list(result.scalar_names))
        self.field_combo.setCurrentText(result.selected_field)
        self.field_combo.blockSignals(False)
        self.vmin_spin.setValue(result.field_range[0])
        self.vmax_spin.setValue(result.field_range[1])
        self._set_controls_enabled(True)
        self._remember_directory("last_vtu_directory", self.current_file_path)
        self._add_recent_file("recent_vtu_files", self.current_file_path)

        if result.scene is not None:
            self.volume_panel.set_scene(
                result.scene,
                preserve_camera_state=preserve_camera_state,
            )

        self.statusBar().showMessage(f"Loaded {self.current_file_path.name}")
        self._save_settings()

    def _handle_loaded_obj_bundle_result(self, result: object) -> None:
        """Apply one completed OBJ loading task to the GUI."""
        if not isinstance(result, _LoadedObjBundleResult):
            raise TypeError("Unexpected OBJ bundle loading result.")

        self._current_bundle = result.bundle
        self._current_bundle_scene = result.scene
        self.obj_path_edit.setText(str(result.bundle.obj_path))
        self.bundle_panel.set_scene(result.scene)
        self._update_texture_preview(
            result.bundle.texture_path,
            result.scene.info.texture_size if result.scene.info is not None else None,
        )
        self._remember_directory("last_obj_bundle_directory", result.bundle.obj_path)
        self._add_recent_file("recent_obj_files", result.bundle.obj_path)
        self.statusBar().showMessage(f"Loaded OBJ bundle {result.bundle.obj_path.name}")
        self._save_settings()

    def _handle_export_result(self, result: object) -> None:
        """Apply one completed export task to the GUI."""
        if not isinstance(result, _ExportBundleResult):
            raise TypeError("Unexpected export result.")

        self._current_bundle = result.bundle
        self._current_bundle_scene = result.scene
        self.obj_path_edit.setText(str(result.bundle.obj_path))
        self.bundle_panel.set_scene(result.scene)
        self._update_texture_preview(
            result.bundle.texture_path,
            result.scene.info.texture_size if result.scene.info is not None else None,
        )
        self._remember_directory("last_export_directory", result.bundle.obj_path)
        self._remember_directory("last_obj_bundle_directory", result.bundle.obj_path)
        self._add_recent_file("recent_obj_files", result.bundle.obj_path)
        self.statusBar().showMessage(
            f"Exported bundle to {result.bundle.obj_path.parent}"
        )
        QtWidgets.QMessageBox.information(
            self,
            "Export complete",
            "\n".join(
                [
                    f"OBJ: {result.bundle.obj_path}",
                    f"MTL: {result.bundle.mtl_path}",
                    f"PNG: {result.bundle.texture_path}",
                ]
            ),
        )
        self._save_settings()

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

    def show_qsettings_dialog(self) -> None:
        """Show a dialog listing all QSettings values and the storage path."""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("QSettings")
        dialog.resize(640, 480)

        layout = QtWidgets.QVBoxLayout(dialog)

        storage_path = self._settings.fileName()
        path_label = QtWidgets.QLabel(f"<b>Storage file:</b> {storage_path}")
        path_label.setWordWrap(True)
        path_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(path_label)

        table = QtWidgets.QTableWidget(dialog)
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Key", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)

        keys = self._settings.allKeys()
        table.setRowCount(len(keys))
        for row, key in enumerate(sorted(keys)):
            value = self._settings.value(key)
            if isinstance(value, list):
                display = "[" + ", ".join(str(v) for v in value) + "]"
            elif isinstance(value, bool):
                display = "true" if value else "false"
            else:
                display = str(value)
            table.setItem(row, 0, QtWidgets.QTableWidgetItem(key))
            table.setItem(row, 1, QtWidgets.QTableWidgetItem(display))
        table.resizeColumnToContents(0)

        layout.addWidget(table)

        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.exec_()

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
            self._last_directory("last_vtu_directory", self.current_file_path),
            "VTU Files (*.vtu);;All Files (*)",
        )
        if not file_name:
            return
        self.start_load_file_async(file_name, refresh=True)

    def open_obj_bundle_dialog(self) -> None:
        """Prompt the user for an OBJ bundle and load it into the right viewport."""
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open OBJ bundle",
            self._last_directory(
                "last_obj_bundle_directory",
                self._current_bundle.obj_path
                if self._current_bundle is not None
                else None,
            ),
            "OBJ Files (*.obj);;All Files (*)",
        )
        if not file_name:
            return
        self.start_load_obj_bundle_async(file_name)

    def load_file(
        self,
        path: str | Path,
        *,
        refresh: bool = True,
        show_progress: bool = True,
    ) -> None:
        """Load a VTU file, populate controls, and optionally refresh the view."""
        progress_dialog = (
            self._create_progress_dialog(
                "Loading VTU file...",
                4 if refresh else 3,
                subject_path=path,
                can_cancel=True,
            )
            if show_progress
            else None
        )
        try:
            result = self._load_file_task(
                path,
                refresh=refresh,
                last_field=str(self._settings.value("last_field", "")).strip(),
                colormap=self.colormap_combo.currentText(),
                n_colors=self.n_colors_spin.value(),
                progress=(
                    lambda value, label: self._update_progress(
                        progress_dialog,
                        value,
                        label,
                    )
                )
                if progress_dialog is not None
                else (lambda value, label: None),
            )
            self._apply_loaded_file_result(result)
            if progress_dialog is not None:
                self._update_progress(
                    progress_dialog,
                    progress_dialog.maximum(),
                    "VTU file loaded.",
                )
        except _OperationCancelled:
            self.statusBar().showMessage("VTU loading cancelled.")
        finally:
            if progress_dialog is not None:
                progress_dialog.close()

    def load_obj_bundle(
        self,
        path: str | Path,
        *,
        show_progress: bool = True,
    ) -> None:
        """Load an OBJ/MTL/PNG bundle into the right viewport."""
        progress_dialog = (
            self._create_progress_dialog(
                "Loading OBJ bundle...",
                2,
                subject_path=path,
                can_cancel=True,
            )
            if show_progress
            else None
        )
        try:
            result = self._load_obj_bundle_task(
                path,
                progress=(
                    lambda value, label: self._update_progress(
                        progress_dialog,
                        value,
                        label,
                    )
                )
                if progress_dialog is not None
                else (lambda value, label: None),
            )
            self._handle_loaded_obj_bundle_result(result)
            if progress_dialog is not None:
                self._update_progress(progress_dialog, 2, "OBJ bundle loaded.")
        except _OperationCancelled:
            self.statusBar().showMessage("OBJ loading cancelled.")
        finally:
            if progress_dialog is not None:
                progress_dialog.close()

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
            camera_state = self.volume_panel.camera_state()
            scene = build_volume_preview_scene(
                self._current_grid,
                self._current_field(),
                source_path=self.current_file_path,
                **self._current_mapping_kwargs(),
            )
            self._current_volume_scene = scene
            self.volume_panel.set_scene(
                scene,
                preserve_camera_state=camera_state,
            )
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
        initial_directory = self._last_directory(
            "last_export_directory",
            self.current_file_path,
        )
        initial_path = (
            str(Path(initial_directory) / suggested_name)
            if initial_directory
            else suggested_name
        )
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export OBJ bundle",
            initial_path,
            "OBJ Files (*.obj);;All Files (*)",
        )
        if not file_name:
            return

        progress_dialog = self._create_progress_dialog(
            "Exporting OBJ bundle...",
            5,
            subject_path=file_name,
            can_cancel=True,
        )
        try:
            output_prefix = Path(file_name).with_suffix("")
            mapping_kwargs = self._current_mapping_kwargs()
            result = self._export_bundle_task(
                self._current_surface,
                self._current_field(),
                output_prefix,
                colormap=str(mapping_kwargs["colormap"]),
                vmin=float(mapping_kwargs["vmin"]),
                vmax=float(mapping_kwargs["vmax"]),
                n_colors=int(mapping_kwargs["n_colors"]),
                generate_normals=self.normals_checkbox.isChecked(),
                progress=lambda value, label: self._update_progress(
                    progress_dialog,
                    value,
                    label,
                ),
            )
            self._handle_export_result(result)
            self._update_progress(progress_dialog, 5, "Export complete.")
        except _OperationCancelled:
            self.statusBar().showMessage("OBJ export cancelled.")
        finally:
            progress_dialog.close()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        """Persist settings when the window closes."""
        self._save_settings()
        self.volume_panel.shutdown()
        self.bundle_panel.shutdown()
        super().closeEvent(event)
