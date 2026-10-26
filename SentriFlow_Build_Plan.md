# SentriFlow — Repository Structure & Build Plan

**Team Senklok · Techtonic UI 3.0 Hackathon (STASH)**
**Target platform:** Windows 11 · **Backend:** Python · **Frontend:** Node (React)

---

## 1. Purpose of this document

This file defines (1) the full repository layout, (2) what each module is responsible for, (3) the data contracts between components, and (4) a phased build plan that matches the hackathon timeline (MVP build 1–14 Nov, stabilisation 15–20 Nov). It is meant to live in the repo as `docs/BUILD_PLAN.md`.

---

## 2. Locked-in technical decisions

| Area | Decision | Notes |
|---|---|---|
| OS | Windows 11 (x64) | All OS-specific code isolated in `os_adapters/windows/` |
| Backend language | Python 3.12 | `venv` + `pyproject.toml`; install with `pip install -e ".[dev]"` |
| Frontend runtime | Node.js 22 LTS (20 LTS also fine) | Vite + React 18 + TypeScript |
| Proxy engine | mitmproxy (addon API), **embedded in-process** | One asyncio loop shared with FastAPI → simple hold/release of requests |
| API | FastAPI + uvicorn, REST + one WebSocket | Binds to `127.0.0.1` only |
| Storage | SQLite (WAL mode) | Local only, under `%LOCALAPPDATA%\SentriFlow\` |
| Process attribution | `psutil` (source port → PID → exe) | `AccessDenied` handled gracefully |
| UI | React, Tailwind CSS, Recharts, Leaflet, Zustand | Map uses a **bundled GeoJSON**, not online tiles (online tiles would leak data to a third party and contradict "local-only") |
| Threat data | StevenBlack hosts, EasyPrivacy, offline GeoIP `.mmdb` | Refreshed by a script, never silently at runtime |
| AI extension | Rule-based per-process baseline; optional scikit-learn IsolationForest | Optional extra: `pip install -e ".[ml]"` |

**Default ports (all on 127.0.0.1):** proxy `8080` · API + dashboard `8787` · Vite dev server `3000` (proxies `/api` and `/ws` to `8787`).

**Runtime data (never in git):** `%LOCALAPPDATA%\SentriFlow\` → `sentriflow.db`, `ca\` (per-install CA), `logs\`, `state.json` (original proxy settings for crash recovery).

**Process model:** one Python process runs (a) mitmproxy `DumpMaster`, (b) uvicorn serving FastAPI, (c) a 1 s ticker for speed stats. In production the built frontend (`frontend/dist`) is served by FastAPI as static files, so the user opens a single URL.

---

## 3. Repository structure

```
sentriflow/
├── README.md                         # What it is, quick start, demo GIF
├── LICENSE
├── THIRD_PARTY_NOTICES.md            # Blocklist / GeoIP / library licences
├── CONTRIBUTING.md                   # Branching, commit style, review rules
├── .gitignore
├── .gitattributes                    # Line-ending rules (Windows)
├── .editorconfig
├── .env.example                      # Ports, timeouts, log level (no secrets)
├── .pre-commit-config.yaml           # ruff, prettier, eslint hooks
│
├── .github/
│   ├── workflows/
│   │   ├── ci-backend.yml            # windows-latest: ruff, mypy, pytest
│   │   └── ci-frontend.yml           # eslint, tsc, vitest, vite build
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_task.md
│
├── backend/
│   ├── pyproject.toml                # deps, extras [dev] [ml], ruff/mypy/pytest config
│   ├── README.md
│   ├── src/
│   │   └── sentriflow/
│   │       ├── __init__.py
│   │       ├── __main__.py           # `python -m sentriflow`
│   │       ├── cli.py                # run | doctor | restore-proxy | install-ca | remove-ca | seed-demo | reset
│   │       ├── config.py             # pydantic-settings (ports, timeouts, paths)
│   │       ├── constants.py
│   │       ├── logging_setup.py      # masked, rotating file logs
│   │       │
│   │       ├── core/                 # Pure domain logic (no I/O, easy to unit-test)
│   │       │   ├── models.py         # Flow, Verdict, Finding, Rule, Alert (pydantic)
│   │       │   ├── events.py         # Typed event bus (flow.*, halt.*, alert.*)
│   │       │   ├── decision_engine.py# rules + findings -> ALLOW / BLOCK / HALT
│   │       │   ├── rule_engine.py    # match process/host/pattern, once vs always
│   │       │   ├── halt_manager.py   # pending-halt registry, futures, timeout=BLOCK
│   │       │   └── scoring.py        # transparent privacy score
│   │       │
│   │       ├── proxy/                # mitmproxy integration
│   │       │   ├── runner.py         # starts embedded DumpMaster on 127.0.0.1:8080
│   │       │   ├── addon.py          # request / response / tls_failed_client hooks
│   │       │   ├── process_resolver.py # client port -> PID -> name/exe (cached)
│   │       │   └── tls_status.py     # inspected | pinned (not inspected) | passthrough
│   │       │
│   │       ├── inspection/
│   │       │   ├── pipeline.py       # runs all inspectors, returns Findings
│   │       │   ├── payload_extractor.py # URL, headers, JSON/form/multipart, gzip/br
│   │       │   ├── pii_patterns.py   # email, card, (optional) Indonesian phone / NIK
│   │       │   ├── luhn.py
│   │       │   ├── custom_strings.py # user-defined sensitive strings / regex
│   │       │   ├── tracker_matcher.py# suffix-trie domain match against blocklists
│   │       │   └── masking.py        # masked samples for logs and UI
│   │       │
│   │       ├── anomaly/
│   │       │   ├── baseline.py       # rule-based per-process behaviour baseline
│   │       │   └── iforest.py        # optional IsolationForest (extra [ml])
│   │       │
│   │       ├── intel/
│   │       │   ├── blocklist_loader.py # parse hosts / EasyPrivacy -> SQLite
│   │       │   └── geoip.py          # offline .mmdb lookup, country + lat/lon
│   │       │
│   │       ├── storage/
│   │       │   ├── db.py             # connection, WAL, migrations runner
│   │       │   ├── schema.sql
│   │       │   ├── migrations/       # 001_init.sql, 002_...
│   │       │   └── repositories/
│   │       │       ├── flows.py
│   │       │       ├── rules.py
│   │       │       ├── alerts.py
│   │       │       ├── blocklist.py
│   │       │       ├── patterns.py
│   │       │       └── settings.py
│   │       │
│   │       ├── api/
│   │       │   ├── server.py         # FastAPI factory, static mount for frontend/dist
│   │       │   ├── security.py       # session token, Origin + Host check, no CORS
│   │       │   ├── schemas.py        # request/response models
│   │       │   ├── ws.py             # /ws broadcaster + halt.decide handler
│   │       │   └── routes/
│   │       │       ├── health.py
│   │       │       ├── flows.py
│   │       │       ├── processes.py
│   │       │       ├── halts.py
│   │       │       ├── rules.py
│   │       │       ├── patterns.py
│   │       │       ├── alerts.py
│   │       │       ├── blocklist.py
│   │       │       ├── score.py
│   │       │       ├── geo.py
│   │       │       ├── settings.py
│   │       │       └── system.py     # proxy on/off, CA status/install/remove
│   │       │
│   │       ├── os_adapters/          # NOT named "platform" (would shadow stdlib)
│   │       │   ├── base.py           # abstract interfaces
│   │       │   ├── __init__.py       # factory -> Windows implementation
│   │       │   └── windows/
│   │       │       ├── system_proxy.py  # winreg + wininet refresh, save/restore
│   │       │       ├── cert_store.py    # certutil -user add/remove by thumbprint
│   │       │       ├── file_acl.py      # icacls restrict CA key folder
│   │       │       ├── firewall.py      # optional: block UDP 443 (QUIC) via netsh
│   │       │       ├── notifications.py # toast fallback when prompt is unattended
│   │       │       ├── paths.py         # %LOCALAPPDATA% layout
│   │       │       └── elevation.py     # is_admin() / relaunch helper
│   │       │
│   │       ├── data/                 # bundled read-only data
│   │       │   ├── blocklists/       # stevenblack-hosts.txt, easyprivacy.txt (snapshots)
│   │       │   └── geoip/            # .gitkeep (the .mmdb is downloaded, not committed)
│   │       │
│   │       └── web/                  # copy of frontend/dist after build (gitignored)
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       │   ├── test_luhn.py
│       │   ├── test_pii_patterns.py
│       │   ├── test_custom_strings.py
│       │   ├── test_tracker_matcher.py
│       │   ├── test_masking.py
│       │   ├── test_rule_engine.py
│       │   ├── test_decision_engine.py
│       │   ├── test_halt_manager.py   # timeout -> BLOCK, once vs always
│       │   └── test_scoring.py
│       ├── integration/
│       │   ├── test_proxy_pipeline.py # local test server through the proxy
│       │   ├── test_process_resolver.py
│       │   ├── test_api_security.py   # bad Origin / missing token rejected
│       │   ├── test_ws_events.py
│       │   └── test_system_proxy_restore.py
│       └── fixtures/
│           ├── payloads/              # json/form/multipart samples with dummy PII
│           └── blocklist_sample.txt
│
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.ts                # dev port 3000, proxy /api + /ws -> :8787
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── eslint.config.js
│   ├── .prettierrc
│   ├── index.html
│   ├── public/
│   │   ├── favicon.svg
│   │   └── geo/world-countries.geojson   # offline map shapes
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── index.css
│       ├── api/
│       │   ├── client.ts             # fetch wrapper (adds session token)
│       │   ├── ws.ts                 # reconnecting WebSocket
│       │   └── types.ts              # mirrors backend schemas
│       ├── store/                    # Zustand
│       │   ├── trafficStore.ts
│       │   ├── haltStore.ts
│       │   ├── alertStore.ts
│       │   └── settingsStore.ts
│       ├── hooks/
│       │   ├── useLiveTraffic.ts
│       │   └── useHaltQueue.ts
│       ├── pages/
│       │   ├── DashboardPage.tsx     # live speed, top apps, score summary
│       │   ├── TrafficPage.tsx       # per-process table + flow drill-down
│       │   ├── AlertsPage.tsx
│       │   ├── RulesPage.tsx         # allow/block rules, custom patterns
│       │   ├── BlocklistPage.tsx
│       │   ├── MapPage.tsx
│       │   └── SettingsPage.tsx      # inspection toggle, timeout, CA + proxy control
│       ├── components/
│       │   ├── layout/               # Sidebar, Header, StatusBadge
│       │   ├── halt/                 # HaltModal, HaltCountdown, HaltBadge
│       │   ├── traffic/              # ProcessTable, SpeedChart, FlowDetail
│       │   ├── alerts/               # AlertList, SeverityPill
│       │   ├── map/                  # DestinationMap (Leaflet + GeoJSON)
│       │   ├── score/                # PrivacyScoreCard, ScoreBreakdown
│       │   └── common/               # Button, Card, Table, EmptyState
│       ├── lib/                      # format.ts (bytes, time), constants.ts
│       └── __tests__/                # Vitest + Testing Library
│
├── demo/
│   ├── test-server/                  # tiny local server that receives demo posts
│   │   └── server.py
│   ├── pii-form/
│   │   └── index.html                # form pre-filled with SEEDED DUMMY PII only
│   ├── seed/
│   │   ├── dummy_pii.json
│   │   └── custom_patterns.json
│   ├── demo-script.md                # step-by-step live demo + talking points
│   └── backup/
│       └── README.md                 # link to recorded backup video (not committed)
│
├── scripts/                          # PowerShell, run from repo root
│   ├── setup.ps1                     # create venv, pip install, npm ci
│   ├── dev.ps1                       # backend + Vite dev server together
│   ├── build.ps1                     # vite build -> backend/src/sentriflow/web
│   ├── run.ps1                       # production-style single-process run
│   ├── test.ps1                      # pytest + vitest + lint
│   ├── update-intel.ps1              # download blocklists / GeoIP (explicit, manual)
│   ├── restore-proxy.ps1             # emergency: restore original Windows proxy
│   ├── block-quic.ps1                # admin: block UDP 443 for demo
│   └── unblock-quic.ps1
│
└── docs/
    ├── BUILD_PLAN.md                 # this file
    ├── architecture.md
    ├── api.md                        # REST + WebSocket contract
    ├── threat-model.md               # trust boundaries, CA risk, mitigations
    ├── privacy-and-consent.md        # what is logged, what is masked
    ├── windows-setup.md              # Python/Node install, CA consent, proxy notes
    ├── testing.md                    # metrics + how each target is measured
    └── proposal/                     # Full Proposal (FPH_Senklok.pdf) sources
        ├── FPH_Senklok.md
        ├── references.md             # IEEE-style
        └── diagrams/
            ├── system-architecture.mmd
            ├── halt-workflow.mmd
            ├── use-case.mmd
            ├── database-erd.mmd
            └── api-architecture.mmd
```

> The five diagrams in `docs/proposal/diagrams/` map directly to the System Design section the Semifinal guideline asks for (architecture, workflow, use case, database design, API architecture).

---

## 4. Module responsibilities

| Module | Responsibility | Key interface |
|---|---|---|
| `proxy/addon.py` | Entry point for every request; builds a flow context, calls inspection and decision, holds or releases | `async request(flow)`, `response(flow)`, `tls_failed_client(data)` |
| `proxy/process_resolver.py` | Maps the client's source port to a process; caches by `(port)` for a few seconds | `resolve(port) -> ProcessInfo \| Unknown` |
| `inspection/pipeline.py` | Runs payload extraction, PII patterns, custom strings, tracker match | `analyze(ctx) -> list[Finding]` |
| `core/decision_engine.py` | Combines saved rules + findings + settings into a verdict | `evaluate(ctx, findings) -> ALLOW \| BLOCK \| HALT` |
| `core/halt_manager.py` | Keeps pending halts, awaits user decision, applies timeout | `async hold(ctx, timeout) -> Verdict`, `resolve(id, action, scope)` |
| `core/scoring.py` | Computes the privacy score from blocked leaks, trackers, allowed leaks | `score(events) -> Score + breakdown` |
| `storage/*` | Persistence only; no business logic | Repository classes per table |
| `api/*` | Thin transport layer; token + origin enforcement | REST + `/ws` |
| `os_adapters/windows/*` | Everything Windows-specific | Abstract interfaces in `base.py` |

**Dependency rule:** `core/` and `inspection/` never import from `api/`, `proxy/` or `os_adapters/`. This keeps the logic that the success targets depend on (PII detection, decisions) fully unit-testable.

---

## 5. Runtime flow (Halt workflow)

```
App ──HTTP/HTTPS──► mitmproxy (127.0.0.1:8080)
                      │  addon.request(flow)
                      ▼
          process_resolver  → PID / exe name
                      ▼
          inspection.pipeline → Findings (PII, tracker, custom string, size)
                      ▼
          decision_engine.evaluate()
              ├── saved rule matches ─────────► ALLOW / BLOCK
              ├── no findings, known process ─► ALLOW
              └── findings or unknown process ► HALT
                                                  │
                         halt_manager.hold()  ──► WebSocket "halt.requested" ─► React HaltModal
                                                  │        (+ toast if tab unattended)
                         user: Allow/Block, once/always  (timeout ⇒ BLOCK)
                                                  │
                      ◄── verdict ────────────────┘
          ALLOW → forward upstream        BLOCK → respond 403 / kill flow
                      ▼
          write flow + alert + rule + score event to SQLite → WS "flow.completed", "score.updated"
```

---

## 6. Data contracts

### 6.1 SQLite tables (`schema.sql`)

| Table | Main columns |
|---|---|
| `flows` | `id`, `ts`, `pid`, `process_name`, `exe_path`, `method`, `scheme`, `host`, `port`, `path_masked`, `bytes_up`, `bytes_down`, `tls_status` (`inspected`/`pinned`/`passthrough`), `verdict`, `verdict_source` (`rule`/`user`/`timeout`/`blocklist`/`default`), `country_code` |
| `alerts` | `id`, `flow_id`, `ts`, `type` (`pii`/`tracker`/`large_upload`/`anomaly`), `severity`, `pattern_label`, `masked_sample` |
| `rules` | `id`, `created_at`, `process_match`, `host_match`, `action` (`allow`/`block`), `note` — persistent ("always") rules only; "once" decisions live in memory |
| `blocklist_domains` | `domain`, `source`, `enabled` |
| `custom_patterns` | `id`, `label`, `pattern`, `is_regex`, `enabled` |
| `score_events` | `id`, `ts`, `delta`, `reason`, `flow_id` |
| `process_baseline` | `process_name`, `hosts_seen`, `avg_bytes_up`, `first_seen` (anomaly extension) |
| `settings` | `key`, `value` |

Logs and DB store **pattern labels and masked samples only**, never full payloads.

### 6.2 REST (all under `/api`, token required)

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness + proxy/CA status |
| GET | `/flows` | History (filters: process, verdict, time) |
| GET | `/processes` | Live per-process aggregate (speed, bytes, hosts) |
| GET | `/halts/pending` | Currently held requests |
| POST | `/halts/{id}/decision` | `{action: allow\|block, scope: once\|always}` |
| GET/POST/DELETE | `/rules` | Manage persistent rules |
| GET/POST/PUT/DELETE | `/patterns` | Custom sensitive strings |
| GET | `/alerts` | Alert history |
| GET | `/blocklist/status` | List sources, counts, last update |
| GET | `/score` | Score + breakdown |
| GET | `/geo/destinations` | Aggregated countries/points for the map |
| GET/PUT | `/settings` | Inspection toggle, halt timeout, thresholds |
| POST | `/system/proxy` | Enable/disable Windows proxy routing |
| GET/POST/DELETE | `/system/ca` | CA status / install (user-confirmed) / remove |

### 6.3 WebSocket `/ws`

Envelope: `{ "type": "...", "ts": "...", "data": { ... } }`

- Server → client: `flow.started`, `flow.completed`, `speed.tick` (per-process B/s, every 1 s), `halt.requested`, `halt.resolved`, `alert.created`, `score.updated`, `system.status`
- Client → server: `halt.decide`

---

## 7. Secure-by-design checklist (and where it lives)

| Requirement | Implementation |
|---|---|
| Dashboard reachable only locally | uvicorn bound to `127.0.0.1`; `Host` header allow-list (`api/security.py`) |
| A web page cannot send Allow/Block | Random per-run session token + `Origin` check on REST and WS; no CORS headers in production |
| Minimal logging | `inspection/masking.py` + `logging_setup.py`; no raw bodies on disk |
| CA risk contained | Per-install CA in `%LOCALAPPDATA%\SentriFlow\ca`, ACL-restricted (`file_acl.py`), removed by thumbprint (`cert_store.py`, `remove-ca`) |
| Never leave user offline | Original proxy saved to `state.json`; restored on exit, on crash via `doctor`/`restore-proxy.ps1` |
| Monitoring own device only | Proxy binds loopback only; no remote/LAN mode |
| No third-party data flow | Offline GeoIP, bundled GeoJSON map, no analytics, no external AI API; intel updates are explicit manual scripts |
| Default-deny on silence | `halt_manager` returns BLOCK on timeout |

---

## 8. Windows 11 specifics

- **Routing:** Per-user system proxy via `HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings` (`winreg`), followed by a WinINET refresh through `ctypes`. Only apps that honour the system proxy are captured (browsers, many desktop apps). Apps that ignore it are a documented limitation.
- **Optional spike (Week 1):** check mitmproxy's local capture mode on Windows for apps that bypass the system proxy. It typically needs administrator rights, so keep the system-proxy path as the primary design and treat this as optional.
- **CA trust:** `certutil -user -addstore Root <cer>` writes to the *current-user* store (no admin; Windows shows a consent dialog). Remove by thumbprint. **Firefox uses its own store**, so demo on Edge/Chrome.
- **Process lookup:** `psutil.net_connections(kind="tcp")` matched on local port; some system processes raise `AccessDenied` → show "Unknown (protected process)" rather than failing.
- **QUIC:** `scripts/block-quic.ps1` adds a `netsh advfirewall` rule for outbound UDP 443 (needs an elevated PowerShell) so browsers fall back to HTTP/2; `unblock-quic.ps1` removes it.
- **Scripts:** PowerShell; run with `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1` if needed.
- **Line endings:** `.gitattributes` fixes `*.ps1` to CRLF-safe handling and everything else to LF, to avoid noisy diffs between teammates.

---

## 9. Developer quick start

```powershell
# one-time
git clone <repo-url> sentriflow; cd sentriflow
.\scripts\setup.ps1          # venv + pip install -e backend[dev] + npm ci in frontend

# daily development (two terminals handled by the script)
.\scripts\dev.ps1            # backend :8787/:8080 + Vite :3000

# production-style run (single process, built UI)
.\scripts\build.ps1
.\scripts\run.ps1            # open http://127.0.0.1:8787

# quality gates
.\scripts\test.ps1           # ruff, mypy, pytest, eslint, tsc, vitest

# if something crashed and the internet seems "broken"
.\scripts\restore-proxy.ps1
```

**Backend dependencies (`pyproject.toml`):** `mitmproxy`, `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `psutil`, `aiosqlite`, `geoip2` (reads offline `.mmdb`), `winotify` (toasts). Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`. Extra `[ml]`: `scikit-learn`. Pin exact versions after the Week-1 spike.

**Frontend dependencies:** `react`, `react-dom`, `react-router-dom`, `zustand`, `recharts`, `leaflet`, `react-leaflet`, `tailwindcss`. Dev: `vite`, `typescript`, `eslint`, `prettier`, `vitest`, `@testing-library/react`.

---

## 10. Build plan

### Ownership (4 roles — assign names as you prefer)

| Role | Owns |
|---|---|
| **R1 – Proxy & OS** | `proxy/`, `os_adapters/windows/`, process mapping, CA/proxy safety |
| **R2 – Inspection & decisions** | `inspection/`, `core/decision_engine`, `rule_engine`, `halt_manager`, `scoring`, `anomaly/` |
| **R3 – API & data** | `storage/`, `api/`, security, WebSocket, `intel/` |
| **R4 – Frontend & demo/docs** | `frontend/`, `demo/`, `docs/`, Full Proposal diagrams |

### Phase 0 — Bootstrap (now → 31 Oct)

| Task | Output |
|---|---|
| Create repo, branch protection, CI skeletons, pre-commit | Green empty CI on `windows-latest` |
| Scaffold backend package and frontend (Vite) with hello-world, `dev.ps1` working | Anyone can run `dev.ps1` after `setup.ps1` |
| **Windows spike (R1):** proxy → browser traffic → CA trusted → port→PID lookup | Go/no-go for embedded mitmproxy + system-proxy approach |
| Freeze data contracts (Section 6) in `docs/api.md` and `schema.sql` | Frontend and backend can work in parallel using mocks |
| Fixed-platform decision recorded (Windows 11) | Closes the "platform TBD" risk |
| Full Proposal writing continues in `docs/proposal/` | Diagrams drafted from Section 5 and 6 |

**Exit criteria:** a browser request appears in a console log with the correct process name.

### Phase 1 — Week 1 (1–7 Nov): Visibility

| Days | Goal | Deliverables |
|---|---|---|
| 1–2 | Skeleton end-to-end | Addon logs flows to SQLite; WS emits `flow.completed`; React shows a raw table |
| 3–4 | Attribution + stats | `process_resolver` with cache; per-process aggregates; `speed.tick`; tls_status (`pinned` shown as "encrypted, not inspected") |
| 5–6 | Dashboard + safety | Traffic page with live speed chart; Settings page with proxy toggle and CA install/remove; proxy auto-restore + `doctor` command |
| 7 | Hardening + review | API token/origin enforcement tests; Milestone M1 demo |

**M1 exit criteria:** ≥ 90 % of flows from a 10-minute browsing session carry a named process; killing SentriFlow leaves the system proxy restored.

### Phase 2 — Week 2 (8–14 Nov): Control

| Days | Goal | Deliverables |
|---|---|---|
| 8–9 | Inspector + blocklist | PII patterns (email, Luhn card), custom strings, payload extractor, tracker matcher with preloaded lists; inspection toggle |
| 10–11 | **Halt** + rules | `halt_manager`, HaltModal with countdown, once/always decisions, persistent rules, default-block timeout, toast fallback |
| 12 | Alerts + score | High-priority PII alert, privacy score and breakdown |
| 13 | Extended / stretch (only if the E2E demo already works) | Geo-map (offline), rule-based anomaly flag |
| 14 | **Feature freeze** | Full demo path passes; tag `v0.1-mvp` |

**M2 exit criteria:** the demo scenario (tracker-heavy site + form with seeded dummy PII) is halted, blocked, logged and reflected in the score.

### Phase 3 — 15–20 Nov: Stabilise (no new features)

- Bug-fix only; performance check (decision latency); long-run test (1 h session)
- Prepare local test server, rehearse `demo/demo-script.md` at least 3 times
- Record backup video; finalise docs and README
- Run the full acceptance checklist (Section 11)

### Scope guard

Extended features start only after the core E2E path (proxy → inspect → halt → rule → dashboard) passes. Out of scope: non-web protocols, kernel-level filtering, installer, trained PII model, mobile.

---

## 11. Testing & acceptance

| Target (from the concept proposal) | How it is measured | Where |
|---|---|---|
| ≥ 90 % of captured flows attributed to a named process | Scripted browsing session; `COUNT(process_name != 'Unknown') / COUNT(*)` | `docs/testing.md`, `test_process_resolver.py` |
| 100 % of seeded PII detected | Fixture payloads in JSON, form and multipart encodings, with and without gzip | `test_pii_patterns.py`, `test_proxy_pipeline.py` |
| User decision applied within 1 s | Timestamp delta between `halt.decide` and upstream release/403 | `test_halt_manager.py` + manual timing |
| Default Block on no answer | Unit test with a short timeout | `test_halt_manager.py` |
| Proxy restored on stop/crash | Integration test reading registry before/after | `test_system_proxy_restore.py` |
| Dashboard not controllable from a web page | Requests with wrong `Origin` / no token rejected | `test_api_security.py` |

Only **dummy PII** is used in tests and demos.

---

## 12. Git and quality conventions

- `main` is always demo-able; work on short-lived branches `feat/<module>-<topic>`, merge by pull request with at least one reviewer.
- Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- CI must pass: ruff (lint + format), mypy (on `core/` and `inspection/` at minimum), pytest, eslint, `tsc --noEmit`, vitest, `vite build`.
- Tests are required for any change in `inspection/` and `core/`.

---

## 13. Risks (Windows-oriented additions to the proposal's risk table)

| Risk | Mitigation |
|---|---|
| App ignores the system proxy | Document as limitation; demo on browsers; optional local-capture spike |
| Firefox does not trust the Windows user store | Demo on Edge/Chrome |
| `AccessDenied` on some processes | Show "Unknown (protected process)"; excluded from the attribution target only if documented |
| System left with a dead proxy after a crash | `state.json` + `atexit` handler + `restore-proxy.ps1` + startup `doctor` check |
| Certificate pinning / QUIC | "Encrypted, not inspected" label; `block-quic.ps1` during demo |
| PowerShell execution policy blocks scripts | Documented `-ExecutionPolicy Bypass` invocation in `windows-setup.md` |

---

## 14. Mapping to the Semifinal Full Proposal

| Full Proposal section | Source in repo |
|---|---|
| Introduction / Problem Analysis | `docs/proposal/FPH_Senklok.md` (+ `references.md`) |
| Proposed Solution | `README.md`, Section 4–5 of this file |
| System Design | `docs/proposal/diagrams/*`, `docs/architecture.md`, `docs/api.md`, `schema.sql` |
| Technical Implementation | Sections 2, 8, 9 of this file |
| Expected MVP | Phase 2 deliverables and acceptance table |
| Submission file name | `FPH_Senklok.pdf` (max 15 pages excluding cover, references, appendix) |
