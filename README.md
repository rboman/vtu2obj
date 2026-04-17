# fossils-vtu2obj

Convert FEM results stored in **VTK XML Unstructured Grid** files (`.vtu`) into:

- an extracted **surface mesh**,
- an **OBJ** file with UV coordinates,
- a **PNG texture** generated from a selected scalar field and colormap,
- a matching **MTL** file for easy import in Blender.

The project is intended for post-processing results produced by the **fossils** finite element solver.

---

## Why this project exists

A current manual workflow is possible with ParaView and Blender:

1. load the FEM results in ParaView,
2. display a nodal scalar field with a chosen colormap and scalar range,
3. extract the surface,
4. export a colored mesh,
5. import it into Blender,
6. unwrap UVs,
7. bake the colors into a PNG texture,
8. export OBJ + PNG.

The attached workflow note describes exactly that current path: surface extraction in ParaView, colored PLY export, Blender import, vertex-color material setup, UV unwrap, image creation, baking, then OBJ + PNG export. fileciteturn1file0 fileciteturn1file1

This repository aims to replace that manual chain with a **Python implementation whose core logic relies only on VTK**.

---

## Main idea

Instead of baking a full spatial texture atlas, this project uses a simpler and more robust approach:

- extract the surface mesh,
- choose a scalar field,
- normalize and quantize scalar values,
- generate a discrete palette texture as a PNG,
- assign UV coordinates from the scalar values,
- export OBJ + MTL + PNG.

This means the texture acts like a **color ramp texture**, while the UV coordinates encode the scalar value at each mesh point.

### Why this is attractive

- no ParaView dependency at runtime,
- no Blender dependency at runtime,
- no UV unwrapping step,
- compact texture file,
- reproducible and scriptable pipeline,
- easy integration into a future GUI.

---

## Proposed technical architecture

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

---

## Scope

### Core features

- Read `.vtu` files with VTK.
- Discover available point and cell arrays.
- Extract the surface mesh.
- Select a field to visualize.
- Choose a colormap.
- Set explicit `vmin` / `vmax`.
- Quantize to a discrete number of colors.
- Build a PNG texture with VTK.
- Build UV coordinates from scalar values.
- Export OBJ + MTL + PNG.
- Preview the result with VTK.

### Applications

- **CLI** with `typer`
- **GUI** with `PyQt5 + VTK`

### Quality

- tests,
- editable install,
- modern `pyproject.toml`,
- optional dev dependencies,
- clean modular code.

---

## Colormap and texture strategy

### Important design note

A diagonal-only texture image is not ideal for interoperability because filtering and interpolation can sample unwanted texels.

The recommended strategy is:

- create a **2D palette texture**,
- repeat the same discrete colormap on every row,
- encode the scalar value into the **U** coordinate,
- keep **V** constant.

For example, with 256 colors:

- texture size: `256 x 16` or `256 x 32`,
- each vertical stripe corresponds to one color bin,
- UV mapping uses the center of each bin.

This is conceptually a 1D color ramp stored in a regular 2D PNG for broad compatibility.

---

## Data assumptions

The initial target is a `.vtu` file produced by `fossils`.

Typical fields of interest include nodal scalar arrays such as:

- `stress_von_mises`
- `strain_von_mises`

and possibly vector/tensor arrays such as displacement or full stress/strain tensors.

Initial implementation can focus on **point-data scalar arrays** first. Cell-data support can be added just after the first milestone.

---

## CLI design

Suggested commands:

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

### Expected outputs for `convert`

For an output prefix `out/model`, the command should generate:

- `out/model.obj`
- `out/model.mtl`
- `out/model.png`

---

## GUI design

A minimal PyQt5 GUI should provide:

- file chooser,
- array selector,
- colormap selector,
- scalar min/max controls,
- preview widget,
- export button.

The first version does not need advanced UX. The priority is correctness and future extensibility.

---

## Test strategy

Focus on deterministic tests first:

- discovering arrays in a dataset,
- clamping and normalization,
- quantization into discrete bins,
- generated texture dimensions and colors,
- generated UV coordinates,
- surface extraction on a tiny synthetic mesh,
- CLI smoke tests.

Keep preview and GUI tests lightweight and optional if headless CI becomes fragile.

---

## Development setup

Recommended install flows:

```bash
pip install -e .
pip install -e .[dev]
pip install -e .[gui]
```

Recommended tooling:

- `pytest`
- `ruff`
- type hints where practical

---

## Roadmap

### Milestone 1

- package skeleton,
- pyproject,
- CLI skeleton,
- load VTU,
- list arrays,
- extract surface,
- preview scalar field.

### Milestone 2

- colormaps,
- discrete texture PNG,
- scalar-to-UV mapping,
- OBJ + MTL export.

### Milestone 3

- minimal GUI,
- stronger tests,
- examples and polish.

---

## Non-goals for the first iteration

- full ParaView colormap parity,
- advanced texture baking,
- physically based materials,
- support for every VTK dataset type,
- optimized performance for very large models.

---

## Notes for contributors and coding agents

- Keep the core conversion logic VTK-only.
- Prefer small reviewable commits.
- Do not add mesh libraries unless explicitly requested.
- Document trade-offs honestly.
- Prioritize correctness, simplicity, and maintainability.
