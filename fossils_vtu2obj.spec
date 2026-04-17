# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec to build CLI and GUI executables in one distribution."""

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH)
src_root = project_root / "src"

vtk_hiddenimports = collect_submodules("vtkmodules")
vtk_datas = collect_data_files("vtkmodules")

app_datas = [
    (str(project_root / "src" / "fossils_vtu2obj" / "gui" / "assets" / "*.svg"), "fossils_vtu2obj/gui/assets"),
]

common_hiddenimports = vtk_hiddenimports + ["PyQt5.QtSvg"]
common_datas = vtk_datas + app_datas


cli_analysis = Analysis(
    [str(project_root / "build_scripts" / "cli_entry.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=common_datas,
    hiddenimports=common_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


gui_analysis = Analysis(
    [str(project_root / "build_scripts" / "gui_entry.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=common_datas,
    hiddenimports=common_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

MERGE(
    (cli_analysis, "fossils-vtu2obj", "fossils-vtu2obj"),
    (gui_analysis, "fossils-vtu2obj-gui", "fossils-vtu2obj-gui"),
)

cli_pyz = PYZ(cli_analysis.pure)
gui_pyz = PYZ(gui_analysis.pure)

cli_exe = EXE(
    cli_pyz,
    cli_analysis.scripts,
    [],
    exclude_binaries=True,
    name="fossils-vtu2obj",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="fossils-vtu2obj-gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)


coll = COLLECT(
    cli_exe,
    gui_exe,
    cli_analysis.binaries,
    cli_analysis.zipfiles,
    cli_analysis.datas,
    gui_analysis.binaries,
    gui_analysis.zipfiles,
    gui_analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="fossils_vtu2obj",
)
