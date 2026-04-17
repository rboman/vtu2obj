"""Reusable Qt panel that combines one VTK view with display and info controls."""

from __future__ import annotations

from PyQt5 import QtCore, QtGui, QtWidgets

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
        self.edge_color_button = QtWidgets.QPushButton()
        self.edge_color_button.clicked.connect(self.choose_edge_color)
        self.edge_color_button.setToolTip(
            "Choose the color used to draw the mesh-edge overlay in this viewport."
        )
        self.show_edges_checkbox.toggled.connect(self._apply_display_options)
        self.show_axes_checkbox.toggled.connect(self._apply_display_options)

        display_layout.addWidget(self.show_edges_checkbox)
        display_layout.addWidget(self.show_axes_checkbox)
        edge_color_label = QtWidgets.QLabel("Edge color")
        edge_color_label.setToolTip(
            "The edge color applies only to the edge overlay of this viewport."
        )
        display_layout.addWidget(edge_color_label)
        display_layout.addWidget(self.edge_color_button)
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
        )

    def set_display_options(self, options: ViewDisplayOptions) -> None:
        """Update the display controls and push them to the VTK view."""
        for checkbox, value in (
            (self.show_edges_checkbox, options.show_edges),
            (self.show_axes_checkbox, options.show_axes),
        ):
            checkbox.blockSignals(True)
            checkbox.setChecked(value)
            checkbox.blockSignals(False)

        self._edge_color = _rgb_to_qcolor(options.edge_color)
        self._refresh_edge_color_button()
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

    def _refresh_edge_color_button(self) -> None:
        """Update the edge-color button text and swatch."""
        self.edge_color_button.setText(self._edge_color.name().upper())
        self.edge_color_button.setStyleSheet(
            "QPushButton {"
            f"background-color: {self._edge_color.name()};"
            f"color: {'#000000' if self._edge_color.lightness() > 128 else '#FFFFFF'};"
            "}"
        )

    def _apply_display_options(self) -> None:
        """Push the current display settings to the VTK widget."""
        if self.vtk_view is None:
            return
        self.vtk_view.set_display_options(self.display_options())
