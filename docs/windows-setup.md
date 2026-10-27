# Windows 11 setup

## Platform decision

SentriFlow targets **Windows 11 x64**. Windows is the supported desktop platform for the MVP because the primary routing path uses the per-user Windows system proxy, and certificate trust and recovery use Windows facilities. Platform-specific code stays under `backend/src/sentriflow/os_adapters/windows/`; the rest of the application uses platform-neutral interfaces.

The supported development stack is Python 3.12 and Node.js 22 LTS (Node.js 20 LTS is also supported by the build plan). The backend is FastAPI with an embedded mitmproxy instance and SQLite storage; the dashboard is React, Vite, and TypeScript. The API and proxy bind to loopback only (`127.0.0.1`). Runtime data, including the database and generated CA, belongs under `%LOCALAPPDATA%\SentriFlow\`.

## Prerequisites

- Windows 11 x64
- Python 3.12
- Node.js 22 LTS (20 LTS is also supported)
- Git

## Development setup

From the repository root, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\scripts\dev.ps1
```

The setup script creates the backend virtual environment, installs the development dependencies, and installs the frontend dependencies. The development script starts the API on `127.0.0.1:8787`, the proxy on `127.0.0.1:8080`, and Vite on `127.0.0.1:3000`.

## Proxy and certificate behavior

SentriFlow routes supported applications through the **current user's** Windows system proxy settings. It does not install a machine-wide proxy or expose a LAN-accessible proxy. Applications that ignore the Windows system proxy are not captured; Firefox may also require separate certificate configuration.

HTTPS inspection requires installing SentriFlow's local CA in the current user's trusted root store. Installing the CA is an explicit user action and Windows may show a consent prompt. Remove the CA after use with the application's `remove-ca` command. The CA private key is stored in the SentriFlow local data directory and its folder ACL is restricted.

SentriFlow saves the existing proxy settings before changing them and restores them on shutdown. If the application exits unexpectedly and networking is affected, run:

```powershell
.\scripts\restore-proxy.ps1
```

## S03 Windows proxy feasibility spike

The spike runner embeds mitmproxy in the Python process and binds only to `127.0.0.1:8080`. It logs the request method, destination host, and the process resolved from the client's local TCP port. It deliberately omits URL paths, query strings, headers, and payloads.

In PowerShell, start the runner:

```powershell
.\.venv\Scripts\python.exe -m sentriflow.proxy.runner
```

mitmproxy creates its local CA under the profile directory printed at startup (normally `%USERPROFILE%\.mitmproxy`). HTTPS inspection requires an explicit current-user trust action. Review the CA file, then install it with:

```powershell
certutil -user -addstore Root "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"
```

Accept the Windows trust prompt only if you intend to run the inspection spike. To remove the certificate, identify its thumbprint in the current user's Trusted Root Certification Authorities store and remove that exact certificate with `certutil -user -delstore Root <thumbprint>`.

Before changing proxy settings, note the existing values. In **Settings → Network & internet → Proxy**, enable manual proxy and set address `127.0.0.1`, port `8080`. Then open Microsoft Edge and visit `https://example.com`; the console should show an entry with `process=msedge.exe` (the executable path can be unavailable for protected processes). Restore the proxy settings to their original values when finished, then stop the runner with Ctrl+C and remove the spike CA if it is no longer needed. Do not use this manual procedure on a managed device without following its administrator's policy.

### Spike result

| Check | Result |
|---|---|
| Embedded mitmproxy starts on loopback port 8080 | Implemented; Windows denied binding with `WinError 10013` during the 27 Oct 2026 run |
| Browser HTTPS request is intercepted and logged with process attribution | Edge loaded an HTTPS page through the proxy on port 8081; proxy output attributed Edge traffic to `msedge.exe` |
| Current-user Windows system proxy routes browser traffic | The temporary 8081 setting also routed the active ChatGPT desktop app; TLS handshakes failed, so the setting was restored before browser verification |
| Go/no-go for embedded mitmproxy plus Windows system proxy | Pending: Windows denied port 8080, and the system-proxy test cannot run safely while the Codex desktop app is active |

In the earlier per-process Edge check, the spike CA was installed in the current user's Root store, then removed by thumbprint; its generated files were also removed. Edge loaded an HTTPS page through port 8081 and the addon attributed Edge traffic to `msedge.exe`. Edge also generated background service requests in that check. In the later current-user system-proxy attempt, the active Codex desktop app was routed through the proxy and its TLS handshakes failed; the system proxy was immediately restored to its original disabled state. The generated CA files and temporary Edge profile were removed, and no CA remains installed. The recorded browser check used port 8081 with an explicit per-process proxy and does not establish the required port-8080/system-proxy go/no-go. Complete that check in a separate Windows session or test machine where Codex is not running. The two proposal screenshots are still pending.

Capture at least two screenshots during the Windows run: the browser showing the HTTPS page and the proxy console showing the same destination with its process name. Do not include unrelated browsing data in the screenshots.

## Checks

Run the repository quality checks from PowerShell with:

```powershell
.\scripts\test.ps1
```

For scripts blocked by the machine's execution policy, use the process-scoped bypass shown above; it does not change the machine or user policy.
