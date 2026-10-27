$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

$backend = Start-Process $py -ArgumentList "-I", "-m", "sentriflow", "run" `
    -WorkingDirectory $root -NoNewWindow -PassThru
try {
    Push-Location (Join-Path $root "frontend")
    npm run dev
    if ($LASTEXITCODE -ne 0) { throw "The frontend development server exited with an error." }
}
finally {
    Pop-Location
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id }
}
