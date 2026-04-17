# fossils-vtu2obj

`fossils-vtu2obj` is a Python project for converting FEM results stored in
**VTK XML Unstructured Grid** files (`.vtu`) into:

- an extracted surface mesh,
- an OBJ file with UV coordinates,
- a PNG palette texture generated from a selected scalar field,
- and a matching MTL file for straightforward Blender import.

The project targets post-processing workflows around the **fossils** finite
element solver and keeps the core conversion pipeline **VTK-only**.

## Status

The repository is currently bootstrapped for the first milestone:

- modern `pyproject.toml` packaging with a `src/` layout,
- a `typer` CLI skeleton,
- modular package structure for the VTK pipeline,
- a reserved `native/` area for a future optional `C++ + SWIG` bridge,
- test scaffolding focused on deterministic logic.

The actual VTU inspection, surface extraction, texture generation, UV mapping,
OBJ export, preview, and GUI behavior are still to be implemented in the next
reviewable steps.

## Design goals

- Use **VTK only** for geometry, scalar handling, color mapping, texture
  generation, preview, and export whenever VTK supports it.
- Keep the main package **Python-first**, so the CLI and conversion workflow
  remain usable without any optional native extension.
- Leave a clean path for a future **optional fossils bridge** implemented with
  `C++ + SWIG`, without coupling the first milestone to a native build system.

## Texture strategy

The project intentionally avoids diagonal-only textures.

Instead, the conversion pipeline will generate a robust 2D palette texture:

- texture width equals the number of discrete color bins,
- each row repeats the same palette,
- the scalar value is encoded in the `U` texture coordinate,
- the `V` coordinate stays constant.

This makes the exported OBJ/MTL/PNG set more stable under texture filtering in
downstream tools such as Blender.

## Project layout

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── native/
│   └── README.md
├── src/
│   └── fossils_vtu2obj/
│       ├── __init__.py
│       ├── __main__.py
│       ├── arrays.py
│       ├── cli.py
│       ├── colormaps.py
│       ├── export_obj.py
│       ├── io_vtk.py
│       ├── logging_utils.py
│       ├── model.py
│       ├── preview.py
│       ├── surface.py
│       ├── texture.py
│       ├── uvmap.py
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── fossils.py
│       └── gui/
│           ├── __init__.py
│           ├── app.py
│           ├── main_window.py
│           └── vtk_view.py
└── tests/
    ├── conftest.py
    ├── test_arrays.py
    ├── test_cli.py
    ├── test_colormaps.py
    ├── test_export_obj.py
    ├── test_integrations.py
    ├── test_surface.py
    ├── test_texture.py
    └── test_uvmap.py
```

## Why `setuptools` for the bootstrap

The initial bootstrap uses `setuptools.build_meta` instead of `hatchling`.

That choice keeps the first milestone simple while preserving an easier upgrade
path toward a future optional native module. If the fossils bridge evolves into
a real compiled extension, the repository can later move to
`scikit-build-core` or another CMake-oriented backend without rewriting the
Python package layout.

## Optional future native integration

The future native integration is planned as an **optional bridge**, not as a
replacement for the VTK conversion code.

- `src/fossils_vtu2obj/integrations/` is the Python-facing boundary.
- `native/` is reserved for future `C++ + SWIG` sources and build files.
- The default test suite and CLI must keep working even when no native bridge
  is installed.

## Development setup

Base install:

```bash
pip install -e .
```

Development tools:

```bash
pip install -e .[dev]
```

GUI dependencies:

```bash
pip install -e .[gui]
```

## Near-term roadmap

1. Implement VTU loading, dataset inspection, and surface extraction.
2. Implement colormaps, palette texture generation, UV mapping, and OBJ export.
3. Implement VTK preview and the minimal PyQt5 GUI.
4. Evaluate whether a future fossils bridge belongs as an optional native
   extension.

## Trade-offs in the bootstrap

- The repository is intentionally not wired to CMake yet, even though a future
  `C++ + SWIG` bridge is anticipated.
- GUI modules exist from day one, but they remain lazily imported so the base
  package does not require `PyQt5`.
- The CLI commands are present early for a stable user-facing shape, but their
  heavy behavior is deferred to the next milestones.
