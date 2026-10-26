<#
  SentriFlow repo scaffold (Build Plan, Section 3)

  Usage (from the ROOT of your cloned repo, after the Vite frontend exists):
      powershell -ExecutionPolicy Bypass -File <path>\scaffold-sentriflow.ps1

  Safe to re-run: existing non-empty files are never overwritten.
  The frontend/ files that Vite creates (package.json, tsconfig*, vite.config.ts,
  index.html, main.tsx, App.tsx, index.css) are intentionally NOT created here.
#>
param([string]$Root = (Get-Location).Path)
$ErrorActionPreference = "Stop"
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Ensure-File([string]$rel) {
    $p = Join-Path $Root $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $p -Parent) | Out-Null
    if (-not (Test-Path $p)) { New-Item -ItemType File -Path $p | Out-Null }
}

function Seed([string]$rel, [string]$content) {
    $p = Join-Path $Root $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $p -Parent) | Out-Null
    if (-not (Test-Path $p) -or (Get-Item $p).Length -eq 0) {
        [IO.File]::WriteAllText($p, ($content.Trim() + "`n"), $utf8)
    }
}

# ---------------------------------------------------------------- seeded files
Seed '.gitignore' @'
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
# Node
node_modules/
frontend/dist/
# Built frontend copied into the backend package
backend/src/sentriflow/web/
# Local secrets / runtime data (never commit)
.env
*.db
*.db-wal
*.db-shm
*.pem
*.key
*.log
state.json
ca/
# Downloaded intel
*.mmdb
# Editors / OS
.vscode/
.idea/
Thumbs.db
'@

Seed '.gitattributes' @'
* text=auto eol=lf
*.ps1 text eol=crlf
*.bat text eol=crlf
*.png binary
*.jpg binary
*.mmdb binary
'@

Seed '.editorconfig' @'
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4

[*.{ts,tsx,js,json,yml,yaml,css,html,md}]
indent_size = 2

[*.ps1]
end_of_line = crlf
'@

Seed '.env.example' @'
# Defaults, all bound to 127.0.0.1. No secrets belong in this file.
SENTRIFLOW_PROXY_PORT=8080
SENTRIFLOW_API_PORT=8787
SENTRIFLOW_HALT_TIMEOUT_SECONDS=30
SENTRIFLOW_LOG_LEVEL=INFO
'@

Seed '.pre-commit-config.yaml' @'
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
      - id: trailing-whitespace
      - id: check-yaml
'@

Seed 'README.md' @'
# SentriFlow

A local, secure-by-design network privacy guardian: see which applications send data,
where it goes and what it contains, and pause / allow / block it in real time.

Team Senklok - Techtonic UI 3.0 Hackathon (STASH).

See `docs/BUILD_PLAN.md` for structure, data contracts and the build plan,
and `docs/windows-setup.md` for setup (Windows 11).

## Quick start

    .\scripts\setup.ps1
    .\scripts\dev.ps1
'@

Seed 'CONTRIBUTING.md' @'
# Contributing

- `main` is always demo-able. Work on short-lived branches: `feat/<module>-<topic>`.
- Merge by pull request with at least one reviewer.
- Conventional commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- CI must pass (ruff, mypy, pytest, eslint, build).
- Any change in `backend/src/sentriflow/inspection/` or `core/` needs tests.
- `core/` and `inspection/` must never import from `api/`, `proxy/` or `os_adapters/`.
- Use dummy PII only in tests and demos.
'@

Seed '.github/PULL_REQUEST_TEMPLATE.md' @'
## What and why

## How was it tested

## Checklist
- [ ] Tests added or updated (required for `core/` and `inspection/`)
- [ ] No real personal data in fixtures or logs
- [ ] Docs updated if a contract (API / schema) changed
'@

Seed '.github/ISSUE_TEMPLATE/bug_report.md' @'
---
name: Bug report
about: Something is broken
labels: bug
---

**What happened**

**Expected**

**Steps to reproduce**
'@

Seed '.github/ISSUE_TEMPLATE/feature_task.md' @'
---
name: Feature / task
about: A piece of planned work
labels: task
---

**Goal**

**Module / role (R1-R4)**

**Done when**
'@

Seed '.github/workflows/ci-backend.yml' @'
name: ci-backend
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/pyproject.toml
      - run: python -m pip install -e "backend[dev]"
      - run: ruff check backend
      - run: ruff format --check backend
      - run: mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
      - run: pytest backend
'@

Seed '.github/workflows/ci-frontend.yml' @'
name: ci-frontend
on:
  push:
    branches: [main]
  pull_request:
jobs:
  build:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run build
'@

Seed 'backend/pyproject.toml' @'
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "sentriflow"
version = "0.1.0"
description = "Local, secure-by-design network privacy guardian"
requires-python = ">=3.12"
# TODO: pin exact versions after the Week-1 spike
dependencies = [
  "mitmproxy",
  "fastapi",
  "uvicorn[standard]",
  "pydantic",
  "pydantic-settings",
  "psutil",
  "aiosqlite",
  "geoip2",
  "winotify; sys_platform == 'win32'",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "httpx", "ruff", "mypy", "pre-commit"]
ml = ["scikit-learn"]

[project.scripts]
sentriflow = "sentriflow.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
sentriflow = ["data/**/*", "web/**/*", "storage/*.sql", "storage/migrations/*.sql"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
'@

Seed 'backend/README.md' @'
# SentriFlow backend

    python -m venv ..\.venv
    ..\.venv\Scripts\python -m pip install -e ".[dev]"
    ..\.venv\Scripts\python -m sentriflow --help
'@

Seed 'backend/src/sentriflow/__init__.py' '__version__ = "0.1.0"'

Seed 'backend/src/sentriflow/__main__.py' @'
import sys

from sentriflow.cli import main

if __name__ == "__main__":
    sys.exit(main())
'@

Seed 'backend/src/sentriflow/cli.py' @'
"""SentriFlow CLI: run | doctor | restore-proxy | install-ca | remove-ca | seed-demo | reset."""

import argparse

from sentriflow import __version__

COMMANDS = ["run", "doctor", "restore-proxy", "install-ca", "remove-ca", "seed-demo", "reset"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sentriflow")
    parser.add_argument("command", choices=COMMANDS, nargs="?", default="run")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)
    print(f"sentriflow {__version__}: '{args.command}' not implemented yet")
    return 0
'@

Seed 'backend/tests/unit/test_smoke.py' @'
from sentriflow import __version__


def test_version() -> None:
    assert __version__
'@

Seed 'scripts/setup.ps1' @'
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e "backend[dev]"

Push-Location frontend
npm ci
Pop-Location
'@

Seed 'scripts/dev.ps1' @'
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
'@

# ------------------------------------------- Python packages (init + modules)
$pkgs = [ordered]@{
    'core'                = 'models events decision_engine rule_engine halt_manager scoring'
    'proxy'               = 'runner addon process_resolver tls_status'
    'inspection'          = 'pipeline payload_extractor pii_patterns luhn custom_strings tracker_matcher masking'
    'anomaly'             = 'baseline iforest'
    'intel'               = 'blocklist_loader geoip'
    'storage'             = 'db'
    'storage/repositories' = 'flows rules alerts blocklist patterns settings'
    'api'                 = 'server security schemas ws'
    'api/routes'          = 'health flows processes halts rules patterns alerts blocklist score geo settings system'
    'os_adapters'         = 'base'
    'os_adapters/windows' = 'system_proxy cert_store file_acl firewall notifications paths elevation'
}
foreach ($k in $pkgs.Keys) {
    $base = "backend/src/sentriflow/$k"
    Ensure-File "$base/__init__.py"
    foreach ($m in $pkgs[$k].Split(' ')) { Ensure-File "$base/$m.py" }
}

# ------------------------------------------------------ remaining empty files
$list = @'
LICENSE
THIRD_PARTY_NOTICES.md
backend/src/sentriflow/config.py
backend/src/sentriflow/constants.py
backend/src/sentriflow/logging_setup.py
backend/src/sentriflow/storage/schema.sql
backend/src/sentriflow/storage/migrations/001_init.sql
backend/src/sentriflow/data/blocklists/.gitkeep
backend/src/sentriflow/data/geoip/.gitkeep
backend/tests/conftest.py
backend/tests/unit/test_luhn.py
backend/tests/unit/test_pii_patterns.py
backend/tests/unit/test_custom_strings.py
backend/tests/unit/test_tracker_matcher.py
backend/tests/unit/test_masking.py
backend/tests/unit/test_rule_engine.py
backend/tests/unit/test_decision_engine.py
backend/tests/unit/test_halt_manager.py
backend/tests/unit/test_scoring.py
backend/tests/integration/test_proxy_pipeline.py
backend/tests/integration/test_process_resolver.py
backend/tests/integration/test_api_security.py
backend/tests/integration/test_ws_events.py
backend/tests/integration/test_system_proxy_restore.py
backend/tests/fixtures/payloads/.gitkeep
backend/tests/fixtures/blocklist_sample.txt
frontend/.prettierrc
frontend/public/geo/.gitkeep
frontend/src/api/client.ts
frontend/src/api/ws.ts
frontend/src/api/types.ts
frontend/src/store/trafficStore.ts
frontend/src/store/haltStore.ts
frontend/src/store/alertStore.ts
frontend/src/store/settingsStore.ts
frontend/src/hooks/useLiveTraffic.ts
frontend/src/hooks/useHaltQueue.ts
frontend/src/pages/DashboardPage.tsx
frontend/src/pages/TrafficPage.tsx
frontend/src/pages/AlertsPage.tsx
frontend/src/pages/RulesPage.tsx
frontend/src/pages/BlocklistPage.tsx
frontend/src/pages/MapPage.tsx
frontend/src/pages/SettingsPage.tsx
frontend/src/components/layout/.gitkeep
frontend/src/components/halt/.gitkeep
frontend/src/components/traffic/.gitkeep
frontend/src/components/alerts/.gitkeep
frontend/src/components/map/.gitkeep
frontend/src/components/score/.gitkeep
frontend/src/components/common/.gitkeep
frontend/src/lib/format.ts
frontend/src/lib/constants.ts
frontend/src/__tests__/.gitkeep
demo/test-server/server.py
demo/pii-form/index.html
demo/seed/dummy_pii.json
demo/seed/custom_patterns.json
demo/demo-script.md
demo/backup/README.md
scripts/build.ps1
scripts/run.ps1
scripts/test.ps1
scripts/update-intel.ps1
scripts/restore-proxy.ps1
scripts/block-quic.ps1
scripts/unblock-quic.ps1
docs/architecture.md
docs/api.md
docs/threat-model.md
docs/privacy-and-consent.md
docs/windows-setup.md
docs/testing.md
docs/proposal/FPH_Senklok.md
docs/proposal/references.md
docs/proposal/diagrams/system-architecture.mmd
docs/proposal/diagrams/halt-workflow.mmd
docs/proposal/diagrams/use-case.mmd
docs/proposal/diagrams/database-erd.mmd
docs/proposal/diagrams/api-architecture.mmd
'@
foreach ($f in ($list -split "`r?`n")) {
    if ($f.Trim()) { Ensure-File $f.Trim() }
}

$count = (Get-ChildItem -Path $Root -Recurse -File -Force |
    Where-Object { $_.FullName -notmatch '\\(\.git|node_modules)\\' }).Count
Write-Host "Scaffold done. $count files under $Root" -ForegroundColor Green
