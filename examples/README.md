# Example datasets

This directory contains real VTU files used to demonstrate and smoke-test the
project.

## `beam3d.vtu`

- Main demonstration dataset for CLI and GUI examples
- Useful scalar fields include:
  - `stress_von_mises`
  - `strain_von_mises`
  - `cell_stress_von_mises`
  - `cell_strain_von_mises`
- Good default file to test inspection, preview, and export workflows

## `doli.vtu`

- Additional real-world smoke-test dataset
- Useful to confirm that default field selection still prefers
  `stress_von_mises` when present
- Good regression target for GUI loading and example-based tests
