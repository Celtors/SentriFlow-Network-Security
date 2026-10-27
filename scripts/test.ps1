$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -I -m ruff check backend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py -I -m ruff format --check backend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py -I -m mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $py -I -m pytest backend -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location frontend
try {
    npm run lint
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
