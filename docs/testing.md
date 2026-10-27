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
