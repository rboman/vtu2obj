# fossils-vtu2obj

`fossils-vtu2obj` converts FEM results stored in **VTK XML Unstructured Grid**
files (`.vtu`) into:

- an extracted surface mesh,
- an OBJ file with UV coordinates,
- a PNG palette texture generated from a selected scalar field,
- and a matching MTL file for direct import in tools such as Blender.

The project is designed for post-processing workflows around the **fossils**
finite element solver and keeps the core conversion pipeline **VTK-only**.

![](docs/images/panthera_vtu2obj.jpg)

![](docs/images/panthera_blender.jpg)

## Quick start

Install the command-line tool:

```bash
pip install .
```

Install the GUI as well:

```bash
pip install ".[gui]"
```

Try the example dataset:

```bash
fossils-vtu2obj inspect examples/beam3d.vtu
fossils-vtu2obj list-arrays examples/beam3d.vtu
fossils-vtu2obj preview examples/beam3d.vtu --field stress_von_mises
fossils-vtu2obj convert examples/beam3d.vtu out/beam --field stress_von_mises
fossils-vtu2obj gui
```

## What the tool does

The current application can:

- inspect VTU datasets,
- list point-data and cell-data arrays,
- extract the outer surface with VTK,
- preview scalar coloring or textured output with VTK,
- generate a discrete palette texture PNG,
- generate UV coordinates from a scalar field,
- export `OBJ + MTL + PNG`,
- open a GUI with a VTU view and an OBJ bundle comparison view.

## Typical workflow

1. Open a `.vtu` result file.
2. Choose a scalar field such as `stress_von_mises`.
3. Choose a colormap and scalar range.
4. Preview the result.
5. Export an OBJ bundle.
6. Open the exported OBJ in Blender or another DCC tool.

The exported texture is a robust **palette texture**:

- each row repeats the same discrete colormap,
- the scalar field is encoded in the `U` coordinate,
- `V` stays constant.

This makes the exported mesh more stable under downstream texture filtering
than a diagonal-only texture approach.

## CLI examples

Inspect a dataset:

```bash
fossils-vtu2obj inspect examples/beam3d.vtu
```

List arrays:

```bash
fossils-vtu2obj list-arrays examples/beam3d.vtu
```

Preview a scalar field:

```bash
fossils-vtu2obj preview examples/beam3d.vtu \
  --field stress_von_mises \
  --colormap rainbow
```

Preview the textured surface:

```bash
fossils-vtu2obj preview examples/beam3d.vtu \
  --field stress_von_mises \
  --colormap rainbow \
  --textured
```

Export an OBJ bundle:

```bash
fossils-vtu2obj convert examples/beam3d.vtu out/beam \
  --field stress_von_mises \
  --colormap rainbow \
  --vmin 0 \
  --vmax 120 \
  --n-colors 16
```

Export a cell-data field:

```bash
fossils-vtu2obj convert examples/beam3d.vtu out/beam_cell \
  --field cell_stress_von_mises \
  --colormap cool_to_warm
```

Check the optional native bridge status:

```bash
fossils-vtu2obj native-status
```

## GUI overview

The GUI currently provides:

- a left viewport dedicated to VTU inspection and conversion,
- a right viewport dedicated to exported OBJ/MTL/PNG bundle comparison,
- tabs `Controls`, `Display`, and `Info` under each viewport,
- scalar field and colormap selection,
- texture preview for the loaded OBJ bundle,
- recent files lists,
- per-view display options such as mesh edges, trihedron, bounding box,
  background preset, lighting preset, and camera presets.

## Included examples

The repository currently includes:

- [examples/beam3d.vtu](examples/beam3d.vtu)
- [examples/doli.vtu](examples/doli.vtu)

See [examples/README.md](examples/README.md) for a short description of each
dataset.

## Current limitations

- Only scalar fields can drive preview and export.
- Vector and tensor arrays are listed during inspection but are not directly
  convertible.
- The GUI uses cooperative cancellation for long-running operations; an active
  VTK call cannot be interrupted immediately.
- The optional native `fossils` bridge is not implemented yet.

## Documentation

- [INSTALL.md](INSTALL.md) for complete installation and packaging notes
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the technical architecture
- [docs/PROJECT_STATUS.md](docs/PROJECT_STATUS.md) for the current state and
  roadmap
- [docs/AI_HANDOFF.md](docs/AI_HANDOFF.md) for project memory aimed at future
  AI sessions or other coding agents
- [AGENTS.md](AGENTS.md) for compact agent-oriented project guidance
