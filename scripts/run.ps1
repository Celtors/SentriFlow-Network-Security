param([switch]$SystemProxy, [switch]$ApiOnly)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$arguments = @("-I", "-m", "sentriflow", "run")
if ($SystemProxy) { $arguments += "--system-proxy" }
if ($ApiOnly) { $arguments += "--api-only" }
& "$root\.venv\Scripts\python.exe" @arguments
exit $LASTEXITCODE
