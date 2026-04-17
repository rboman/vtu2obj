"""Reusable Qt panel that combines one VTK view with display and info controls."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

from ..defaults import (
    BACKGROUND_PRESET_LABELS,
    CAMERA_PRESET_LABELS,
    LIGHTING_PRESET_LABELS,
)
from ..model import MeshInfo, ViewDisplayOptions
from ..preview import PreviewScene
from .vtk_view import VtkView


def _rgb_to_qcolor(color: tuple[float, float, float]) -> QtGui.QColor:
    """Convert one normalized RGB triplet to a Qt color."""
    return QtGui.QColor.fromRgbF(*color)


def _qcolor_to_rgb(color: QtGui.QColor) -> tuple[float, float, float]:
    """Convert one Qt color to a normalized RGB triplet."""
    return (color.redF(), color.greenF(), color.blueF())


class MeshViewportPanel(QtWidgets.QWidget):
    """Bundle one VTK viewport with per-view display controls and mesh info."""

    def __init__(
        self,
        title: str,
        *,
        default_display_options: ViewDisplayOptions,
        enable_vtk_view: bool = True,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._scene: PreviewScene | None = None
        self._info: MeshInfo | None = None
        self._edge_color = _rgb_to_qcolor(default_display_options.edge_color)
        self.vtk_view: VtkView | None = None

        self._build_ui(title, enable_vtk_view)
        self.set_display_options(default_display_options)
        self.set_info(None)

    @property
    def scene(self) -> PreviewScene | None:
        """Return the current scene displayed by the panel."""
        return self._scene

    def _build_ui(self, title: str, enable_vtk_view: bool) -> None:
        """Create the panel widgets."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QtWidgets.QLabel(title)
        title_font = self.title_label.font()
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setToolTip(
            f"This panel displays the {title.lower()} and its dedicated controls."
        )
        layout.addWidget(self.title_label)

        if enable_vtk_view:
            self.vtk_view = VtkView(self)
            layout.addWidget(self.vtk_view, stretch=1)
        else:
            self.placeholder_label = QtWidgets.QLabel(
                "VTK preview widget disabled for this session."
            )
            self.placeholder_label.setAlignment(QtCore.Qt.AlignCenter)
            self.placeholder_label.setMinimumHeight(240)
            self.placeholder_label.setToolTip(
                "The embedded VTK viewport is disabled in this session, usually for a "
                "headless automated test."
            )
            layout.addWidget(self.placeholder_label, stretch=1)

        self.tabs = QtWidgets.QTabWidget(self)
        self.tabs.setToolTip(
            "Use these tabs to configure the viewport overlays or inspect the mesh "
            "information shown in this panel."
        )
        layout.addWidget(self.tabs)

        display_tab = QtWidgets.QWidget(self.tabs)
        display_layout = QtWidgets.QVBoxLayout(display_tab)

        self.show_edges_checkbox = QtWidgets.QCheckBox("Show mesh edges")
        self.show_edges_checkbox.setToolTip(
            "Overlay the extracted mesh edges on top of the rendered geometry for "
            "this viewport only."
        )
        self.show_axes_checkbox = QtWidgets.QCheckBox("Show XYZ trihedron")
        self.show_axes_checkbox.setToolTip(
            "Display the orientation trihedron in the lower-left corner of this "
            "viewport."
        )
        self.show_bounding_box_checkbox = QtWidgets.QCheckBox(
            "Show graduated bounding box"
        )
        self.show_bounding_box_checkbox.setToolTip(
            "Display a graduated bounding box with axis ticks around the currently "
            "displayed mesh."
        )

        for checkbox in (
            self.show_edges_checkbox,
            self.show_axes_checkbox,
            self.show_bounding_box_checkbox,
        ):
            checkbox.toggled.connect(self._apply_display_options)
            display_layout.addWidget(checkbox)

        edge_color_row = QtWidgets.QHBoxLayout()
        edge_color_label = QtWidgets.QLabel("Edge color")
        edge_color_label.setToolTip(
            "The edge color applies only to the edge overlay of this viewport."
        )
        self.edge_color_button = QtWidgets.QPushButton()
        self.edge_color_button.clicked.connect(self.choose_edge_color)
        self.edge_color_button.setToolTip(
            "Choose the color used to draw the mesh-edge overlay in this viewport."
        )
        edge_color_row.addWidget(edge_color_label)
        edge_color_row.addStretch(1)
        edge_color_row.addWidget(self.edge_color_button)
        display_layout.addLayout(edge_color_row)

        background_row = QtWidgets.QHBoxLayout()
        background_label = QtWidgets.QLabel("Background")
        self.background_combo = QtWidgets.QComboBox()
        for key, label in BACKGROUND_PRESET_LABELS.items():
            self.background_combo.addItem(label, key)
        self.background_combo.currentIndexChanged.connect(self._apply_display_options)
        background_label.setToolTip(
            "Choose the renderer background preset for this viewport."
        )
        self.background_combo.setToolTip(background_label.toolTip())
        background_row.addWidget(background_label)
        background_row.addStretch(1)
        background_row.addWidget(self.background_combo)
        display_layout.addLayout(background_row)

        lighting_row = QtWidgets.QHBoxLayout()
        lighting_label = QtWidgets.QLabel("Lights")
        self.lighting_combo = QtWidgets.QComboBox()
        for key, label in LIGHTING_PRESET_LABELS.items():
            self.lighting_combo.addItem(label, key)
        self.lighting_combo.currentIndexChanged.connect(self._apply_display_options)
        lighting_label.setToolTip(
            "Choose a lighting preset designed for this viewport."
        )
        self.lighting_combo.setToolTip(lighting_label.toolTip())
        lighting_row.addWidget(lighting_label)
        lighting_row.addStretch(1)
        lighting_row.addWidget(self.lighting_combo)
        display_layout.addLayout(lighting_row)

        intensity_row = QtWidgets.QHBoxLayout()
        intensity_label = QtWidgets.QLabel("Intensity")
        self.lighting_intensity_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.lighting_intensity_slider.setRange(0, 200)
        self.lighting_intensity_slider.setSingleStep(5)
        self.lighting_intensity_slider.valueChanged.connect(self._apply_display_options)
        self.lighting_intensity_value = QtWidgets.QLabel("100%")
        self.lighting_intensity_slider.valueChanged.connect(
            lambda value: self.lighting_intensity_value.setText(f"{value}%")
        )
        intensity_label.setToolTip(
            "Scale the strength of the current lighting preset."
        )
        self.lighting_intensity_slider.setToolTip(intensity_label.toolTip())
        intensity_row.addWidget(intensity_label)
        intensity_row.addWidget(self.lighting_intensity_slider, stretch=1)
        intensity_row.addWidget(self.lighting_intensity_value)
        display_layout.addLayout(intensity_row)

        camera_row = QtWidgets.QHBoxLayout()
        camera_label = QtWidgets.QLabel("Camera")
        self.camera_preset_combo = QtWidgets.QComboBox()
        for key, label in CAMERA_PRESET_LABELS.items():
            self.camera_preset_combo.addItem(label, key)
        self.camera_apply_button = QtWidgets.QPushButton("Apply")
        self.camera_apply_button.clicked.connect(self.apply_camera_preset)
        camera_label.setToolTip(
            "Choose a predefined camera orientation for this viewport."
        )
        self.camera_preset_combo.setToolTip(camera_label.toolTip())
        self.camera_apply_button.setToolTip(
            "Apply the selected predefined camera orientation."
        )
        camera_row.addWidget(camera_label)
        camera_row.addStretch(1)
        camera_row.addWidget(self.camera_preset_combo)
        camera_row.addWidget(self.camera_apply_button)
        display_layout.addLayout(camera_row)

        display_layout.addStretch(1)
        self.tabs.addTab(display_tab, "Display")

        info_tab = QtWidgets.QWidget(self.tabs)
        info_layout = QtWidgets.QVBoxLayout(info_tab)
        self.info_text_edit = QtWidgets.QPlainTextEdit(info_tab)
        self.info_text_edit.setReadOnly(True)
        self.info_text_edit.setToolTip(
            "Read-only technical summary of the mesh displayed in this viewport: "
            "topology, arrays, UVs, normals, and texture state."
        )
        info_layout.addWidget(self.info_text_edit)
        self.tabs.addTab(info_tab, "Info")

    def display_options(self) -> ViewDisplayOptions:
        """Return the display options currently selected in the UI."""
        return ViewDisplayOptions(
            show_edges=self.show_edges_checkbox.isChecked(),
            edge_color=_qcolor_to_rgb(self._edge_color),
            show_axes=self.show_axes_checkbox.isChecked(),
            show_bounding_box=self.show_bounding_box_checkbox.isChecked(),
            background_preset=self.background_combo.currentData(),
            lighting_preset=self.lighting_combo.currentData(),
            lighting_intensity=self.lighting_intensity_slider.value(),
            camera_preset=self.camera_preset_combo.currentData(),
        )

    def set_display_options(self, options: ViewDisplayOptions) -> None:
        """Update the display controls and push them to the VTK view."""
        for checkbox, value in (
            (self.show_edges_checkbox, options.show_edges),
            (self.show_axes_checkbox, options.show_axes),
            (self.show_bounding_box_checkbox, options.show_bounding_box),
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(value)
            checkbox.blockSignals(False)

        self._edge_color = _rgb_to_qcolor(options.edge_color)
        self._refresh_edge_color_button()

        self.background_combo.blockSignals(True)
        self.background_combo.setCurrentIndex(
            self.background_combo.findData(options.background_preset)
        )
        self.background_combo.blockSignals(False)

        self.lighting_combo.blockSignals(True)
        self.lighting_combo.setCurrentIndex(
            self.lighting_combo.findData(options.lighting_preset)
        )
        self.lighting_combo.blockSignals(False)

        self.lighting_intensity_slider.blockSignals(True)
        self.lighting_intensity_slider.setValue(options.lighting_intensity)
        self.lighting_intensity_slider.blockSignals(False)
        self.lighting_intensity_value.setText(f"{options.lighting_intensity}%")

        self.camera_preset_combo.blockSignals(True)
        self.camera_preset_combo.setCurrentIndex(
            self.camera_preset_combo.findData(options.camera_preset)
        )
        self.camera_preset_combo.blockSignals(False)

        self._apply_display_options()

    def camera_state(self) -> dict[str, object] | None:
        """Return the current camera state when the VTK view is active."""
        if self.vtk_view is None:
            return None
        return self.vtk_view.camera_state()

    def set_scene(
        self,
        scene: PreviewScene,
        *,
        preserve_camera_state: dict[str, object] | None = None,
    ) -> None:
        """Display a new preview scene in the panel."""
        self._scene = scene
        if self.vtk_view is not None:
            self.vtk_view.set_scene(
                scene,
                preserve_camera_state=preserve_camera_state,
            )
        self.set_info(scene.info)

    def clear_scene(self) -> None:
        """Reset the panel to an empty state."""
        self._scene = None
        if self.vtk_view is not None:
            self.vtk_view.clear_scene()
        self.set_info(None)

    def shutdown(self) -> None:
        """Release the VTK resources owned by this panel, when any."""
        if self.vtk_view is not None:
            self.vtk_view.shutdown()

    def set_info(self, info: MeshInfo | None) -> None:
        """Display the current mesh information summary."""
        self._info = info
        if info is None:
            self.info_text_edit.setPlainText("No mesh loaded.")
            return
        self.info_text_edit.setPlainText("\n".join(info.as_lines()))

    def choose_edge_color(self) -> None:
        """Prompt the user for a new edge color."""
        color = QtWidgets.QColorDialog.getColor(
            self._edge_color,
            self,
            "Choose edge color",
        )
        if not color.isValid():
            return
        self._edge_color = color
        self._refresh_edge_color_button()
        self._apply_display_options()

    def apply_camera_preset(self) -> None:
        """Apply the currently selected camera preset to the VTK view."""
        if self.vtk_view is None:
            return
        self.vtk_view.apply_camera_preset(self.camera_preset_combo.currentData())

    def _refresh_edge_color_button(self) -> None:
        """Update the edge-color button text, icon, and swatch."""
        swatch = QtGui.QPixmap(18, 18)
        swatch.fill(self._edge_color)
        self.edge_color_button.setIcon(QtGui.QIcon(swatch))
        self.edge_color_button.setText(self._edge_color.name().upper())
        self.edge_color_button.setStyleSheet(
            "QPushButton {"
            f"background-color: {self._edge_color.name()};"
            f"color: {'#000000' if self._edge_color.lightness() > 128 else '#FFFFFF'};"
            "padding-left: 6px; padding-right: 6px;"
            "}"
        )

    def _apply_display_options(self) -> None:
        """Push the current display settings to the VTK widget."""
        if self.vtk_view is None:
            return
        self.vtk_view.set_display_options(self.display_options())
