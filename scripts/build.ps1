$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location (Join-Path $root "frontend")
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally { Pop-Location }
$web = Join-Path $root "backend\src\sentriflow\web"
if (Test-Path $web) { Remove-Item $web -Recurse -Force }
New-Item $web -ItemType Directory -Force | Out-Null
Copy-Item "$root\frontend\dist\*" $web -Recurse -Force
