"""Embedded VTK view used by the Qt GUI."""

from __future__ import annotations

import vtk
from PyQt5 import QtCore
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from ..model import ViewDisplayOptions
from ..preview import PreviewScene


class VtkView(QVTKRenderWindowInteractor):
    """Embed one configurable VTK renderer inside the Qt GUI."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._scene: PreviewScene | None = None
        self._display_options = ViewDisplayOptions(
            show_edges=False,
            edge_color=(0.82, 0.84, 0.88),
            show_axes=True,
        )
        self._renderer = vtk.vtkRenderer()

        render_window = self.GetRenderWindow()
        render_window.AddRenderer(self._renderer)
        render_window.SetMultiSamples(0)
        self.Initialize()

        self._interactor = render_window.GetInteractor()
        if self._interactor is not None:
            self._interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

        self._axes_actor = vtk.vtkAxesActor()
        self._axes_widget: vtk.vtkOrientationMarkerWidget | None = None
        self._rebuild_axes_widget()

    @property
    def scene(self) -> PreviewScene | None:
        """Return the currently displayed scene, if any."""
        return self._scene

    @property
    def display_options(self) -> ViewDisplayOptions:
        """Return the active display options."""
        return self._display_options

    def set_display_options(self, options: ViewDisplayOptions) -> None:
        """Update the view overlays without rebuilding the whole scene."""
        self._display_options = options
        self._apply_display_options()

    def set_scene(self, scene: PreviewScene) -> None:
        """Replace the currently displayed preview scene."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        render_window.AddRenderer(scene.renderer)
        self._renderer = scene.renderer
        self._scene = scene

        if self._interactor is not None:
            self._interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

        self._rebuild_axes_widget()

        self._apply_display_options()
        QtCore.QTimer.singleShot(0, self._apply_display_options)

    def clear_scene(self) -> None:
        """Reset the embedded view to an empty renderer."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        self._renderer = vtk.vtkRenderer()
        render_window.AddRenderer(self._renderer)
        self._scene = None

        self._rebuild_axes_widget()

        self._apply_display_options()

    def shutdown(self) -> None:
        """Release the VTK resources held by the embedded Qt widget."""
        try:
            if self._axes_widget is not None:
                self._axes_widget.SetEnabled(0)
        except RuntimeError:
            pass
        self._axes_widget = None

        render_window = self.GetRenderWindow()
        if render_window is not None:
            try:
                render_window.GetRenderers().RemoveAllItems()
            except RuntimeError:
                pass
            try:
                render_window.Finalize()
            except RuntimeError:
                pass

        try:
            self.Finalize()
        except RuntimeError:
            pass

    def closeEvent(self, event) -> None:
        """Shut down the VTK render window before Qt destroys the widget."""
        self.shutdown()
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        """Re-sync overlays once the native Qt widget becomes visible."""
        super().showEvent(event)
        self._apply_display_options()
        QtCore.QTimer.singleShot(0, self._apply_display_options)

    def _sync_axes_widget(self) -> None:
        """Synchronize the orientation marker widget with the current state."""
        if self._interactor is None or self._axes_widget is None:
            return

        if self._display_options.show_axes:
            self._axes_widget.EnabledOn()
            self._axes_widget.InteractiveOff()
            self._axes_widget.KeyPressActivationOff()
        else:
            self._axes_widget.EnabledOff()

    def _rebuild_axes_widget(self) -> None:
        """Create a fresh orientation-marker widget bound to the current renderer."""
        if self._interactor is None:
            return

        if self._axes_widget is not None:
            try:
                self._axes_widget.SetEnabled(0)
            except RuntimeError:
                pass

        self._axes_widget = vtk.vtkOrientationMarkerWidget()
        self._axes_widget.SetOrientationMarker(self._axes_actor)
        self._axes_widget.SetInteractor(self._interactor)
        self._axes_widget.SetViewport(0.0, 0.0, 0.20, 0.20)
        self._axes_widget.KeyPressActivationOff()
        if hasattr(self._axes_widget, "SetDefaultRenderer"):
            self._axes_widget.SetDefaultRenderer(self._renderer)
        if hasattr(self._axes_widget, "SetCurrentRenderer"):
            self._axes_widget.SetCurrentRenderer(self._renderer)

    def _apply_display_options(self) -> None:
        """Apply edge and axis settings to the current scene."""
        if self._scene is not None and self._scene.edge_actor is not None:
            edge_actor = self._scene.edge_actor
            edge_actor.SetVisibility(self._display_options.show_edges)
            edge_actor.GetProperty().SetColor(*self._display_options.edge_color)

        self._sync_axes_widget()
        render_window = self.GetRenderWindow()
        if render_window is not None:
            render_window.Render()
