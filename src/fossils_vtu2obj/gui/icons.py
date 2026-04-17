"""Qt icon helpers for the fossils-vtu2obj GUI."""

from __future__ import annotations

from pathlib import Path

from PyQt5 import QtGui, QtWidgets


def app_icon_path() -> Path:
    """Return the packaged application icon path."""
    return Path(__file__).with_name("assets") / "fossils_vtu2obj_app.svg"


def create_app_icon() -> QtGui.QIcon:
    """Return the application icon."""
    return QtGui.QIcon(str(app_icon_path()))


def standard_icon(
    widget: QtWidgets.QWidget,
    pixmap: QtWidgets.QStyle.StandardPixmap,
) -> QtGui.QIcon:
    """Return one standard Qt icon from the active application style."""
    return widget.style().standardIcon(pixmap)
