# AGENTS.md

## Mission

Build a **Python package and applications** that convert a
**VTK XML Unstructured Grid (`.vtu`)** containing FEM results into:

- a surface mesh exported as OBJ,
- a PNG texture representing a chosen scalar field with a chosen colormap,
- and a matching MTL file so the OBJ can be loaded directly in Blender.

The tool is intended for FEM post-processing of results produced by the
**fossils** solver.

## Product goals

1. Read a `.vtu` file containing point data and later cell data.
2. Extract the surface mesh using a VTK-only pipeline.
3. Let the user choose the scalar field, colormap, scalar range, and number of
   discrete color bins.
4. Generate a palette PNG texture from the selected colormap.
5. Generate texture coordinates on the mesh from scalar values.
6. Export the surface mesh as OBJ with UVs and a matching MTL referencing the
   PNG.
7. Provide a fast preview using VTK.
8. Provide both a CLI based on `typer` and a GUI based on `PyQt5 + VTK`.
9. Keep the repository extensible toward an optional future `C++ + SWIG`
   fossils bridge.

## Non-negotiable constraints

### Core conversion stack

The core conversion logic must use only **VTK** for:

- reading the `.vtu`,
- extracting the surface,
- managing scalar fields,
- generating the PNG texture,
- generating UV coordinates,
- preview rendering,
- and exporting the result whenever VTK supports it.

### Allowed supporting libraries

These are allowed outside the core conversion logic:

- `typer` for the CLI,
- `PyQt5` for the GUI,
- `pytest` for tests,
- standard library modules,
- light dev tooling such as `ruff`.

Do **not** add ParaView, Blender Python APIs, `pyvista`, `meshio`, `trimesh`,
`matplotlib`, or other mesh/visualization libraries unless the user explicitly
asks for them.

## Important design decision about the texture

Do not implement a diagonal-only texture image.

Implement a 2D palette texture where:

- each row repeats the same 1D discrete colormap,
- `u = scalar_to_bin_center(s)`,
- `v` is constant, typically the middle of the texture.

This is more robust than a diagonal-only texture under interpolation and
filtering in downstream tools.

### Required implementation choice

Implement the texture as:

- width = `n_colors` or a padded multiple,
- height = at least `8` or `16` pixels,
- one vertical stripe per color bin,
- identical rows repeating the same stripe pattern.

## Python-first plus optional native bridge

The repository should remain **Python-first**. The conversion workflow must be
usable without any native module.

However, the initial structure must leave a clean path for an optional future
`C++ + SWIG` integration with fossils:

- keep the VTK conversion logic inside `src/fossils_vtu2obj/`,
- reserve `src/fossils_vtu2obj/integrations/` for optional bridges,
- reserve `native/` for future compiled sources and build files,
- avoid tight coupling between the CLI and any future native extension.

The native bridge is expected to be optional and should not replace the VTK
pipeline.

## Expected architecture

Use a `src/` layout and bootstrap with `setuptools`.

Suggested structure:

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
│       ├── cli.py
│       ├── logging_utils.py
│       ├── model.py
│       ├── io_vtk.py
│       ├── arrays.py
│       ├── surface.py
│       ├── colormaps.py
│       ├── texture.py
│       ├── uvmap.py
│       ├── export_obj.py
│       ├── preview.py
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── fossils.py
│       └── gui/
│           ├── __init__.py
│           ├── app.py
│           ├── main_window.py
│           └── vtk_view.py
├── tests/
│   ├── conftest.py
│   ├── test_arrays.py
│   ├── test_cli.py
│   ├── test_colormaps.py
│   ├── test_export_obj.py
│   ├── test_integrations.py
│   ├── test_surface.py
│   ├── test_texture.py
│   └── test_uvmap.py
└── examples/
    └── README.md
```

## Functional requirements

### 1. Input inspection

Implement functions to:

- load a `.vtu` unstructured grid,
- list available point data arrays,
- list available cell data arrays,
- report number of points and cells,
- identify scalar, vector, and tensor arrays,
- validate that a requested field exists.

### 2. Surface extraction

Use a VTK pipeline equivalent to:

- `vtkXMLUnstructuredGridReader`,
- `vtkDataSetSurfaceFilter`,
- `vtkTriangleFilter` when needed.

Keep scalar arrays on the extracted surface whenever possible.

### 3. Field selection and scalar preparation

Support at minimum:

- point-data scalar fields,
- automatic min/max,
- user-defined min/max,
- clamping outside the selected range,
- quantization to `n_colors` bins.

Cell-data support can follow later.

### 4. Colormap support

Provide VTK-native colormap presets such as:

- `rainbow`,
- `viridis_like`,
- `cool_to_warm`,
- `grayscale`.

If a colormap is only an approximation, document that honestly.

### 5. Texture generation

Generate a PNG texture using VTK image classes and `vtkPNGWriter`.

### 6. UV generation from scalar values

Create texture coordinates per point from the chosen scalar field, using clamp,
normalize, quantize, and bin-center mapping.

### 7. OBJ/MTL export

Export the final surface polydata with UVs to OBJ and write a matching MTL that
references the texture PNG.

### 8. Preview

Implement VTK preview modes for scalar-colored and textured rendering.

### 9. CLI

Create a `typer` CLI with subcommands such as:

- `inspect`
- `list-arrays`
- `preview`
- `convert`

### 10. GUI

Provide a minimal PyQt5 GUI with:

- file open button,
- field selector,
- colormap selector,
- min/max controls,
- export button,
- VTK render widget.

## Testing requirements

Prioritize deterministic non-GUI logic:

1. array discovery,
2. scalar normalization and clamping,
3. quantization into bins,
4. texture image generation dimensions and content,
5. UV coordinate generation,
6. surface extraction on a tiny synthetic dataset,
7. CLI smoke tests.

Also verify that the absence of the optional native bridge does not break
imports or the CLI.

## Tooling requirements

Set up a professional Python project with:

- `pyproject.toml`,
- editable install support,
- console script entry point,
- optional extras such as `[dev]` and `[gui]`,
- `pytest`,
- `ruff`,
- basic type hints where practical.

Bootstrap with `setuptools.build_meta`. If a future native bridge becomes more
than a thin optional layer, the repository may later migrate to
`scikit-build-core`.

## Iteration strategy

Work in small, reviewable steps.

### Phase 1

Bootstrap repository:

- packaging,
- package skeleton,
- CLI skeleton,
- tests scaffold,
- optional native bridge scaffolding.

### Phase 2

Implement inspection and surface extraction.

### Phase 3

Implement colormaps, texture generation, UV mapping, and export.

### Phase 4

Implement preview and the minimal GUI.

### Phase 5

If needed, add an optional fossils bridge in `native/` and expose it through
`fossils_vtu2obj.integrations.fossils`.

## Coding style

- Keep functions small.
- Prefer explicit names.
- Add docstrings to public functions.
- Avoid hidden global state.
- Use dataclasses for structured options and results when helpful.
- Prefer pure functions for scalar mapping logic.

## When uncertain

Choose the simplest implementation that preserves:

1. VTK-only core logic,
2. correct UV-based texturing,
3. maintainable code,
4. reproducible CLI behavior,
5. optional-native extensibility without coupling the core package to fossils.
