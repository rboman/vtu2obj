<#
Build script for Windows packaging (PyInstaller + Inno Setup).

Quick start (from the repository root):
    powershell -ExecutionPolicy Bypass -File build_installer.ps1

Useful variants:
    # Build only the installer from an existing dist/
    powershell -ExecutionPolicy Bypass -File build_installer.ps1 -SkipPyInstaller

    # Build only PyInstaller outputs (skip Inno Setup)
    powershell -ExecutionPolicy Bypass -File build_installer.ps1 -SkipInno

Prerequisites:
    - Python environment with project deps installed (including pyinstaller)
    - Inno Setup 6 (ISCC.exe), installed or available in PATH

Outputs:
    - dist/fossils_vtu2obj
    - dist/installer
#>

param(
    [switch]$SkipPyInstaller,
    [switch]$SkipInno
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptRoot

function Invoke-Step {
    param(
        [string]$Title,
        [scriptblock]$Action
    )
    Write-Host "`n=== $Title ===" -ForegroundColor Cyan
    & $Action
}

if (-not $SkipPyInstaller) {
    Invoke-Step -Title "Building executables with PyInstaller" -Action {
        pyinstaller fossils_vtu2obj.spec --clean --noconfirm
    }
}

if (-not $SkipInno) {
    Invoke-Step -Title "Building installer with Inno Setup" -Action {
        $isccPaths = @(
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
        )

        $iscc = $null
        foreach ($candidate in $isccPaths) {
            if (Test-Path $candidate) {
                $iscc = $candidate
                break
            }
        }

        if (-not $iscc) {
            $resolved = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($resolved) {
                $iscc = $resolved.Source
            }
        }

        if (-not $iscc) {
            throw "Inno Setup compiler (ISCC.exe) not found. Install Inno Setup 6 or add ISCC.exe to PATH."
        }

        & $iscc installer.iss
    }
}

Write-Host "`nBuild complete." -ForegroundColor Green
Write-Host "- PyInstaller output: dist/fossils_vtu2obj" -ForegroundColor Green
Write-Host "- Installer output: dist/installer" -ForegroundColor Green
