# AGENTS.md

## Mission

Maintain and extend `fossils-vtu2obj`, a Python-first tool that converts VTU
FEM results into:

- an extracted surface mesh,
- an OBJ file with UV coordinates,
- a PNG palette texture,
- and a matching MTL file.

The project is aimed at post-processing workflows around the `fossils` solver.

## Non-negotiable constraints

- The core conversion pipeline must stay **VTK-only** for reading, surface
  extraction, scalar processing, texture generation, UV generation, preview,
  and export whenever VTK supports it.
- Do not add ParaView, Blender Python APIs, PyVista, `meshio`, `trimesh`,
  `matplotlib`, or similar extra visualization stacks unless explicitly asked.
- The CLI must remain based on `typer`.
- The GUI must remain based on `PyQt5 + VTK`.
- The project must remain usable without any native `fossils` bridge.

## Current architecture

- `src/fossils_vtu2obj/`
  - VTK conversion pipeline and CLI
- `src/fossils_vtu2obj/gui/`
  - PyQt5 + VTK GUI
- `src/fossils_vtu2obj/integrations/`
  - optional Python-facing integration boundary for a future `fossils` bridge
- `native/`
  - reserved placeholder for a future optional `C++ + SWIG` integration

## Technical decisions already made

- Texture strategy: use a **2D repeated palette texture**, not a diagonal-only
  texture.
- UV strategy: map the scalar field to `U`, keep `V` constant.
- Default preferred field: `stress_von_mises` when present.
- Default color bins: `16`.
- Current docs language: **English**.
- `README.md` is user-facing; it should not become a long implementation diary.

## Current product state

Implemented today:

- VTU inspection and array listing
- surface extraction
- scalar and textured VTK preview
- UV generation and palette texture generation
- OBJ/MTL/PNG export
- CLI commands: `inspect`, `list-arrays`, `preview`, `convert`, `gui`,
  `native-status`
- GUI with dual viewports, per-view display settings, recent files, clear
  views, and texture preview
- deterministic tests for the main non-GUI logic plus headless GUI coverage

## Known limits

- Only scalar arrays are supported for preview/export.
- The GUI uses cooperative cancellation; active VTK calls cannot be interrupted
  immediately.
- The optional native `fossils` bridge is not implemented yet.
- Windows-specific Qt/VTK behavior should be treated carefully when changing
  rendering lifecycle code.

## Documentation rules

- Keep `README.md` focused on users.
- Put detailed installation steps in `INSTALL.md`.
- Put technical structure in `docs/ARCHITECTURE.md`.
- Put current state and roadmap in `docs/PROJECT_STATUS.md`.
- Put longer AI-oriented continuity notes in `docs/AI_HANDOFF.md`.
- Archive historical prompt material instead of mixing it into active docs.

## Modification rules

- Prefer small, reviewable changes.
- Keep public behavior honest in the docs.
- Update documentation when user-visible behavior changes.
- Do not leave stale bootstrap-era text that no longer matches the repository.

## Short roadmap

- Continue improving GUI ergonomics and large-dataset behavior.
- Refine export fidelity and downstream DCC interoperability.
- Keep documentation aligned with the real project state.
- Add a native bridge only as an optional layer if it becomes worthwhile.
