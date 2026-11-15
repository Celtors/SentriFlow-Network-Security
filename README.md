# SentriFlow

A local browsing companion with trained phishing-risk estimates and an HTTP/HTTPS privacy
checkpoint: understand observed websites, inspect outgoing requests and pause sensitive transfers.

The `reform` branch adds a compact default view with actual calibrated ML inference. **Explore
details** opens website/privacy evidence and the existing traffic, rules, alerts, map and Settings.
The top-right arrow opens a small separate browser window; always-on-top is controlled by your OS.
Black/papaya-orange styling, one frontend, no browser extension. The model ships with the app;
ordinary users do **not** need a dataset, sklearn or a training run.

See [CURRENT_STATE.md](CURRENT_STATE.md) for delivery/test status and
[the model card](docs/ml-model.md) for dataset attribution, features, evaluation and limitations.

The primary deployment target is **Windows 11 x64, Python 3.12 and Node.js 22**. The backend
also runs on Linux for development with an explicit proxy. Windows routing and certificate
trust remain Windows adapters. The repository architecture is documented in
[SentriFlow_Build_Plan.md](SentriFlow_Build_Plan.md).

R1's proxy/Windows work, R2's backend and Halt engine, R3's inspection/data work, and
R4's dashboard now run as one application. See the [current implementation status](docs/implementation-status.md)
and [integrated run/check guide](docs/integration.md). The original named assignments and
earlier evidence remain in [Audric's worklog](docs/audric-worklog.md).

On Windows, from the repository root:

```powershell
.\scripts\setup.ps1                 # Python venv, backend/dev dependencies, npm ci
.\scripts\build.ps1                 # Package the dashboard into the backend
.\scripts\run.ps1                   # Proxy :8080 and API :8787, loopback only
# Optional Windows actions, performed explicitly:
.\.venv\Scripts\python.exe -I -m sentriflow install-ca --consent
.\scripts\run.ps1 -SystemProxy      # Route apps that honor Windows system proxy
```

Open the printed launch URL. In the compact view, use **Review capture settings** to configure
browser routing and certificate trust. Watching YouTube only produces updates if its traffic
passes through the proxy; clients bypassing Windows proxy settings or using an unproxied transport
are outside capture. The app follows the **latest observed page**, not the focused browser tab.

Installing the CA lets SentriFlow inspect HTTPS on your own device. It creates a per-install
key and trusts only its certificate in the current-user store. No trust or OS routing changes
happen during normal startup. Stop the running instance before starting another.

The console prints a launch URL containing a per-run token in its fragment. Use that token
as `X-SentriFlow-Token` for REST. WebSockets use subprotocols `['sentriflow', token]` and an
allowed local Origin. See the [API contract](docs/api.md) and [Windows guide](docs/windows-setup.md).

The expanded dashboard includes website analysis, traffic, Halt decisions, rules, alerts, settings and an offline vector
map. `scripts/dev.ps1` runs both services; open
`http://127.0.0.1:3000/#token=<token printed by backend>` during UI development.
`scripts/build.ps1` packages the dashboard for the single-process backend server. The printed
launch URL signs in automatically; the login form also accepts the token from its fragment.

For Linux backend development:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'backend[dev]'
npm --prefix frontend ci
.venv/bin/python -I scripts/build.py
.venv/bin/python -I -m sentriflow run
```

Validate or reproduce the offline backend rehearsal:

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe -I -m sentriflow.verification --output docs/evidence/kpis.json
```

The [test guide](docs/testing.md) explains the measurement limits. Automated rehearsal uses
temporary HTTP/HTTPS servers and dummy PII; it never trusts a CA or changes system routing.

For real rendered UI and live-model verification with installed Microsoft Edge:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "backend[browser]"
.\.venv\Scripts\python.exe -I scripts/check-reform.py
.\.venv\Scripts\python.exe -I scripts/check-browser.py --evidence-dir docs/evidence/reform/legacy
```

The first check routes public-shaped fixture names only to local test origins; it does not
visit those public websites. Both checks preserve OS routing and CA trust.

The percentage is a Random Forest's phishing output with isotonic calibration, trained using
13 numeric domain/scheme features from UCI PhiUSIIL (CC BY 4.0). It is an address-based estimate,
not a guarantee or a verdict about all malware. Domain age, permissions and page behavior are
not learned inputs. Browser headers, cookie presence, static form structure and third-party
destinations are separate redacted observations; camera/microphone/location requests,
fingerprinting execution and browser-storage reads explicitly remain unobservable here.

After a crash, recover Windows routing and remove CA trust when finished:

```powershell
.\scripts\restore-proxy.ps1
.\.venv\Scripts\python.exe -I -m sentriflow remove-ca
```

Country lookup uses a manually installed local MMDB and bundled map shapes. Missing data is
reported explicitly; the app never downloads it or uses online tiles. R3's bundled blocklist
loader and R4's explicit `--import-blocklist` command share domain validation. Anomaly detection,
native Windows acceptance, a representative KPI session, and a backup recording remain pending.
See [the integrated run and verification guide](docs/integration.md) for the shared contracts and preserved branch evidence.
