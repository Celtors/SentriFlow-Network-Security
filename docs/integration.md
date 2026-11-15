# R1–R4 integrated application

`reform` extends this integration with a shipped calibrated domain-risk model, live website
summaries and a compact default UI. The latest task/status is [CURRENT_STATE.md](../CURRENT_STATE.md);
the original role allocation is historical. [Model documentation](ml-model.md) records the
actual dataset, license, feature schema, evaluation and calibration limits.

The merged role implementations now share `application.Runtime`, Pydantic contracts, SQLite
repositories and one API/proxy event loop. `runtime.py` and `launcher.py` are compatibility
imports, not parallel applications. Ports and module boundaries follow the existing build plan.

| Contribution | Connected implementation |
| --- | --- |
| R1 proxy / Windows work | Embedded listener, socket attribution, CA/routing adapters, recovery and standalone spike |
| R2 backend / Halt work | Composition, REST/WS, rules, independent holds, explicit control and shutdown lifecycle |
| R3 detection / data work | Inspector, blocklist parsing/loading, SQLite repositories, privacy-at-rest and security checks |
| R4 interface / evidence work | Dashboard, live queues/rates, rules/alerts/settings, local geography, figures and proposal export |

## Start the combined app

Windows, from the repository root:

```powershell
.\scripts\setup.ps1
.\scripts\build.ps1
.\scripts\run.ps1
```

Open the printed URL; the fragment token signs the dashboard in. It can also be pasted into
the login form. Routing and CA trust remain explicit Settings/CLI actions. To use a different
proxy port, for example after Windows denies 8080, run `scripts\run.ps1 -ProxyPort 8081`.
`-ApiPort`, `-DataDir`, `-ApiOnly` and `-SystemProxy` use the same backend configuration.

Linux development:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e 'backend[dev,browser]'
npm --prefix frontend ci
.venv/bin/python -I scripts/build.py
.venv/bin/python -I -m sentriflow run
```

`python scripts/build.py` is the common packager behind `build.ps1`. Stop the running app
before replacing its build. For Vite development use `scripts/dev.ps1`: the backend launch
URL stays visible, and Vite reads `SENTRIFLOW_API_PORT` instead of assuming a different target.
The default dev port remains 3000; its API/WS target defaults to 8787.

## End-to-end data path

A proxy client is resolved using its source IP/port and the configured proxy port. Inspection
uses the current patterns and a cached domain matcher; repository updates invalidate the
matcher. Blocklist files have their own configuration path independent of the optional MMDB.
A risk enters its own Halt future. A user decision, timeout, capacity limit or shutdown settles
it; silence never forwards the payload. Allowed response chunks update rates before completion.
Masked metadata, alerts and the disclosed score reach the same dashboard state.

Binary request bodies are excluded from text inspection and do not trigger Halt just
because they are binary. Their URL/headers, tracker policy and saved rules still apply;
an independent unknown-process large-upload trigger can also pause them. Traffic shows
the excluded-body note and `not_inspected` status without creating a privacy alert for
every binary request. The app does not claim to detect PII inside excluded bodies.
Malformed or unsupported text payloads retain the existing Halt behavior.
After updating this backend, stop and restart SentriFlow to clear old pending holds and
use the new policy. A frontend rebuild or model retraining is not required.

The same intercepted request now calls `WebsiteMonitor`: navigation metadata identifies an
observed page, numeric domain features feed the shipped Random Forest in a worker thread,
and `website.updated` updates the compact card. Background traffic does not replace a known
page. Referrer/Origin host and process associate related destinations, with same-host-tab
ambiguity disclosed. A bounded response tee extracts static form types/action hostnames
without changing forwarded bytes or retaining body/value strings. It respects the inspection
toggle; unsupported encodings and absent payloads are unavailable. It never injects browser
scripts or claims to observe JS permission/storage/fingerprinting calls.

The model is advisory: existing Halt/rules/tracker policies remain the enforcement authority.
Missing/corrupt model artifacts disable only the estimate. Session website state is bounded
in memory; it does not add a new database containing URLs or browser secrets.

The first authenticated WebSocket status contains a snapshot produced after subscribing to
the event bus, then queued changes follow. Reloading/reconnecting restores pending holds.
Rule/pattern/settings changes notify other connected clients. Late snapshots and events from
disconnected clients cannot overwrite a newer held-flow state. Custom pattern values are
stored locally but omitted from public snapshots and update events.

The application, rather than Uvicorn, owns shutdown signals. It blocks pending holds, restores
Windows routing before listener teardown, drains service hooks while SQLite is open, then
closes the database and releases the session lock. Seed/reset refuse a live data directory.
Blocklist import happens inside the same startup ownership lock. Forced kills still rely on
the watchdog/recovery snapshot; real Windows acceptance remains separate.

## Verify the integration

The earlier [validation record](evidence/integration/validation.json) records 163 passing
backend tests, 11 passing frontend tests, all static/build checks, and the real browser run.
For current reform results see [CURRENT_STATE.md](../CURRENT_STATE.md) and
`docs/evidence/reform/`. Do not interpret the older record as validation of the new model/UI.

Run `scripts/test.ps1` on Windows. Equivalent portable gates:

```bash
.venv/bin/python -I -m ruff check backend
.venv/bin/python -I -m ruff format --check backend
.venv/bin/python -I -m mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
.venv/bin/python -I -m pytest backend -q
npm --prefix frontend run lint
npm --prefix frontend run test
npm --prefix frontend run build
.venv/bin/python -I scripts/build.py --skip-build
```

Rehearse the rendered application with an installed local Chrome:

```bash
.venv/bin/python -I scripts/check-browser.py --browser-path /usr/bin/google-chrome --evidence-dir docs/evidence/integration
```

On Windows omit `--browser-path` to use Edge. The script owns its temporary backend/origin
processes and never installs a CA or changes routing. It makes no external request unless
`--public-map-check` is explicitly supplied. The report retains driver-roundtrip timings and
records DOM-click-to-response timings separately, including browser evaluation overhead.
An earlier concurrent benchmark report is retained to expose host-load variation.

The generated proposal remains a working draft. Rebuild its diagrams and PDF after changing
contracts with `scripts/export-proposal.py` (use `--browser-path` on Linux). Its exporter
blocks external requests and writes page count/hash/provenance to `proposal/export-report.json`.

The optional MMDB and real feeds are not bundled in a fresh clone. Missing MMDB data is
reported in the UI; the offline country shapes still render. Native Windows/long-run acceptance,
participant research, final review and backup video remain outside these local automated results.
