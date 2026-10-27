$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
& (Join-Path $root '.venv\Scripts\python.exe') -m sentriflow run @args
if ($LASTEXITCODE -ne 0) { throw 'SentriFlow exited with an error' }
