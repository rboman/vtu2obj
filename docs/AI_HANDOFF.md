# AI handoff

This file is intended as compact continuity memory for a new AI session or a
different coding agent.

## What this project is

`fossils-vtu2obj` converts VTU FEM results into:

- surface OBJ geometry,
- a palette PNG texture,
- and a matching MTL file.

The main audience is FEM post-processing around the `fossils` solver.

## Important decisions already made

- Use VTK only for the core conversion pipeline.
- Do not use ParaView, Blender APIs, PyVista, `meshio`, `trimesh`,
  `matplotlib`, or similar extra geometry/visualization stacks.
- Use a repeated 2D palette texture, not a diagonal-only texture.
- Use scalar-to-UV mapping: scalar -> `U`, constant `V`.
- Keep the project Python-first.
- Treat the future native `fossils` bridge as optional.
- Keep docs in English.

## Current product shape

- CLI commands:
  - `inspect`
  - `list-arrays`
  - `preview`
  - `convert`
  - `gui`
  - `native-status`
- GUI:
  - dual viewport layout
  - left = VTU workflow
  - right = OBJ bundle comparison
  - tabs `Controls`, `Display`, `Info`
  - texture preview on the OBJ side
  - recent files and clear views
  - background, lights, camera, trihedron, bounding box, edges per view

## Key code areas

- `src/fossils_vtu2obj/cli.py`
  - CLI surface
- `src/fossils_vtu2obj/preview.py`
  - preview scene construction
- `src/fossils_vtu2obj/export_obj.py`
  - OBJ/MTL/PNG export
- `src/fossils_vtu2obj/uvmap.py`
  - scalar-to-UV logic
- `src/fossils_vtu2obj/gui/main_window.py`
  - main GUI workflow
- `src/fossils_vtu2obj/gui/vtk_view.py`
  - embedded VTK renderer behavior
- `src/fossils_vtu2obj/defaults.py`
  - centralized defaults and magic numbers

## Known pitfalls

- Windows Qt/VTK shutdown and widget lifecycle can be fragile.
- Active VTK calls on the GUI thread cannot be force-cancelled safely.
- Rendering-related refactors should be checked carefully on Windows.
- Keep user docs and AI docs separate.

## How to document future work

- Update `README.md` only for user-visible behavior.
- Update `INSTALL.md` for installation or packaging changes.
- Update `docs/ARCHITECTURE.md` for structural changes.
- Update `docs/PROJECT_STATUS.md` when project scope or priorities shift.
- Update `AGENTS.md` and this file when a new agent would otherwise lose
  important context.

## Likely next improvements

- GUI responsiveness for very large meshes
- export fidelity and shading behavior
- additional UX polish in the GUI
- optional native bridge only if justified by a real workflow need
