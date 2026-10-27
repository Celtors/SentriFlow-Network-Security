# Windows 11 setup and recovery

Use your own Windows 11 x64 device with Python 3.12 and Node.js 22. From the repository root,
run `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`. Add `-BackendOnly` to defer
the frontend install. Activate `.venv` or use its Python executable explicitly.

Windows is the primary MVP platform because routing uses the current user's Windows system
proxy and certificate trust/recovery use Windows facilities. OS-specific code stays in
`backend/src/sentriflow/os_adapters/windows/`; FastAPI, inspection and SQLite use the shared
architecture. Install Git as well as Python and Node before cloning the repository.

For development, run `.\scripts\dev.ps1` after setup. It starts the backend and Vite; the
development dashboard is at `http://127.0.0.1:3000`. Use the backend's printed token in that
URL's fragment, as described in [api.md](api.md). For a process-scoped execution-policy
override, use `Set-ExecutionPolicy -Scope Process Bypass` in the current PowerShell session.

Start `scripts\run.ps1`. This generates a CA in `%LOCALAPPDATA%\SentriFlow\ca` with restricted
directory permissions, starts the proxy on 127.0.0.1:8080 and the API on 127.0.0.1:8787,
and prints a per-run dashboard URL. Ordinary startup does not change OS routing or trust.

To inspect browser HTTPS, opt into current-user CA trust:

```powershell
.\.venv\Scripts\python.exe -I -m sentriflow install-ca --consent
```

Read the Windows certificate consent dialog. The CA permits local HTTPS interception; install
only for use on your own device. The private key stays under the per-install runtime directory.
Edge/Chrome normally use Windows trust. Firefox may require separate trust configuration.

Stop the existing instance, then opt into system routing with `scripts\run.ps1 -SystemProxy`.
Original `ProxyEnable`, `ProxyServer`, and `ProxyOverride` values are saved before any change.
Loopback and local hosts are bypassed, so use an explicit proxy for local demo requests.
Only applications that honor the system proxy are captured. QUIC and certificate-pinned apps
can bypass interception or reject the CA; a TLS failure is shown as encrypted, not inspected.
The backend never disables upstream TLS verification.

In another terminal, force an HTTP dummy request through the proxy, even to localhost:

```powershell
python demo\test-server\server.py
# Separate terminal, while SentriFlow runs:
curl.exe --proxy http://127.0.0.1:8080 --noproxy "" `
  -H "Content-Type: application/json" `
  --data-binary '@demo/seed/dummy_pii.json' http://127.0.0.1:9090/submit
```

Run `sentriflow seed-demo` before startup to register the dummy name. The name is a custom
string; email and Luhn-valid test card detection are built in. Until the R4 Halt UI is wired,
use REST or WebSocket from [api.md](api.md) to decide. A silent prompt blocks at 30 seconds.

On Ctrl+C, the backend restores Windows routing before stopping the local proxy. An independent
watchdog attempts recovery after forced termination. A power loss stops both processes; on
restart, inspect and restore the saved settings before enabling routing again:

```powershell
.\.venv\Scripts\python.exe -I -m sentriflow doctor
.\scripts\restore-proxy.ps1
```

Recovery keeps the saved file if any registry write or refresh fails. Do not delete
`state.json` to bypass that error. If necessary, disable the stale SentriFlow proxy in Windows
Settings → Network & internet → Proxy, then reconcile the saved original values.

After monitoring, stop SentriFlow, restore routing, and remove this installation's trust:

```powershell
.\.venv\Scripts\python.exe -I -m sentriflow remove-ca
```

Removal targets the exact SHA-1 certificate thumbprint in the current-user Root store. It does
not delete other certificates or the CA files. Keep the files until trust removal is confirmed.
To clear history afterward, while the service is stopped, use `sentriflow reset --confirm`.

Set environment variables before startup to override defaults, for example
`$env:SENTRIFLOW_HALT_TIMEOUT_SECONDS = "20"`. `.env.example` lists the defaults; the CLI reads
the process environment. A custom `--data-dir` must also be passed to recovery and CA commands.

## R1 standalone proxy feasibility spike

The standalone entry point is retained alongside the integrated API/Halt runtime:

```powershell
.\.venv\Scripts\python.exe -I -m sentriflow.proxy.runner --port 8081
```

It starts only embedded mitmproxy, bound to `127.0.0.1`, and logs method, destination host,
process name, PID and executable path. URL paths, queries, headers and payloads are omitted.
It uses the same asynchronous resolver and `exe_path` model as the application, configured
for the selected proxy port. Unknown/protected processes retain the shared `Unknown` identity.

The merged runner generates its CA under `%LOCALAPPDATA%\SentriFlow\ca`, using the same
restricted directory and explicit `install-ca --consent` / `remove-ca` commands above.
It no longer uses the original spike's `%USERPROFILE%\.mitmproxy` certificate location.
It also accepts `--data-dir`; pass that same directory to installation/removal commands.

Use an explicit per-process browser proxy for a spike check, or run the system-routing check
in a separate Windows test session. The standalone runner does not manage Windows routing
or recovery; use the integrated `scripts\run.ps1 -SystemProxy` for managed system routing.
If a manual proxy setting is used, record and restore its original values before stopping
the listener. Do not run the standalone and integrated proxies on the same port concurrently.

## R1's recorded Windows results — 27 October 2026

These are R1's historical observations, preserved from the incoming branch; they were not
repeated during conflict resolution.

| Check | Recorded result |
| --- | --- |
| Embedded mitmproxy on port 8080 | Windows denied binding with `WinError 10013` |
| Explicit per-process Edge proxy on port 8081 | Edge loaded an HTTPS page and proxy output attributed its traffic to `msedge.exe` |
| Current-user system-proxy attempt on port 8081 | It also routed the active ChatGPT/Codex desktop app, which had TLS handshake failures; original disabled settings were restored |
| Port-8080/system-proxy go/no-go | Pending a separate Windows session or test machine |

For R1's earlier Edge check, the spike CA was installed in the current-user Root store,
then removed by thumbprint; generated CA files and the temporary Edge profile were removed.
R1 recorded that no spike CA remained installed at the end of those checks. The successful
8081/per-process test does not establish the required 8080/system-proxy acceptance result.
The two proposal screenshots remain pending: capture the browser's HTTPS page and the
matching proxy console entry with process attribution, excluding unrelated browsing data.

Run `.\scripts\test.ps1` for repository quality checks. The native Windows acceptance and
recording procedures are in [testing.md](testing.md) and [../demo/demo-script.md](../demo/demo-script.md).
