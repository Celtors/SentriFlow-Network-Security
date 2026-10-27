# Windows setup and local demo

Run commands from the repository root. Python 3.12+ and Node 22 LTS are required. Local verification used Python 3.13.9 and Node 22.17.0; the intended target remains Windows 11. The scaffold's current React 19/Vite 8 setup was retained rather than downgraded to the older versions mentioned in the planning document.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
npm --prefix frontend ci
.\scripts\build.ps1
.\scripts\run.ps1
```

Open **http://127.0.0.1:8787**, then paste the terminal's session token. Keep that terminal open; Ctrl+C stops the guardian. Do not run the obsolete `python -m backend.main` command from the earlier separate project. Current default ports follow this repo's build plan: proxy 8080, API/dashboard 8787, Vite dev 3000.

Runtime data defaults to `%LOCALAPPDATA%\SentriFlow`: SQLite, generated CA, session lock and an optional proxy recovery journal. The directory is ACL-restricted. For an isolated local directory:

```powershell
.\.venv\Scripts\python.exe -m sentriflow run --data-dir .runtime\manual-demo
```

Keep the same `--data-dir` when using doctor, CA operations or emergency restore. A new session token is generated per run and never written to disk. Another active process cannot use the same data directory.

## Capture a real request

Opening the dashboard does not route your browser. To test explicit capture, keep the guardian running and use another terminal:

```powershell
curl.exe --noproxy "none.invalid" --proxy http://127.0.0.1:8080 http://example.com
```

The chart measures only proxied payload. Request bodies are counted on approval; response payload is counted as chunks arrive, with per-process `speed.tick` once per second. It excludes network/protocol overhead and all traffic bypassing the proxy.

For an entirely offline demo, start the origin in a second terminal:

```powershell
.\.venv\Scripts\python.exe demo/test-server/server.py
```

In another terminal:

```powershell
curl.exe --noproxy "none.invalid" --proxy http://127.0.0.1:8080 --max-time 40 --data-urlencode "email=student@example.test" --data-urlencode "phone=+6281234567890" --data-urlencode "card=4111111111111111" http://127.0.0.1:9090/submit
```

Choose Block (local 403, no origin payload) or Allow (origin 200) in the dashboard. Ignore the prompt to demonstrate the default 30-second Block. Remember a decision to create an executable-identity/exact-host rule, and delete that rule before demonstrating Halt again.

Slow response to demonstrate the chart moving before download completion:

```powershell
curl.exe --noproxy "none.invalid" --proxy http://127.0.0.1:8080 http://127.0.0.1:9090/stream --output NUL
```

Tracker demo: use `http://tracker.sentriflow.test/pixel` through the proxy and Block it. That reserved host has no real origin; Allow will not make it reachable. The bundled blocklist is only a tiny demo seed. Import a reviewed local hosts/domain file using `run --import-blocklist PATH`. Simple `||domain^` rules work; unsupported modifiers/exceptions are reported as skipped. This is not a complete EasyPrivacy implementation.

## Browser routing and HTTPS consent

Settings exposes **Enable browser routing**, which explicitly changes the current user's WinINET proxy. It bypasses loopback so the dashboard stays direct. Browsers honoring that proxy can be captured; apps ignoring it, QUIC and non-web protocols remain outside scope. Do not treat it as a kernel firewall or system-wide packet monitor.

For HTTPS, first start the proxy to generate its unique CA. Settings requires an explicit consent checkbox before installing the public certificate in CurrentUser Root. Equivalent command:

```powershell
.\.venv\Scripts\python.exe -m sentriflow install-ca --confirm
# Remove that exact CA by thumbprint when finished:
.\.venv\Scripts\python.exe -m sentriflow remove-ca
```

For one curl invocation, use `--cacert "$env:LOCALAPPDATA\SentriFlow\ca\mitmproxy-ca-cert.pem"` instead of changing system trust. Never share `mitmproxy-ca.pem` or other private-key files. Remove CA trust before deleting the public certificate files, since removal identifies that installation by thumbprint. Trust status is currently reported as `not_checked`; generation is not proof of installation. Certificate pinning/trust failures are labeled uninspected rather than bypassed.

Proxy settings are snapshotted before mutation and restored on normal exit. An independent hidden watchdog is started only when the user enables routing; it attempts recovery after parent-process death. It preserves the journal if settings were changed externally. These paths are tested with a fake registry adapter; real-machine normal/forced-crash acceptance is still required. Manual recovery:

```powershell
.\.venv\Scripts\python.exe -m sentriflow doctor
.\scripts\restore-proxy.ps1
```

No trust-store, firewall or system-proxy mutation was performed during the automated verification in this session.

## Quality checks

```powershell
.\scripts\test.ps1
```

This runs backend Ruff, domain mypy, pytest, frontend ESLint, Vitest and production build. Optional actual Edge check, with ports 8080/8787/9090 free:

```powershell
.\.venv\Scripts\python.exe -m pip install -e "backend[browser]"
.\.venv\Scripts\python.exe scripts/check-browser.py
```

It uses a new `.runtime` directory and only dummy local traffic, leaving real proxy/CA settings alone. Screenshots and JSON measurements are written to `docs/evidence`. It terminates its own child processes afterward. CI definitions exist, but no remote CI run or push was performed by this session.
