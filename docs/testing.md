# Verification and acceptance

Date: 27 October 2026, Asia/Jakarta. Local runtime: Python 3.13.9, Node 22.17.0, Windows, Microsoft Edge headless. Current checks passed: 48 backend tests, 8 frontend tests, Ruff, strict domain mypy, ESLint and TypeScript/Vite build. Run `scripts/test.ps1` for backend Ruff/mypy/pytest plus frontend ESLint/Vitest/build. Automated fixtures use dummy data only. The optional public-map browser check additionally sends one non-personal request to example.com; it is explicitly selected with `--public-map-check`.

R4 map/detail/alert/PDF checks, exact artifacts, data provenance and limitations are recorded in [r4-delivery.md](r4-delivery.md). The exporter reported zero external requests and a 13-page A4 working draft. The dashboard/browser map test also recorded zero external asset/tile/lookup requests.

The backend includes unit tests for bounded PII extraction/detection, Luhn, literals/redaction, tracker suffix boundaries, rule precedence/scope, timeout/parallel holds, persistence failure/recovery and score. Integration covers peer/Host/Origin/token/WS checks, real HTTP hold-before-forward, explicit Block/no-delivery, default timeout Block, incomplete input, inspector failure, and trusted local HTTPS. Windows routing tests use an in-memory registry adapter; they do not change the machine's registry. Watchdog dead-owner restoration is tested using the same fake adapter.

A dedicated streaming test keeps a chunked response open until the test permits completion and asserts positive download counters/speed while the response task is still incomplete. This distinguishes real chunk-based accounting from counting only completed responses.

Frontend tests cover flow upserts, idle speed samples, independent pending queues, and an Unknown-process Halt modal sending a one-time Block. The optional `scripts/check-browser.py` launches the actual CLI, proxy, local origin and Edge, performs UI decisions and rules/settings actions, and verifies mobile width. It never installs CA trust, enables Windows routing or changes firewall rules.

Actual browser evidence: [JSON report](evidence/local-demo-report.json), [dashboard](evidence/dashboard.png), [Halt](evidence/halt.png). The last recorded sample has 3/3 attributed requests, all three seeded pattern labels detected on each request, and 49–56 ms click-to-HTTP-response durations. It also observed positive download rate before stream completion. Re-running the script replaces evidence with that run's measured results.

These are small-sample local feasibility measurements. Still required: representative ten-minute multi-app attribution session, PII precision/false-positive review, clean Windows 11 setup, real OS normal/forced-crash proxy recovery, pinned-app compatibility, QUIC fallback, notification delivery, an hour-long load/stability run, participant comprehension tasks and backup video. No claim of universal PII detection or full-device traffic coverage is made. Dependency deprecation warnings can originate from Starlette's TestClient/httpx and mitmproxy's ldap3/pyasn1 imports.

Remote GitHub Actions has been configured, not run or pushed by this session. Python 3.12 remains the intended minimum; local testing used 3.13, so the CI/clean-machine 3.12 check is still necessary.
