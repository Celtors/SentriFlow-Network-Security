$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root '.venv\Scripts\python.exe'
& $py -m ruff check backend
if ($LASTEXITCODE -ne 0) { throw 'Ruff lint failed' }
& $py -m ruff format --check backend
if ($LASTEXITCODE -ne 0) { throw 'Ruff formatting failed' }
& $py -m mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
if ($LASTEXITCODE -ne 0) { throw 'Domain type checking failed' }
& $py -m pytest backend
if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
npm --prefix frontend run lint
if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed' }
npm --prefix frontend run test
if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
