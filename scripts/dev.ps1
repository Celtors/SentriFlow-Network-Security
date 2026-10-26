$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

$backend = Start-Process $py -ArgumentList "-m", "sentriflow", "run" `
    -WorkingDirectory $root -PassThru
try {
    Push-Location (Join-Path $root "frontend")
    npm run dev
}
finally {
    Pop-Location
    if (-not $backend.HasExited) { Stop-Process -Id $backend.Id }
}
