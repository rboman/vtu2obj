# Prompt initial pour Codex

You are helping me bootstrap a new GitHub repository from scratch.

I want a **professional Python project** that converts a **VTK XML Unstructured Grid (`.vtu`)** containing FEM results into:

- an extracted **surface mesh**,
- an **OBJ** file with UV coordinates,
- a **PNG** texture representing a selected scalar field with a selected colormap,
- and a matching **MTL** file.

## Context

This project is for post-processing results produced by my finite element code **fossils**.

The current manual workflow is:

1. load `.vtu` results in ParaView,
2. choose a nodal field (for example `stress_von_mises`),
3. choose the scalar range and colormap,
4. extract the surface,
5. export a colored mesh,
6. import it into Blender,
7. bake a texture,
8. export OBJ + PNG.

I want to automate this with **Python**, and the **core conversion logic must use only VTK**.

## Hard constraints

1. The core conversion pipeline must rely only on **VTK** for:
   - reading the `.vtu`,
   - extracting the surface,
   - managing scalar fields,
   - generating the PNG texture,
   - generating UV coordinates,
   - preview rendering,
   - and exporting the result whenever VTK supports it.
2. The CLI must use **typer**.
3. There must also be a minimal **PyQt5 + VTK** GUI.
4. The repository must use a modern layout with:
   - `pyproject.toml`
   - `src/` layout
   - editable install support
   - tests
5. Do **not** add ParaView, Blender Python APIs, PyVista, meshio, trimesh, matplotlib, or other unnecessary visualization/mesh dependencies.

## Important design choice

Do **not** implement a diagonal-only texture image.

Instead, implement a robust palette texture like this:

- create a **2D PNG** where each row repeats the same **discrete colormap**,
- default to **256 color bins**,
- map scalar values to the **U** texture coordinate,
- keep **V** constant,
- export OBJ UVs accordingly.

This is preferred because it is simpler and more robust under downstream texture filtering.

## Functional requirements

### A. Inspection

Create functionality to:

- load a `.vtu` file,
- list available point arrays,
- list available cell arrays,
- report number of points and cells,
- validate that a requested field exists.

### B. Surface extraction

Use a VTK-only pipeline to:

- read the unstructured grid,
- extract the surface,
- triangulate if needed,
- preserve scalar arrays on the extracted surface.

### C. Field selection and scaling

The user must be able to choose:

- the field name,
- the colormap,
- `vmin`,
- `vmax`,
- number of colors.

For the first version, it is acceptable to support **point-data scalar arrays first**.

### D. Colormaps

Provide several built-in colormap names, such as:

- `rainbow`
- `cool_to_warm`
- `grayscale`
- a reasonable VTK-native alternative to `viridis`

Be honest if a colormap is only an approximation.

### E. Texture generation

Generate a PNG texture with VTK.

Requirements:

- discrete palette,
- configurable number of bins,
- repeated along rows,
- written with VTK PNG writing.

### F. UV generation

Generate UV coordinates from the scalar values:

- clamp scalar to `[vmin, vmax]`,
- normalize to `[0, 1]`,
- quantize to a discrete bin center,
- store UV coordinates on the mesh.

### G. Export

Export:

- OBJ geometry,
- MTL file,
- PNG texture.

If VTK does not generate everything needed in one step, it is acceptable to write the MTL file manually.

### H. Preview

Provide VTK preview modes for:

- scalar-colored preview,
- textured preview.

### I. Applications

Create:

1. a **CLI** based on `typer`,
2. a minimal **GUI** based on **PyQt5 + VTK**.

## Suggested package structure

Use something close to:

```text
.
├── AGENTS.md
├── README.md
├── pyproject.toml
├── src/
│   └── fossils_vtu2obj/
│       ├── __init__.py
│       ├── cli.py
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
│           ├── app.py
│           ├── main_window.py
│           └── vtk_view.py
└── tests/
    ├── test_arrays.py
    ├── test_surface.py
    ├── test_texture.py
    ├── test_uvmap.py
    ├── test_export_obj.py
    └── test_cli.py
```

You may adjust the structure if needed, but keep the code modular and clean.

## What I want you to do first

Please work in **small, reviewable steps**, not in one giant rewrite.

### Step 1

Bootstrap the repository with:

- `pyproject.toml`
- package skeleton under `src/`
- test skeleton
- `README.md`
- `AGENTS.md`
- a `typer` CLI skeleton

### Step 2

Implement:

- VTU loading,
- dataset inspection,
- array listing,
- surface extraction.

### Step 3

Implement:

- colormaps,
- palette texture PNG generation,
- scalar-to-UV mapping,
- OBJ/MTL export.

### Step 4

Implement:

- VTK preview,
- minimal PyQt5 GUI.

## Acceptance criteria for the first useful milestone

At the end of the first useful milestone, I want to be able to run commands like:

```bash
fossils-vtu2obj list-arrays post.vtu
fossils-vtu2obj preview post.vtu --field stress_von_mises --colormap rainbow
fossils-vtu2obj convert post.vtu out/model --field stress_von_mises --colormap rainbow --vmin 0 --vmax 120 --n-colors 256
```

and obtain:

- `out/model.obj`
- `out/model.mtl`
- `out/model.png`

## Quality requirements

- Use small functions and clear names.
- Add docstrings to public APIs.
- Add type hints where practical.
- Add tests for deterministic logic.
- Avoid fragile GUI-heavy tests in the default suite.
- Document trade-offs in the README.

## Deliverable format

Please start by:

1. proposing a concrete plan,
2. creating the initial repository files,
3. explaining any technical trade-offs briefly,
4. then stopping for review before making the next larger step.
