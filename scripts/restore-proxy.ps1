$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root '.venv\Scripts\python.exe') -m sentriflow restore-proxy @args
if ($LASTEXITCODE -ne 0) { throw 'Proxy restoration failed; recovery journal was preserved' }
