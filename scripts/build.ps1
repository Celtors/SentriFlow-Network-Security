$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
Push-Location (Join-Path $root 'frontend')
try {
    npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
} finally { Pop-Location }
$web = Join-Path $root 'backend\src\sentriflow\web'
New-Item -ItemType Directory -Force -Path $web | Out-Null
# Copy only; never delete user files or recursively remove computed paths.
Copy-Item -Path (Join-Path $root 'frontend\dist\*') -Destination $web -Recurse -Force
Write-Output 'Built frontend copied into the backend web package.'
