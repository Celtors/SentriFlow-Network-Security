# SentriFlow

A local HTTP/HTTPS privacy checkpoint: inspect outgoing requests, pause sensitive transfers,
and allow or block them through an authenticated local API and WebSocket.

The primary deployment target is **Windows 11 x64, Python 3.12 and Node.js 22**. The backend
also runs on Linux for development with an explicit proxy. Windows routing and certificate
trust remain Windows adapters. The repository architecture is documented in
[SentriFlow_Build_Plan.md](SentriFlow_Build_Plan.md).

Audric Yusuf Maynard Simatupang's assignments follow the **named R2 assignments in the
7-day tracker**, which differ from the generic role numbering in the build plan.
[Implementation status and evidence](docs/audric-worklog.md) records the handoff.

On Windows, from the repository root:

```powershell
.\scripts\setup.ps1                 # Python venv, backend/dev dependencies, npm ci
.\scripts\run.ps1                   # Proxy :8080 and API :8787, loopback only
# Optional Windows actions, performed explicitly:
.\.venv\Scripts\python.exe -I -m sentriflow install-ca --consent
.\scripts\run.ps1 -SystemProxy      # Route apps that honor Windows system proxy
```

Installing the CA lets SentriFlow inspect HTTPS on your own device. It creates a per-install
key and trusts only its certificate in the current-user store. No trust or OS routing changes
happen during normal startup. Stop the running instance before starting another.

The console prints a launch URL containing a per-run token in its fragment. Use that token
as `X-SentriFlow-Token` for REST. WebSockets use subprotocols `['sentriflow', token]` and an
allowed local Origin. See the [API contract](docs/api.md) and [Windows guide](docs/windows-setup.md).

R4's dashboard includes traffic, Halt decisions, rules, alerts, settings and an offline vector
map. `scripts/dev.ps1` runs both services; open
`http://127.0.0.1:3000/#token=<token printed by backend>` during UI development.
`scripts/build.ps1` packages the dashboard for the single-process backend server. The printed
launch URL signs in automatically; the login form also accepts the token from its fragment.

For Linux backend development:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'backend[dev]'
.venv/bin/python -I -m sentriflow run
```

Validate or reproduce the offline backend rehearsal:

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe -I -m sentriflow.verification --output docs/evidence/kpis.json
```

The [test guide](docs/testing.md) explains the measurement limits. Automated rehearsal uses
temporary HTTP/HTTPS servers and dummy PII; it never trusts a CA or changes system routing.

After a crash, recover Windows routing and remove CA trust when finished:

```powershell
.\scripts\restore-proxy.ps1
.\.venv\Scripts\python.exe -I -m sentriflow remove-ca
```

Country lookup uses a manually installed local MMDB and bundled map shapes. Missing data is
reported explicitly; the app never downloads it or uses online tiles. R3's bundled blocklist
loader and R4's explicit `--import-blocklist` command share domain validation. Anomaly detection,
native Windows acceptance, a representative KPI session, and a backup recording remain pending.
See [the R4 merge notes](docs/merge-r4.md) for the shared contracts and preserved branch evidence.
