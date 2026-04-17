# Installation instructions for `fossils-vtu2obj`

These steps install the project from GitHub in an isolated Python environment.

## Requirements

* Python 3.10 or newer
* Git installed
* Internet access to download Python packages

## Recommended installation method: use a virtual environment

Using a virtual environment keeps this project isolated from other Python installations on your computer.

### 1. Open a terminal

On Windows, you can use:

* PowerShell
* Command Prompt

### 2. Clone the repository

```bash
git clone https://github.com/rboman/vtu2obj.git
cd vtu2obj
```

### 3. Create a virtual environment

```bash
python -m venv .venv
```

### 4. Activate the virtual environment

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

On Windows Command Prompt:

```bat
.venv\Scripts\activate.bat
```

On Linux or macOS:

```bash
source .venv/bin/activate
```

After activation, your terminal should usually show `(.venv)` at the beginning of the prompt.

### 5. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 6. Install the project

Install the standard command-line version:

```bash
pip install .
```

If you also want the graphical interface dependencies:

```bash
pip install ".[gui]"
```

If you want development tools as well:

```bash
pip install ".[dev]"
```

If you want everything:

```bash
pip install ".[gui,dev]"
```

## 7. Check that the installation works

Run:

```bash
fossils-vtu2obj --help
```

If that works, the package is installed correctly.

## 8. Example usage

Once installed, the command-line tool is available as:

```bash
fossils-vtu2obj
```

You can display the help with:

```bash
fossils-vtu2obj --help
```

## Updating the project later

If you already cloned the repository and want the latest version:

```bash
git pull
pip install --upgrade .
```

## Optional: developer installation

If you plan to modify the source code yourself, install it in editable mode:

```bash
pip install -e ".[gui,dev]"
```

This is mainly useful for development, not for normal usage.

## Leaving the environment

When you are done, deactivate the virtual environment:

```bash
deactivate
```

## Notes for Windows users

If PowerShell blocks the activation script, you can either:

* use Command Prompt instead of PowerShell, or
* allow local scripts in PowerShell for your user session

A simple workaround is to use:

```bat
.venv\Scripts\activate.bat
```

from Command Prompt.

## Quick install summary

```bash
git clone https://github.com/rboman/vtu2obj.git
cd vtu2obj
python -m venv .venv
# activate the environment 
.venv\Scripts\activate # (Windows)
python -m pip install --upgrade pip
pip install .[gui]
fossils-vtu2obj gui
```
