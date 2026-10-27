$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path ".venv")) { python -m venv .venv }
if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { throw 'Python 3.12+ is required' }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
if ($LASTEXITCODE -ne 0) { throw 'Backend installation failed' }

Push-Location frontend
npm ci
if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed' }
Pop-Location
