# Agent handoff: current scaffold implementation

Current integrated status: [implementation-status.md](implementation-status.md); run/check guide: [integration.md](integration.md). Earlier role-specific evidence below is retained as history.

Merged runtime/contracts: see [merge-r4.md](merge-r4.md). The branch-specific history and evidence below are preserved from R4's original checkout.

**R4 update, 27 October 2026:** see [r4-delivery.md](r4-delivery.md). Offline GeoIP/Leaflet map, request detail, severity filtering and Halt error UX are implemented; five diagrams now have SVG/PNG exports, and the proposal has a 13-page A4 PDF working draft. Current checks: 48 backend / 8 frontend tests, Ruff/mypy/ESLint/build and expanded real Edge flow passed. The optional public-map check used one non-personal example.com request and recorded zero external browser requests. Remaining field validation and submission limits are documented there. The paragraphs below describe the preceding handoff and its original state; use the current R4 status for map/PDF completion.

Date: 27 October 2026, Asia/Jakarta. Work on **this** repository: `D:\ITBx_Sem5\SentriFlow\SentriFlow-Network-Security`, current branch `dev`, baseline commit `711dba2`. User corrected the plan: the earlier independent implementation was based on the wrong foundation. Do not copy its root `backend.main` architecture/ports into this repo. The sibling `SentriFlow-Network-Security - Copy` was left untouched.

The real baseline had an existing `SentriFlow_Build_Plan.md`, empty module scaffold, placeholder CLI, smoke test and Vite starter. The current code fills `backend/src/sentriflow`, planned repository/route modules and frontend pages/hooks/stores. Pure `core` and `inspection` do not import transport/proxy/OS layers. `runtime.py` composes them; `launcher.py` owns lifecycle. Defaults are **8787 dashboard/API**, **8080 proxy**, **3000 Vite**, and `/ws` typed events. Runtime defaults to `%LOCALAPPDATA%\SentriFlow`, override with `--data-dir` for tests.

Implemented: local proxy/CA, source socket process mapping, bounded PII/literals/domain matching, Halt and persistent exact process+host rules, SQLite repositories, authenticated API/WS, real dashboard, payload speed ticker from response chunks, opt-in Windows routing snapshot/restore/watchdog and opt-in current-user CA trust operations. Palette preference remains black + papaya orange #FF8700. See [architecture](architecture.md), [API](api.md), and [status](implementation-status.md) for exact scope.

Important: actual system proxy, trust store and firewall were **not modified** during testing. OS restore/watchdog tests use a fake registry adapter. CA generation in private test directories is not CA trust installation. Do not claim real-machine crash recovery, representative attribution or pinning coverage is validated.

Checks: 44 backend tests and 4 frontend tests passed, along with backend pytest including actual local HTTP/HTTPS/streaming, Ruff and strict mypy on pure layers; frontend ESLint/Vitest/TypeScript/Vite. Actual Edge script completed three dummy Halt cycles, remembered/edit/deleted a rule, saved settings and checked mobile width. Evidence JSON/screenshots are under `docs/evidence`; measurements are a small local sample only. Download rates were observed while a slow response was still in progress, addressing the earlier completion-only chart limitation.

Run from repo root:

```powershell
.\scripts\build.ps1
.\scripts\run.ps1
# Open http://127.0.0.1:8787 and paste terminal token
```

Fresh install: `python -m venv .venv`, `.\.venv\Scripts\python.exe -m pip install -e "backend[dev]"`, `npm --prefix frontend ci`. Local Python is 3.13.9; intended minimum/CI is 3.12. Tests: `scripts/test.ps1`. Optional browser: install `backend[browser]`, then `scripts/check-browser.py` with ports free. It writes measured evidence and stops only its own processes. Keep tokens/CA keys/runtime/private participant data out of Git and tool output.

Still pending: offline GeoIP/map shapes, anomaly model/baseline, comprehensive licensed blocklist/Adblock syntax, real Windows routing/crash/pinning/QUIC/notification validation, long-run/load tests, representative KPI session, participant research, independent review, backup video and final proposal PDF/submission. Empty optional modules are reservations, not working features. Draft proposal, diagram sources, source notes and user-validation kit exist; no survey results or legal/statistical assertions were fabricated.

The root README.md was already deleted when this task started and was not restored. `backend/README.md` and `docs/windows-setup.md` are current setup entry points. All current changes are uncommitted; no push, PR, tag, deployment or submission was done. Preserve unrelated working-tree changes and inspect status before editing. The old handoff/tests from the sibling copy are not evidence for this implementation.
