# Windows 11 setup and recovery

Use your own Windows 11 x64 device with Python 3.12 and Node.js 22. From the repository root,
run `powershell -ExecutionPolicy Bypass -File scripts\setup.ps1`. Add `-BackendOnly` to defer
the frontend install. Activate `.venv` or use its Python executable explicitly.

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
