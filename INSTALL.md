# Installation

This document covers full installation and packaging workflows for
`fossils-vtu2obj`.

## Requirements

- Python 3.10 or newer
- Git
- Internet access to download Python packages

## Recommended setup

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/rboman/vtu2obj.git
cd vtu2obj
python -m venv .venv
```

Activate it:

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

Linux or macOS:

```bash
source .venv/bin/activate
```

Upgrade `pip`:

```bash
python -m pip install --upgrade pip
```

## Installation modes

Standard CLI install:

```bash
pip install .
```

GUI install:

```bash
pip install ".[gui]"
```

Development tools:

```bash
pip install ".[dev]"
```

Editable development install with GUI:

```bash
pip install -e ".[gui,dev]"
```

## Verify the installation

Check the CLI:

```bash
fossils-vtu2obj --help
```

Check the GUI command:

```bash
fossils-vtu2obj gui
```

## Updating an existing checkout

```bash
git pull
pip install --upgrade .
```

For an editable environment:

```bash
pip install -e ".[gui,dev]"
```

## Windows notes

If PowerShell blocks script execution, either use Command Prompt or allow local
scripts for your user session.

A simple Command Prompt fallback is:

```bat
.venv\Scripts\activate.bat
```

## Packaging a Windows installer

The repository includes:

- `build_installer.ps1`
- `fossils_vtu2obj.spec`
- `installer.iss`

These support a Windows packaging workflow based on **PyInstaller** and
**Inno Setup**.

### Packaging prerequisites

- install the project with GUI and development extras:

```bash
pip install -e ".[gui,dev]"
```

- install Inno Setup 6 so that `ISCC.exe` is available

### Build everything

```powershell
powershell -ExecutionPolicy Bypass -File build_installer.ps1
```

### Useful variants

Only rebuild the setup executable:

```powershell
powershell -ExecutionPolicy Bypass -File build_installer.ps1 -SkipPyInstaller
```

Only rebuild the PyInstaller application bundle:

```powershell
powershell -ExecutionPolicy Bypass -File build_installer.ps1 -SkipInno
```

### Packaging outputs

- `dist/fossils_vtu2obj/`
  - `fossils-vtu2obj.exe`
  - `fossils-vtu2obj-gui.exe`
- `dist/installer/`
  - generated setup executable

### Packaging note

The PyInstaller specification in this repository is configured to avoid common
Windows antivirus false positives related to UPX-compressed binaries.

## Leaving the environment

```bash
deactivate
```
