# Validation and KPI measurements

Install `backend[dev]` with Python 3.12. From the repository root:

```bash
.venv/bin/python -I -m ruff check backend
.venv/bin/python -I -m ruff format --check backend
.venv/bin/python -I -m mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
.venv/bin/python -I -m pytest backend -q
.venv/bin/python -I -m sentriflow.verification --output docs/evidence/kpis.json
```

On Windows use `.venv\Scripts\python.exe`; `scripts\test.ps1` also runs frontend lint/build.
Isolated Python mode avoids unrelated host Python/pytest plugins. Tests require permission
to create local sockets; no internet or administrator privileges are required by the tests.

The unit suite covers Luhn checks, encoded PII, literal/regex patterns, regex timeouts,
domain boundaries, masking, rule precedence, tracker policies, and independent Halt futures.
Halt tests verify default Block, once/always behavior, conflicting decisions, persistence
failure, pending capacity and cancellation. Integration checks authenticate REST and WS,
exercise API CRUD, reopen SQLite, and verify proxy snapshot restoration against a fake registry.

`sentriflow.verification` creates real loopback HTTP and HTTPS servers, embedded mitmproxy,
FastAPI and a WebSocket client. It preserves TLS validation using a temporary upstream trust
certificate and a client that trusts only the temporary SentriFlow CA. It verifies:

- Three consecutive tracker → PII Allow → PII Block → score-update rehearsals.
- Eighteen seeded name/email/card matches across JSON, form and multipart, plain and gzip.
- Sensitive requests stay held and never reach the test destination when blocked.
- A saved always-block rule applies to the next connection; no-answer requests block.
- Flow history, alerts and captured events contain no seeded raw PII values.

The JSON report records real durations and host details. `decision_max_ms` measures from
WebSocket send to receipt of the proxy response; it includes delivery and handling overhead.
The non-halted and direct medians use ten local GETs each. Their difference is a local
measurement, not a general browsing-performance claim. Source-port lookup currently scans
the OS TCP connection table for uncached client ports; high concurrency needs profiling.

The test fixture does not install a certificate into any system store or modify routing.
Windows registry tests use an injected fake adapter. Linux attribution is limited to local
test connections. Two CLI lifecycle tests use POSIX SIGTERM and are skipped on Windows.

Native Windows acceptance must add genuine evidence for these cases:

| Criterion | Procedure | Evidence to record |
| --- | --- | --- |
| ≥90% named flows | Browse Edge/Chrome for 10 minutes through system routing | Named/total count, duration, protected-process exclusions |
| HTTPS trust | Install CA with consent, browse HTTPS, remove CA afterward | Current-user thumbprint, trust status, inspected flow |
| Recovery | Compare original registry values after Ctrl+C and forced termination | Before/after values; watchdog delay; recovery-file state |
| UI decision <1s | Click each of four Halt actions in the dashboard | Click-to-completion timing and matching saved-rule behavior |
| Continuous session | Browse for at least 30 minutes; report any missed protocols | Duration, crashes, memory and responsiveness |
| S20 recording | Rehearse the frontend demo three times, then record | Actual video file and screenshots, no personal payloads |

No measured Windows values or video should be inferred from automated backend tests. Current
results and outstanding evidence are in [evidence/kpis.json](evidence/kpis.json) and
[audric-worklog.md](audric-worklog.md).


## S41 acceptance results (Windows 11, measured 2026-10-27, commit 8fdd2be)

Source: [evidence/kpis-windows.json](evidence/kpis-windows.json), produced on Windows 11
(`Windows-11-10.0.26200-SP0`) by `python -I -m sentriflow.verification` (loopback only; no system proxy or
certificate store was changed). The older `kpis.json` was measured on Linux.
"Automated" = loopback backend rehearsal. It is **not** a browser session, so rows that need one stay open.

| # | Build Plan target | Result | Evidence | Status |
| - | --- | --- | --- | --- |
| 1 | >= 90% of flows attributed to a named process | 28/28 flows named, but all from the test process itself | automated only | **OPEN**: needs a 10-minute Edge/Chrome session |
| 2 | 100% of seeded PII detected | 18/18 (100.0%): name, email, card over JSON, form, multipart, plain and gzip, HTTP and HTTPS | automated | **PASS** (automated) |
| 3 | Decision applied within 1 s | max 8.62 ms, median 6.52 ms over 16 decisions (WebSocket send to proxy response) | automated | **PASS** (automated); UI click timing still open |
| 4 | Default Block when nobody answers | timeout request blocked and never reached upstream (halt timeout set to 0.1 s) | automated + unit tests | **PASS** (automated); manual run with the default 30 s optional |
| 5 | Proxy restored after stop or crash | restoration verified only against a fake registry | unit tests | **OPEN**: needs the real registry, normal exit and forced kill |
| 6 | Dashboard not controllable from a web page | every `/api` route and `/ws` reject bad token, Origin and Host; no CORS headers | `test_route_security_matrix.py`, `test_ws_security.py`, `test_api_security.py` | **PASS** (automated) |

Extra automated checks: no seeded PII in the SQLite file, its WAL, any table or SentriFlow logs
(`test_privacy_at_rest.py`); blocked payloads never reached the upstream server; a saved always-rule
applied to the next connection; score recovered by 5 points after each Block in all 3 rehearsals.

Rows 1 and 5 (and the optional manual checks) need a person at the PC: they change the Windows
system proxy and trust a temporary CA for the current user. The procedure is in the "Native Windows
acceptance" table above. Row 1 and row 5 results must be added here once measured.
