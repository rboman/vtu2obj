# AGENTS.md

## Mission

Build a **Python package and applications** that convert a **VTK XML Unstructured Grid (`.vtu`)** containing FEM results into:

- a **surface mesh** exported as **OBJ**,
- a **PNG texture** representing a chosen scalar field with a chosen colormap,
- optionally a matching **MTL** file so the OBJ can be loaded directly in Blender.

The project starts from an empty GitHub repository.

The tool is intended for FEM post-processing of results produced by the **fossils** solver.

---

## Product goals

1. Read a `.vtu` file containing point data and/or cell data.
2. Extract the **surface mesh** using a VTK-only pipeline.
3. Let the user choose:
   - the scalar field to visualize,
   - the colormap,
   - the scalar range `[vmin, vmax]`,
   - the number of discrete color bins (default: 256).
4. Generate a **texture PNG** from the selected colormap.
5. Generate **texture coordinates** on the mesh from scalar values.
6. Export the surface mesh as **OBJ** with UVs and a matching **MTL** referencing the PNG.
7. Provide a **fast preview** using VTK.
8. Provide both:
   - a **CLI** based on `typer`,
   - a **GUI** based on **PyQt5 + VTK**.
9. Include **tests**, clean packaging, and a professional project layout.

---

## Non-negotiable constraints

### Core conversion stack

The **core conversion logic must use only VTK** for geometry, scalar processing, lookup tables, texture generation, preview, and file export whenever VTK supports it.

That means:

- use VTK readers/writers/filters,
- use VTK lookup tables / color transfer functions,
- use VTK image generation for the texture,
- use VTK rendering for preview.

### Allowed supporting libraries

These are allowed outside the core conversion logic:

- `typer` for the CLI,
- `PyQt5` for the GUI,
- `pytest` for tests,
- standard library modules,
- light dev tooling such as `ruff`.

Do **not** introduce ParaView, Blender Python APIs, `meshio`, `trimesh`, `pyvista`, `matplotlib`, or other mesh/visualization libraries unless the user explicitly asks for them.

---

## Important design decision about the texture

The user initially described a diagonal-coded PNG texture. For robustness and interoperability, prefer the following design:

- generate a **2D palette texture** where each row repeats the same 1D discrete colormap,
- assign UV coordinates from the normalized scalar value:
  - `u = scalar_to_bin_center(s)`
  - `v = 0.5` (or any constant row center)

This is better than a diagonal-only texture because it is more stable under interpolation and filtering in downstream tools.

### Required implementation choice

Implement the texture as:

- width = `n_colors` or a padded multiple,
- height = at least `8` or `16` pixels,
- each vertical stripe corresponds to one discrete color bin,
- every row repeats the same stripe pattern.

Optionally support a “padded” mode later to reduce color bleeding.

---

## Expected architecture

Use a `src/` layout.

Suggested package name:

- `fossils_vtu2obj`

Suggested structure:

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/
│   └── fossils_vtu2obj/
│       ├── __init__.py
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
│       └── gui/
│           ├── __init__.py
│           ├── app.py
│           ├── main_window.py
│           └── vtk_view.py
├── tests/
│   ├── test_arrays.py
│   ├── test_colormaps.py
│   ├── test_texture.py
│   ├── test_uvmap.py
│   ├── test_surface.py
│   ├── test_export_obj.py
│   └── test_cli.py
└── examples/
    └── README.md
```

This exact structure may be adjusted if needed, but keep the code modular.

---

## Functional requirements

### 1. Input inspection

Implement functions to:

- load a `.vtu` unstructured grid,
- list available point data arrays,
- list available cell data arrays,
- report number of points/cells,
- identify scalar/vector/tensor arrays,
- validate that a requested field exists.

### 2. Surface extraction

Use a VTK pipeline equivalent to:

- `vtkXMLUnstructuredGridReader`
- `vtkDataSetSurfaceFilter`
- `vtkTriangleFilter` (if needed)
- normal generation only if helpful for downstream rendering

Keep scalar arrays on the surface if possible.

### 3. Field selection and scalar preparation

Support at minimum:

- point-data scalar fields,
- optional cell-data support later.

If cell data is selected, either:

- convert cell data to point data with VTK, or
- clearly document the current limitation.

Scalars must support:

- automatic min/max,
- user-defined min/max,
- clamping outside the selected range,
- quantization to `n_colors` bins.

### 4. Colormap support

Provide a colormap module with a few named presets, for example:

- `rainbow`
- `viridis_like`
- `cool_to_warm`
- `grayscale`

If exact matplotlib colormaps are not available through VTK alone, create close VTK-native equivalents and document them honestly.

The API should expose:

- a VTK lookup table or color transfer function,
- conversion from normalized scalar to RGB,
- generation of the discrete palette texture.

### 5. Texture generation

Generate a PNG texture using VTK image classes.

Requirements:

- discrete palette with configurable `n_colors` (default 256),
- RGBA or RGB PNG,
- repeat the palette along rows,
- write with `vtkPNGWriter`.

### 6. UV generation from scalar values

Create texture coordinates per point from the chosen scalar field.

Requirements:

- clamp and normalize scalar values,
- quantize to bins for the discrete texture,
- store UV coordinates as point data texture coordinates,
- ensure the exported OBJ contains usable UVs.

### 7. OBJ/MTL export

Export the final surface polydata with UVs to OBJ.

Requirements:

- geometry must be the extracted surface,
- UV coordinates must be present,
- normals should be written if convenient,
- write a matching `.mtl` file that references the generated PNG.

If VTK does not directly write everything needed for the MTL, write the small MTL text file manually.

### 8. Preview

Implement VTK preview modes:

- scalar-colored preview using the lookup table,
- textured preview using the generated UVs + texture,
- optional wireframe toggle later.

Support offscreen rendering only if easy, but do not over-engineer it initially.

### 9. CLI

Create a `typer` CLI with subcommands such as:

- `inspect`
- `list-arrays`
- `preview`
- `convert`

Example desired UX:

```bash
fossils-vtu2obj inspect post.vtu
fossils-vtu2obj list-arrays post.vtu
fossils-vtu2obj preview post.vtu --field stress_von_mises --colormap rainbow
fossils-vtu2obj convert post.vtu out/model \
  --field stress_von_mises \
  --colormap rainbow \
  --vmin 0 \
  --vmax 120 \
  --n-colors 256
```

### 10. GUI

Provide a minimal but functional PyQt5 GUI.

Required elements:

- file open button,
- combo box for field selection,
- combo box for colormap selection,
- min/max controls,
- export button,
- VTK render widget.

The GUI can be minimal at first. Prefer a clean architecture over visual polish.

---

## Testing requirements

Tests must focus first on deterministic, non-GUI logic.

Priority tests:

1. array discovery,
2. scalar normalization and clamping,
3. quantization into bins,
4. texture image generation dimensions and content,
5. UV coordinate generation,
6. surface extraction on a tiny synthetic dataset,
7. CLI smoke tests.

If headless rendering is flaky in CI, mark preview/GUI tests separately and keep the main test suite robust.

Also create at least one tiny synthetic VTK dataset in tests rather than depending only on large external fixtures.

---

## Tooling requirements

Set up a professional Python project:

- `pyproject.toml`
- editable install support
- console script entry point
- optional extras such as `[dev]` and `[gui]`
- `pytest`
- `ruff`
- basic type hints where practical

Prefer straightforward, maintainable tooling over cleverness.

---

## Iteration strategy

Work in small, reviewable steps.

### Phase 1

Bootstrap repository:

- packaging,
- package skeleton,
- CLI skeleton,
- README,
- tests scaffold.

### Phase 2

Implement inspection and surface extraction.

### Phase 3

Implement colormaps, texture generation, UV mapping.

### Phase 4

Implement OBJ/MTL export and preview.

### Phase 5

Implement minimal GUI.

### Phase 6

Polish tests, docs, and examples.

---

## Coding style

- Keep functions small.
- Prefer explicit names.
- Add docstrings to public functions.
- Avoid hidden global state.
- Use dataclasses for structured options/results when helpful.
- Prefer pure functions for scalar mapping logic.

---

## Definition of done for the first meaningful milestone

A first milestone is complete when all of the following are true:

1. The package installs with `pip install -e .[dev]`.
2. `fossils-vtu2obj list-arrays post.vtu` works.
3. `fossils-vtu2obj preview post.vtu --field stress_von_mises` opens a VTK preview.
4. `fossils-vtu2obj convert post.vtu out/model --field stress_von_mises` writes:
   - `model.obj`
   - `model.mtl`
   - `model.png`
5. The exported mesh loads in Blender with the texture.
6. Tests pass.

---

## Things to avoid

- Do not rewrite the whole project in one giant step.
- Do not add unnecessary dependencies.
- Do not silently degrade behavior.
- Do not claim exact colormap equivalence unless it is true.
- Do not implement a fake preview; use real VTK rendering.
- Do not rely on ParaView or Blender for any runtime conversion step.

---

## When uncertain

If a technical point is ambiguous, choose the simplest implementation that preserves:

1. VTK-only core logic,
2. correct UV-based texturing,
3. maintainable code,
4. reproducible CLI behavior.

Document trade-offs in the README.
