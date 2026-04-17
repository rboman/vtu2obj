# Architecture

## Overview

`fossils-vtu2obj` is organized around a VTK-only conversion pipeline:

1. read a VTU unstructured grid,
2. inspect arrays and dataset metadata,
3. extract the outer surface,
4. prepare a scalar field and mapping range,
5. generate UV coordinates from scalar values,
6. generate a palette texture PNG,
7. export `OBJ + MTL + PNG`,
8. preview the result with VTK.

## Main subsystems

### Core conversion modules

- `io_vtk.py`
  - VTU reading and dataset inspection
- `arrays.py`
  - array discovery and default field selection
- `surface.py`
  - surface extraction and normal generation
- `colormaps.py`
  - discrete colormap presets
- `texture.py`
  - VTK palette texture image generation and PNG writing
- `uvmap.py`
  - scalar normalization, quantization, and UV generation
- `export_obj.py`
  - OBJ/MTL/PNG export helpers
- `preview.py`
  - scalar and textured VTK preview scenes

### CLI

- `cli.py`
  - user-facing command-line entry point
  - current commands: `inspect`, `list-arrays`, `preview`, `convert`,
    `gui`, `native-status`

### GUI

- `gui/app.py`
  - GUI launcher
- `gui/main_window.py`
  - main application window, workflow wiring, recent files, progress dialogs
- `gui/viewport_panel.py`
  - reusable viewport panel with `Controls`, `Display`, `Info` tabs
- `gui/vtk_view.py`
  - embedded VTK renderer, overlays, lighting, camera presets

## Data model

Important shared types are defined in `model.py`, including:

- dataset summaries,
- array descriptors,
- scalar mapping options,
- export bundle paths,
- per-viewport display options,
- mesh information shown in the GUI.

## Texture and UV design

The project intentionally uses a **repeated palette texture**:

- width = number of color bins,
- height = repeated rows,
- one vertical stripe per discrete bin,
- scalar field mapped to `U`,
- constant `V`.

This is simpler and more robust downstream than a diagonal-only texture.

## GUI architecture

The GUI is built around two synchronized workflows:

- left side: VTU loading, scalar selection, preview, conversion
- right side: exported OBJ bundle loading and textured comparison

Each viewport has:

- `Controls`
- `Display`
- `Info`

Per-viewport display options currently include:

- mesh edges,
- XYZ trihedron,
- graduated bounding box,
- edge color,
- background preset,
- lighting preset and intensity,
- camera preset.

## Optional native bridge

The repository keeps a clean place for a future optional native `fossils`
integration:

- `src/fossils_vtu2obj/integrations/`
- `native/`

That bridge is expected to stay optional and must not replace the Python/VTK
pipeline.
