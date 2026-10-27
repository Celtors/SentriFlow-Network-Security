# SentriFlow backend

This package implements the existing `SentriFlow_Build_Plan.md` scaffold. Entry point: `python -m sentriflow run`. API/dashboard: **127.0.0.1:8787**; interception proxy: **127.0.0.1:8080**. The previous separate implementation and its port 8765 are not used here.

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
npm --prefix frontend ci
.\scripts\build.ps1
.\scripts\run.ps1
```

Open http://127.0.0.1:8787 and paste the token printed in the terminal. The built frontend is served by FastAPI; no separate Vite process is needed. Development mode uses Vite at port 3000 with `/api` and `/ws` proxied to 8787.

Full setup, routing/CA consent, test commands and demo: [Windows setup](../docs/windows-setup.md). Current scope and remaining work: [implementation status](../docs/implementation-status.md).
