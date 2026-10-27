# SentriFlow backend

Run commands from the repository root. Requires Python 3.12; see the root README for Windows
setup. Install with `python -m pip install -e 'backend[dev]'` in a virtual environment.

`python -I -m sentriflow run` starts embedded mitmproxy and FastAPI on one asyncio loop.
`--api-only` starts the transport without interception. `--system-proxy` opts into Windows
per-user routing after both listeners start. Ports, timeout and the runtime directory use
`SENTRIFLOW_*` environment variables; `--data-dir PATH` overrides the runtime directory.

Commands: `run`, `doctor`, `restore-proxy`, `install-ca --consent`, `remove-ca`, `seed-demo`,
and `reset --confirm`. Stop the service before reset. Reset removes the local database;
CA trust is removed separately by thumbprint.

`core/` and `inspection/` contain domain models, policies and inspectors. `application.py`
wires them to repositories. `proxy/` translates mitmproxy flows into masked metadata and
awaits independent Halt futures. `api/` exposes the same runtime through REST and WebSocket.
`os_adapters/windows/` contains registry, WinINET, current-user CA and key-directory ACL code.

R4's `runtime.py` and `launcher.py` import paths delegate to this same runtime and lifecycle.
`GET /api/snapshot` initializes/resynchronizes the dashboard; the WebSocket uses the same
session token in the `sentriflow` subprotocol handshake. Download counters stream before
completion. Offline country aggregation uses observed IPs and the local MMDB only.

Build with `scripts/build.ps1` before the production-style run. Open the printed fragment-token
URL or paste its token into the dashboard login form. CLI port overrides (`--api-port`,
`--proxy-port`) and explicit `--import-blocklist PATH` are supported. Existing schema-v1 data
upgrades transactionally to schema v2; do not replace the original migration with another
branch's schema. See [merge-r4.md](../docs/merge-r4.md).

Unit and integration tests: `python -I -m pytest backend -q`. The real HTTP/HTTPS rehearsal
also runs as `python -I -m sentriflow.verification`. It requires the `[dev]` dependencies.

Validated runtime versions are recorded in [the worklog](../docs/audric-worklog.md).
