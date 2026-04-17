# Project status

## Current state

The project is beyond bootstrap stage and currently provides a usable first
product milestone.

Stable and working today:

- VTU loading and inspection
- point-array and cell-array listing
- scalar field validation
- surface extraction with VTK
- scalar-colored preview
- textured preview
- palette texture PNG generation
- UV mapping from scalar fields
- OBJ/MTL/PNG export
- CLI commands for inspection, preview, conversion, and GUI launch
- PyQt5 + VTK GUI with dual viewport comparison
- recent files, clear views, texture preview, and per-view display controls

## Stable implementation choices

- core pipeline stays VTK-only,
- repeated palette texture instead of diagonal-only texture,
- scalar field encoded in UVs,
- `stress_von_mises` preferred by default when available,
- project remains Python-first,
- future `fossils` native bridge remains optional.

## Current limitations

- only scalar fields are supported for preview/export,
- vector and tensor arrays are inspectable but not directly usable,
- cancellation in the GUI is cooperative rather than immediate,
- Qt/VTK lifecycle details on Windows require care,
- the native `fossils` bridge is still a placeholder.

## Documentation debt now addressed

The repository now separates:

- user documentation,
- installation details,
- architecture notes,
- AI handoff memory,
- agent instructions.

This avoids mixing bootstrap history with user-facing guidance.

## Near-term priorities

- continue polishing the GUI for large datasets,
- improve export fidelity and downstream rendering behavior,
- keep examples and documentation aligned with real project behavior,
- prepare native integration only if a clear use case appears.
