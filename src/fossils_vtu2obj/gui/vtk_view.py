"""Embedded VTK view used by the Qt GUI."""

from __future__ import annotations

import math

import vtk
from PyQt5 import QtCore
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from ..defaults import (
    DEFAULT_BACKGROUND_PRESET,
    DEFAULT_CAMERA_PRESET,
    DEFAULT_LIGHTING_INTENSITY,
    DEFAULT_LIGHTING_PRESET,
    DEFAULT_RENDERER_BACKGROUND,
    DEFAULT_RENDERER_BACKGROUND_2,
    DEFAULT_TRIHEDRON_VIEWPORT,
    PARAVIEW_DARK_GRADIENT_BACKGROUND,
    PARAVIEW_DARK_GRADIENT_BACKGROUND_2,
)
from ..model import CameraPreset, ViewDisplayOptions
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
            show_bounding_box=False,
            background_preset=DEFAULT_BACKGROUND_PRESET,
            lighting_preset=DEFAULT_LIGHTING_PRESET,
            lighting_intensity=DEFAULT_LIGHTING_INTENSITY,
            camera_preset=DEFAULT_CAMERA_PRESET,
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

        self._cube_axes_actor = vtk.vtkCubeAxesActor()
        self._configure_cube_axes_actor()

        self._rebuild_axes_widget()
        self._apply_background_preset()
        self._rebuild_lights()

    @property
    def scene(self) -> PreviewScene | None:
        """Return the currently displayed scene, if any."""
        return self._scene

    @property
    def display_options(self) -> ViewDisplayOptions:
        """Return the active display options."""
        return self._display_options

    def camera_state(self) -> dict[str, object] | None:
        """Capture the current camera state for later restoration."""
        if self._scene is None:
            return None

        camera = self._renderer.GetActiveCamera()
        return {
            "position": tuple(camera.GetPosition()),
            "focal_point": tuple(camera.GetFocalPoint()),
            "view_up": tuple(camera.GetViewUp()),
            "clipping_range": tuple(camera.GetClippingRange()),
            "parallel_scale": float(camera.GetParallelScale()),
            "view_angle": float(camera.GetViewAngle()),
            "parallel_projection": bool(camera.GetParallelProjection()),
        }

    def set_display_options(self, options: ViewDisplayOptions) -> None:
        """Update the view overlays and renderer configuration."""
        self._display_options = options
        self._apply_display_options()

    def set_scene(
        self,
        scene: PreviewScene,
        *,
        preserve_camera_state: dict[str, object] | None = None,
    ) -> None:
        """Replace the currently displayed preview scene."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        render_window.AddRenderer(scene.renderer)
        self._renderer = scene.renderer
        self._scene = scene

        if self._interactor is not None:
            self._interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

        self._attach_cube_axes_actor()
        self._rebuild_axes_widget()

        if preserve_camera_state is not None:
            self._restore_camera_state(preserve_camera_state)

        self._apply_display_options()
        QtCore.QTimer.singleShot(0, self._apply_display_options)

    def clear_scene(self) -> None:
        """Reset the embedded view to an empty renderer."""
        render_window = self.GetRenderWindow()
        render_window.GetRenderers().RemoveAllItems()
        self._renderer = vtk.vtkRenderer()
        render_window.AddRenderer(self._renderer)
        self._scene = None

        self._attach_cube_axes_actor()
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

    def apply_camera_preset(self, preset_name: CameraPreset) -> None:
        """Apply one named camera orientation to the current scene."""
        if self._scene is None:
            return

        bounds = self._scene.surface.GetBounds()
        if bounds is None:
            return

        center = (
            0.5 * (bounds[0] + bounds[1]),
            0.5 * (bounds[2] + bounds[3]),
            0.5 * (bounds[4] + bounds[5]),
        )
        extent_x = bounds[1] - bounds[0]
        extent_y = bounds[3] - bounds[2]
        extent_z = bounds[5] - bounds[4]
        diagonal = math.sqrt(extent_x**2 + extent_y**2 + extent_z**2)
        distance = max(diagonal * 1.8, max(extent_x, extent_y, extent_z) * 3.0, 1.0)

        direction_map: dict[
            CameraPreset,
            tuple[tuple[float, float, float], tuple[float, float, float]],
        ] = {
            "3d_angled": ((1.35, -1.15, 0.90), (0.0, 0.0, 1.0)),
            "+X": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            "-X": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
            "+Y": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            "-Y": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
            "+Z": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
            "-Z": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        }
        direction, view_up = direction_map[preset_name]
        norm = math.sqrt(sum(component * component for component in direction))
        scaled_direction = tuple(distance * component / norm for component in direction)

        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint(*center)
        camera.SetPosition(
            center[0] + scaled_direction[0],
            center[1] + scaled_direction[1],
            center[2] + scaled_direction[2],
        )
        camera.SetViewUp(*view_up)
        camera.OrthogonalizeViewUp()
        self._renderer.ResetCameraClippingRange()
        self._cube_axes_actor.SetCamera(camera)
        self.GetRenderWindow().Render()

    def closeEvent(self, event) -> None:
        """Shut down the VTK render window before Qt destroys the widget."""
        self.shutdown()
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        """Re-sync overlays once the native Qt widget becomes visible."""
        super().showEvent(event)
        self._apply_display_options()
        QtCore.QTimer.singleShot(0, self._apply_display_options)

    def _attach_cube_axes_actor(self) -> None:
        """Attach the cube-axes actor to the current renderer."""
        if self._renderer.HasViewProp(self._cube_axes_actor) == 0:
            self._renderer.AddViewProp(self._cube_axes_actor)

    def _configure_cube_axes_actor(self) -> None:
        """Configure the bounding-box actor used in the display options."""
        self._cube_axes_actor.SetFlyModeToStaticEdges()
        self._cube_axes_actor.DrawXGridlinesOn()
        self._cube_axes_actor.DrawYGridlinesOn()
        self._cube_axes_actor.DrawZGridlinesOn()
        self._cube_axes_actor.XAxisMinorTickVisibilityOff()
        self._cube_axes_actor.YAxisMinorTickVisibilityOff()
        self._cube_axes_actor.ZAxisMinorTickVisibilityOff()
        if hasattr(self._cube_axes_actor, "SetLabelFormat"):
            self._cube_axes_actor.SetLabelFormat("%-#6.3g")
        else:
            for axis_name in ("X", "Y", "Z"):
                setter = getattr(
                    self._cube_axes_actor,
                    f"Set{axis_name}LabelFormat",
                    None,
                )
                if setter is not None:
                    setter("%-#6.3g")
        self._cube_axes_actor.SetScreenSize(8.0)
        self._cube_axes_actor.SetVisibility(False)

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

    def _sync_cube_axes_actor(self) -> None:
        """Synchronize the cube-axes actor with the current scene and display state."""
        if self._scene is None:
            self._cube_axes_actor.SetVisibility(False)
            return

        self._cube_axes_actor.SetBounds(self._scene.surface.GetBounds())
        self._cube_axes_actor.SetCamera(self._renderer.GetActiveCamera())
        self._cube_axes_actor.SetVisibility(self._display_options.show_bounding_box)
        label_color = (0.85, 0.87, 0.90)
        if self._display_options.background_preset == "white":
            label_color = (0.15, 0.15, 0.18)
        for text_property in (
            self._cube_axes_actor.GetTitleTextProperty(0),
            self._cube_axes_actor.GetTitleTextProperty(1),
            self._cube_axes_actor.GetTitleTextProperty(2),
            self._cube_axes_actor.GetLabelTextProperty(0),
            self._cube_axes_actor.GetLabelTextProperty(1),
            self._cube_axes_actor.GetLabelTextProperty(2),
        ):
            text_property.SetColor(*label_color)

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
        self._axes_widget.SetViewport(*DEFAULT_TRIHEDRON_VIEWPORT)
        self._axes_widget.KeyPressActivationOff()
        if hasattr(self._axes_widget, "SetDefaultRenderer"):
            self._axes_widget.SetDefaultRenderer(self._renderer)
        if hasattr(self._axes_widget, "SetCurrentRenderer"):
            self._axes_widget.SetCurrentRenderer(self._renderer)

    def _apply_display_options(self) -> None:
        """Apply overlays, background, and lighting to the current scene."""
        if self._scene is not None and self._scene.edge_actor is not None:
            edge_actor = self._scene.edge_actor
            edge_actor.SetVisibility(self._display_options.show_edges)
            edge_actor.GetProperty().SetColor(*self._display_options.edge_color)

        self._apply_background_preset()
        self._rebuild_lights()
        self._sync_axes_widget()
        self._sync_cube_axes_actor()
        self.GetRenderWindow().Render()

    def _apply_background_preset(self) -> None:
        """Apply the selected background preset to the renderer."""
        preset = self._display_options.background_preset
        if preset == "paraview_dark_gradient":
            self._renderer.SetBackground(*PARAVIEW_DARK_GRADIENT_BACKGROUND)
            self._renderer.SetBackground2(*PARAVIEW_DARK_GRADIENT_BACKGROUND_2)
            self._renderer.GradientBackgroundOn()
            return
        if preset == "black":
            self._renderer.SetBackground(0.0, 0.0, 0.0)
            self._renderer.SetBackground2(0.0, 0.0, 0.0)
            self._renderer.GradientBackgroundOff()
            return
        if preset == "white":
            self._renderer.SetBackground(1.0, 1.0, 1.0)
            self._renderer.SetBackground2(1.0, 1.0, 1.0)
            self._renderer.GradientBackgroundOff()
            return
        self._renderer.SetBackground(*DEFAULT_RENDERER_BACKGROUND)
        self._renderer.SetBackground2(*DEFAULT_RENDERER_BACKGROUND_2)
        self._renderer.GradientBackgroundOff()

    def _rebuild_lights(self) -> None:
        """Recreate the renderer lights from the current lighting preset."""
        self._renderer.AutomaticLightCreationOff()
        self._renderer.LightFollowCameraOn()
        self._renderer.RemoveAllLights()

        scale = max(self._display_options.lighting_intensity, 0) / 100.0
        preset = self._display_options.lighting_preset
        if preset == "flat":
            self._renderer.AddLight(self._build_headlight(0.95 * scale))
            return

        if preset == "studio_soft":
            lights = (
                self._build_camera_light(0.90 * scale, (0.7, 0.5, 1.0)),
                self._build_camera_light(0.45 * scale, (-0.8, 0.2, 0.6)),
                self._build_camera_light(0.25 * scale, (0.1, -0.7, -1.0)),
            )
        else:
            lights = (
                self._build_camera_light(1.15 * scale, (1.0, 0.3, 0.9)),
                self._build_camera_light(0.28 * scale, (-0.7, -0.1, 0.2)),
                self._build_camera_light(0.65 * scale, (-0.4, 0.9, -0.8)),
            )

        for light in lights:
            self._renderer.AddLight(light)

    @staticmethod
    def _build_headlight(intensity: float) -> vtk.vtkLight:
        """Create one simple headlight."""
        light = vtk.vtkLight()
        light.SetLightTypeToHeadlight()
        light.SetIntensity(intensity)
        return light

    @staticmethod
    def _build_camera_light(
        intensity: float,
        position: tuple[float, float, float],
    ) -> vtk.vtkLight:
        """Create one camera-relative light."""
        light = vtk.vtkLight()
        light.SetLightTypeToCameraLight()
        light.SetPosition(*position)
        light.SetFocalPoint(0.0, 0.0, 0.0)
        light.SetIntensity(intensity)
        return light

    def _restore_camera_state(self, state: dict[str, object]) -> None:
        """Apply one previously captured camera state to the current renderer."""
        camera = self._renderer.GetActiveCamera()
        camera.SetPosition(*state["position"])
        camera.SetFocalPoint(*state["focal_point"])
        camera.SetViewUp(*state["view_up"])
        camera.SetClippingRange(*state["clipping_range"])
        camera.SetParallelScale(float(state["parallel_scale"]))
        camera.SetViewAngle(float(state["view_angle"]))
        if bool(state["parallel_projection"]):
            camera.ParallelProjectionOn()
        else:
            camera.ParallelProjectionOff()
        camera.OrthogonalizeViewUp()
