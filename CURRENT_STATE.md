# CURRENT STATE — reform

Updated: 15 November 2026 (Asia/Jakarta). Milestone: repository synchronization and assessment.

## Objective

Implement a real trained website/phishing risk model in the existing SentriFlow application,
retain traffic/privacy controls, and provide a compact floating-style interface with expanded
details. Never feed sensitive values to the model, invent observations/predictions, or build a
browser extension. Commit and push coherent checkpoints to `origin/reform`.

## Repository and synchronization

- Remote: `https://github.com/Celtors/SentriFlow-Network-Security.git`.
- Worktree: `D:\ITBx_Sem5\SentriFlow\SentriFlow-Reform`; branch `reform`.
- Base: latest fetched `origin/merge`, `e670eab` (15 November synchronization).
- `origin/reform` did not exist at initial fetch; this branch was created from updated integration.
- Original checkout `SentriFlow-Network-Security` remains on `merge` with its uncommitted proposal,
  setup, and lockfile edits intact. Those unrelated changes are not included here.
- No reset, discarded changes, or force push. First checkpoint push is pending this commit.

## Existing architecture and functionality

- Python package `backend/src/sentriflow`; `application.Runtime` composes async SQLite repositories,
  inspection, Halt/rules, process resolver, local intelligence and event bus on one API/proxy loop.
- mitmproxy at 8080; FastAPI/dashboard at 8787; Vite dev at 3000. Existing REST token header:
  `X-SentriFlow-Token`; WS subprotocols `sentriflow` and session token. Preserve these contracts.
- Existing working functionality: HTTP/HTTPS interception, redacted PII/tracker checks, independent
  held requests, persistent decisions, per-process chunk-based traffic rates, alerts, score,
  Windows proxy/CA consent/recovery, and offline vector country map.
- React/TypeScript/Zustand/Recharts/Leaflet frontend; authenticated snapshots and event updates,
  reconnect, multiple-client sync, actual traffic/Halt/rules/settings pages.
- Existing integration record reports 163 backend / 11 frontend tests; baseline has not yet been
  rerun in this isolated worktree. These are historical results, not current verification.

## What monitoring actually observes

- Proxy supplies destination, request URL transiently, headers/body transiently for existing local
  inspection, process identity, response status/IP/country, timing and measured payload counters.
- No browser extension or browser-API telemetry currently exists. Camera/microphone/location
  permission requests, successful JS API calls, fingerprinting API use, localStorage reads, and
  the currently focused browser tab are not observable from proxy metadata alone.
- Plan: identify page navigations when request metadata supports them, keep background/subresource
  traffic distinct, and report an observed page rather than falsely claiming the focused tab.
- Privacy expansion will use bounded redacted metadata and evidence statuses. Do not store raw
  URLs/query/form values, tokens, cookie values, passwords or card values in ML inputs/events.

## ML decision, data and status

- Actual model: not implemented at this checkpoint; no synthetic or hardcoded risk output.
- Candidate models: Random Forest first; compare Logistic Regression using identical live-derived
  URL/domain numerical features. Use disjoint registered-domain groups for fitting, selection,
  calibration and final evaluation; remove conflicting/duplicate URLs.
- Dataset selected for inspection: UCI PhiUSIIL, ID 967, authors Arvind Prasad and Shalini Chandra.
  Official source: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
  License: CC BY 4.0. UCI documents raw URL strings, 235,795 rows and original label 1=legitimate,
  0=phishing. Positive-class mapping must be explicitly inverted to 1=phishing.
- Dataset has not yet been downloaded or inspected locally. Training must recompute features
  from raw URLs instead of using precomputed label-derived reputation/similarity columns.
- Proposed inputs: bounded URL/domain length and structure, digit/hyphen/subdomain statistics,
  observed scheme, IP-literal/punycode indicators. No reputation, domain-age or browser behavior
  feature unless the same measurement exists in both training and runtime.
- Feature extraction, trained artifact, inference integration, evaluation metrics and calibration:
  pending. Export a safe versioned artifact; validate trained/exported inference parity and the
  positive class. Report phishing-scope limitations and missing evidence clearly.
- Training source guidance reviewed: official UCI dataset metadata and scikit-learn calibration
  documentation. Exact download/hash, inspected columns, split counts/features and metrics will
  be recorded at the data/training milestone.

## UI state

Existing full dashboard is functional. Compact floating-style risk view, explicit analysis/loading/
missing-evidence states and expanded website/transparency detail are pending. Preserve black and
papaya-orange branding and useful existing controls; do not create a second frontend.

## Important files and dependencies

`application.py`, `proxy/addon.py`, `core/models.py`, `inspection/pipeline.py`, `api/server.py`,
`api/ws.py`, `storage/repositories/`, `frontend/src/App.tsx`, `api/types.ts`, `api/ws.ts`,
`hooks/useLiveTraffic.ts`, `store/trafficStore.ts`, and existing UI pages are the integration points.
`scripts/build.py`, `scripts/check-browser.py` and existing unit/integration tests are reusable.
`backend[ml]` currently declares scikit-learn but is not connected to execution. No dependency
changes have been made yet.

## Commands

From this worktree (a separate environment will be installed here):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev,browser,ml]"
npm --prefix frontend ci
.\.venv\Scripts\python.exe -I scripts/build.py
.\.venv\Scripts\python.exe -I -m sentriflow run
.\scripts\test.ps1
```

Training/reproduction commands and new website API routes are pending implementation. Do not
use the original checkout's editable environment for this worktree.

## Completed / remaining / next checkpoint

Completed: prompt read, dirty-worktree assessment, remote fetch, safe isolated `reform` worktree,
updated integration base, actual monitoring/API/UI assessment, initial dataset/license research.

Next: commit/push this assessment; install isolated dependencies and run baseline checks; inspect
official dataset and implement reusable feature extraction/data preparation; commit/push that
checkpoint. Then train/evaluate/calibrate/export, integrate live inference and observable privacy
evidence, redesign the existing UI, perform actual browser/regression verification, and push final.

Known limits: no model or new UI yet; dataset license/metadata reviewed but no local data-quality
verification; proxy cannot prove JS API access/focused-tab state. Model percentages must remain
absent until a valid artifact and actual inference exist.

Git delivery: assessment commit and `origin/reform` creation are the immediate next action.
Subsequent checkpoints will list successful commit IDs, test outcomes, failures and exact blockers.
