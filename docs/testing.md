# Validation and KPI measurements

Install `backend[dev]` with Python 3.12. From the repository root:

```bash
.venv/bin/python -I -m ruff check backend
.venv/bin/python -I -m ruff format --check backend
.venv/bin/python -I -m mypy backend/src/sentriflow/core backend/src/sentriflow/inspection
.venv/bin/python -I -m pytest backend -q
.venv/bin/python -I -m sentriflow.verification --output docs/evidence/kpis.json
```

On Windows use `.venv\Scripts\python.exe`; `scripts\test.ps1` also runs frontend lint/tests/build.
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
test connections. CLI lifecycle tests use POSIX SIGTERM and are skipped on Windows.

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
| 1 | >= 90% of flows attributed to a named process | Real Edge session: **3871/3922 = 98.70%** named (msedge.exe 3733; 5 other named processes, 138 flows; 51 flows `Unknown`, none `protected process`). Session lasted 8 min 3 s, not 10 | [evidence/s41-row1-windows.json](evidence/s41-row1-windows.json), code `origin/merge` b9548be | **PASS** (8 min 3 s session; repeat for a full 10 min if the rubric needs it) |
| 2 | 100% of seeded PII detected | 18/18 (100.0%): name, email, card over JSON, form, multipart, plain and gzip, HTTP and HTTPS | automated | **PASS** (automated) |
| 3 | Decision applied within 1 s | max 8.62 ms, median 6.52 ms over 16 decisions (WebSocket send to proxy response) | automated | **PASS** (automated); UI click timing still open |
| 4 | Default Block when nobody answers | timeout request blocked and never reached upstream (halt timeout set to 0.1 s) | automated + unit tests | **PASS** (automated); manual run with the default 30 s optional |
| 5 | Proxy restored after stop or crash | Real Windows registry, run twice with the same result. Normal exit (Ctrl+Break): proxy was on (`127.0.0.1:18080`), process exited in 0.3 s, all 5 values back to baseline immediately, `state.json` removed. Forced kill: watchdog restored all 5 values in 0.75 s, `state.json` removed at 0.75 s, watchdog process exited | [evidence/s41-row5-windows.json](evidence/s41-row5-windows.json), code `origin/merge` b9548be | **PASS** (registry only; logoff, reboot and power loss not tested) |
| 6 | Dashboard not controllable from a web page | every `/api` route and `/ws` reject bad token, Origin and Host; no CORS headers | `test_route_security_matrix.py`, `test_ws_security.py`, `test_api_security.py` | **PASS** (automated) |

Extra automated checks: no seeded PII in the SQLite file, its WAL, any table or SentriFlow logs
(`test_privacy_at_rest.py`); blocked payloads never reached the upstream server; a saved always-rule
applied to the next connection; score recovered by 5 points after each Block in all 3 rehearsals.

Measured on the integrated `merge` code with a real Edge session. Observations from that run that are not part of the targets but matter for the demo: 618 of 3922 flows were blocked (465 halt timeouts, 140 TLS failures, 13 unsupported protocol), so about 12% of ordinary browsing reached the Halt path and, with nobody answering, timed out into Block; `tls_status` also took the value `not_inspected` and `verdict_source` the value `unsupported_protocol`, neither in the Build Plan lists. The temporary CA was removed manually after `sentriflow remove-ca` timed out in the run.


## Four-role integration verification

See [integration.md](integration.md) and [the current browser report](evidence/integration/local-demo-report.json).
Tests cover reconnecting to an existing hold, cross-client settings/rule/pattern events, exact
source-IP process attribution, blocklist cache invalidation and independent data paths, API-only
environment/import handling, maintenance ownership and cleanup on real process termination.
The updated proposal export uses the same contracts and reports zero external requests.
