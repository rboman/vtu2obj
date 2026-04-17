"""VTK widget placeholder for the future GUI."""

from __future__ import annotations

import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from ..preview import PreviewScene


class VtkView(QVTKRenderWindowInteractor):
    """Embed a VTK renderer inside the Qt GUI."""

    def __init__(self, parent: object | None = None) -> None:
        super().__init__(parent)
        self._scene: PreviewScene | None = None
        self._renderer = vtk.vtkRenderer()
        render_window = self.GetRenderWindow()
        render_window.AddRenderer(self._renderer)
        render_window.SetMultiSamples(0)
        self.Initialize()

    @property
    def scene(self) -> PreviewScene | None:
        """Return the currently displayed scene, if any."""
        return self._scene

    def set_scene(self, scene: PreviewScene) -> None:
        """Replace the currently displayed preview scene."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        render_window.AddRenderer(scene.renderer)
        self._renderer = scene.renderer
        self._scene = scene
        render_window.Render()

    def clear_scene(self) -> None:
        """Reset the embedded view to an empty renderer."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        self._renderer = vtk.vtkRenderer()
        render_window.AddRenderer(self._renderer)
        self._scene = None
        render_window.Render()
