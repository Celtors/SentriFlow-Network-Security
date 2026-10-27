param(
    [switch]$SystemProxy,
    [switch]$ApiOnly,
    [string]$DataDir,
    [int]$ApiPort,
    [int]$ProxyPort
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$arguments = @("-I", "-m", "sentriflow", "run")
if ($SystemProxy) { $arguments += "--system-proxy" }
if ($ApiOnly) { $arguments += "--api-only" }
if ($DataDir) { $arguments += @("--data-dir", $DataDir) }
if ($ApiPort) { $arguments += @("--api-port", "$ApiPort") }
if ($ProxyPort) { $arguments += @("--proxy-port", "$ProxyPort") }
& "$root\.venv\Scripts\python.exe" @arguments
exit $LASTEXITCODE
