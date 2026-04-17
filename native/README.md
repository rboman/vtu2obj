# Native extension placeholder

This directory is reserved for a future optional `C++ + SWIG` bridge related to
the `fossils` solver.

Current expectations:

- the native bridge stays optional,
- the VTK conversion pipeline remains implemented in Python,
- the main package and CLI keep working when nothing in `native/` is built.

If the native integration becomes real later, this directory can host:

- SWIG interface files,
- C++ bridge code,
- optional CMake files,
- and packaging glue for a compiled extension.
