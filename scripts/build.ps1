$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
& "$root\.venv\Scripts\python.exe" -I "$root\scripts\build.py"
exit $LASTEXITCODE
