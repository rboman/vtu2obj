# Native bridge placeholder

This directory is reserved for a future optional `C++ + SWIG` bridge related to
the `fossils` solver.

Current status:

- nothing in this directory is required to run the project,
- the main VTU-to-OBJ pipeline is implemented in Python with VTK,
- the CLI and GUI must keep working even when no native module exists.

If a native integration becomes necessary later, this directory may host:

- SWIG interface files,
- C++ bridge code,
- optional CMake files,
- packaging glue for a compiled extension.
