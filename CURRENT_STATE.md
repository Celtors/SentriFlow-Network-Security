# CURRENT STATE - reform

Updated: 16 November 2026 (Asia/Jakarta). Status: IMPLEMENTED, LOCALLY VERIFIED, AND PUSHED. Original ML/UI delivery completed 15 November; latest policy follow-up is below.

## Latest follow-up: binary-body Halt exclusion, 16 November 2026

Status: IMPLEMENTED, LOCALLY VERIFIED, AND PUSHED to `origin/reform` in `24f67d5`
(`fix: exclude binary bodies from automatic Halt prompts`). This section supersedes earlier
binary-body Halt behavior; the original delivery record below remains historical.

- User request: stop binary request bodies from flooding the Allow/Block queue.
- Binary MIME types are excluded before text decoding/decompression, while URL/header
  checks remain enabled. Non-UTF-8 untyped/multipart bodies are also treated as binary.
- Exclusions create an `inspection_skipped` note in Traffic and `not_inspected` status,
  without a Halt or an alert solely because the body is binary. Raw bodies are not stored.
  These notes alone are excluded from the dashboard's risky-request counts.
- Saved rules, PII/custom strings in URL/headers, tracker policies and the independent
  unknown-process large-upload check still apply. Text decoding/size/encoding limits,
  JSON errors and inspector failures retain their existing enforcement behavior.
- Binary-body content is outside PII coverage. Transport-size limits still apply.
- Validation: 193 backend tests passed, 3 existing manual acceptance cases skipped.
  Ruff check/format and strict mypy for core/inspection passed. Real loopback-proxy tests
  verify repeated octet-stream/Protobuf forwarding unchanged with no Halt events/alerts,
  exclusion from risk counts, PII-header Halt, saved Block and tracker Block behavior.
  No Windows system routing or CA trust was changed during these checks. Frontend and
  model files are unchanged; native Google Meet traffic was not replayed in verification.
- Restart the backend after updating to discard old pending holds and load the policy.
  No frontend rebuild, CA installation or model retraining is needed for this change.

## Objective and repository

Implement genuine phishing-risk inference inside the existing SentriFlow app,
preserve traffic/privacy controls, provide a compact floating-style view and
expanded details, keep sensitive values out of ML, and push recoverable milestones.
No browser extension. Latest user implementation prompt is the primary spec.

- Remote: https://github.com/Celtors/SentriFlow-Network-Security.git
- Worktree: `D:/ITBx_Sem5/SentriFlow/SentriFlow-Reform`, branch **reform**.
- Base: fetched current `origin/merge` e670eab, not the stale local merge checkout.
- Original `SentriFlow-Network-Security` checkout remains on merge; unrelated dirty
  proposal/setup/lockfile changes are untouched. No reset/discard/force push.
- Confirmed pushed: **12bd8f5** assessment; **93bbcf9** data/feature foundation.
  **51fc4c4** trained/calibrated model; **bf6158a** live inference/privacy integration.
  **d7f866b** compact UI, real browser evidence, hardening and documentation.
  All five implementation checkpoints were successfully pushed to origin/reform;
  remote HEAD d7f866bad64814741ecba74d712a6c19f205e7f6 was verified.
  The final documentation checkpoint carries this refreshed handoff; use git log
  for its revision. No implementation remains solely in this local worktree.

## Existing architecture retained

`backend/src/sentriflow/application.py` Runtime composes async SQLite repositories,
EventBus, HaltManager, inspection, rules, tracker/GeoIP intelligence and process
resolver. mitmproxy/API run on one asyncio loop. Proxy 8080, API/UI 8787, Vite 3000.
Authentication: X-SentriFlow-Token or existing Bearer header; WS subprotocols
sentriflow + token. Host/Origin checks remain mandatory for new routes.
React/TypeScript/Zustand/Recharts/Leaflet existing frontend, no duplicate app.

Retained HTTP/HTTPS interception, redacted PII/tracker checks, independent held
requests, remembered rules, alerts, persistent redacted history, per-process
streaming byte rates, offline vector map, Windows routing/CA consent and recovery.
Core/inspection must not import API/proxy/OS adapters (CONTRIBUTING).

## Model, data, artifacts - COMPLETE and verified

- Official UCI PhiUSIIL dataset 967, Arvind Prasad and Shalini Chandra (2024).
  Source: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
  License CC BY 4.0; attribution/adaptations in **docs/ml-model.md**.
- Archive ignored at `.runtime/datasets/phiusiil-verified.zip`, 15,376,007 bytes,
  SHA256 0a639fd03aea6308c5b1c10c92aa23c2ce1505447a9137271865cd0badc9a59a.
  Public URL strings are never visited; no raw dataset committed.
- 235,795 rows, 56 actual columns. Source label 1=legitimate/0=phishing;
  **explicitly inverted to positive 1=phishing**. Discard other source features.
- Schema **2**: canonical origin removes www prefix, path/query/userinfo/fragment.
  Initial 24-feature path model was rejected by ordinary-address smoke probes
  due to collection-format bias. It is NOT the shipped artifact.
- Final 13 numeric features: hostname length, HTTPS scheme, IP literal, subdomain
  count, longest label, suffix length, domain digits/ratio/hyphens/entropy,
  punycode, host dots, nonstandard port. Definitions in model card and extractor.
- Shared **ml/features.py** for training/live; tldextract bundled PSL only, no
  runtime suffix downloads. No passwords/tokens/cookies/forms/browser behavior
  are inputs. HTTPS is a scheme observation, not a trust assertion.
- 14,414 origin duplicates, 12 conflicting origins removed, 0 invalid rows;
  retained 221,369 origins / 197,699 registered-domain groups including private PSL.
- Domain-disjoint fit/selection/calibration/test: 135,209 /21,561 /32,310 /32,289
  rows; zero group overlap asserted. Seed42. Final test 20,147 legit/12,142 phishing.
- Random Forest 96 trees/depth12/min leaf8 beats scaled Logistic Regression on
  selection AUC .969612 vs .964816. Isotonic calibrated only on separate domains.
- Test precision .983424, recall .908829, F1 .944656, AUC .970029, accuracy .959955.
  TN19961/FP186/FN1107/TP11035; FPR .009232, FNR .091171. Brier .036154 -> .035100;
  ECE10 .002652. Internal-corpus evaluation, not production/temporal guarantee.
- **backend/src/sentriflow/data/models/website-risk.json**, ~2.1MB, safe data-only
  learned tree export, calibration knots and train medians. SHA256 sibling file.
  **data_report.json**, **training_report.json** contain provenance/counts/metrics/
  reliability bins/class summaries/global importance and environment versions.
- **ml/predictor.py** validates checksum/schema/class/tree and matches sklearn
  float32 traversal. Whole test-set export parity max absolute error 3.062e-14.
  Runtime needs no sklearn/numpy/network/training. Missing artifact -> unavailable.
- Percentage=100*isotonic-calibrated positive-class inference (one decimal).
  Display low<30/medium30-<70/high>=70; fixed policy, not tuned on test.
  Explanations rerun model replacing each feature with training median; local
  sensitivity only, not causal/additive or invented browser-behavior reasons.
- Sanity probes: YouTube home and watch path identical 4.9%, Google/GitHub 4.4%;
  these are unlabelled smoke examples, not additional accuracy measurements.

## Live integration and frontend - COMPLETE and browser verified

- Runtime loads the shipped model once; off-loop inference with bounded concurrency.
  Only canonical scheme/hostname/port reaches model.analyze: query/path/userinfo
  never cross that boundary. Model failures report unavailable, enforcement stays on.
- `website/service.py`: 50 bounded memory-only summaries /1000 request links.
  Sec-Fetch document/navigation identifies latest observed page, background traffic
  does not replace it. Referrer/Origin host/process associates related requests.
- Browser/device header and cookie PRESENCE only: attempt before forwarding,
  transmission observed after upstream response; recipient read/storage unconfirmed.
  Cookie response presence, external domains, redirects and payload counts included.
- `website/observations.py`: unchanged response byte tee,128KiB decoded/256KiB wire
  bound, identity/gzip/deflate. Static form/input types/action hostnames, no values.
  Honors inspection toggle, unsupported encodings/charset/parse failures unavailable,
  partial samples disclosed. Parser buffers discarded at completion. Arbitrary HTML
  parser errors must not interrupt the actual transfer (new regression test).
- Runtime/proxy hooks, authenticated GET /api/websites, /api/websites/{id},
  /api/model/status, initial snapshot and website.updated events integrated.
- `frontend/src/components/WebsitePanel.tsx`, `website.css`, App/store/hook changes:
  black/papaya compact-first card, actual percentage, risk tier, local sensitivity
  reasons, recommendation, clear loading/missing/error/stale states. Expanded
  Website tab has history selector, privacy evidence, destinations, model details.
  Other dashboard tabs and global Halt decisions preserved. No extension.
- Small separate browser window via top-right arrow; OS controls always-on-top.
  Compact choice persists only per browser session. Followed page survives bounded
  background-history eviction; selecting an evicted entry falls back to current.
- **scripts/check-reform.py passed in real Edge**, using loopback-only HTTPS origins
  with public-shaped names and the actual shipped model (4.9% /100% test outputs,
  not hardcoded). Checks compact/default, actual HTTPS navigation, WS updates,
  static forms, explicit unavailable browser APIs, redaction, model details,
  expanded layout, mobile390px, authenticated popup and reload synchronization.
  Browser errors empty. Screenshots visually reviewed.
- **scripts/check-browser.py passed**: real CLI startup, compact-to-expanded flow,
  Halt once/remember/reload, Allow/Block, rules CRUD and cross-client sync, settings,
  bytes/rates before transfer completion, request details, alerts and offline map.
  4/4 synthetic PII samples detected; max click-to-response37.7ms (small local sample).
  No external browser requests or JS errors. No OS routing/CA trust changed.
- Evidence: **docs/evidence/reform/** (browser/performance reports + screenshots);
  legacy regression report/screenshots under **reform/legacy/**. Test fixture routing
  in verification.py is opt-in only; real application has no public-host remapping.
- Warm local inference including explanations,150 samples: median 2.920 ms / p95 4.248 ms,
  model load100.117ms. Microbenchmark only, not representative long-running load.
- CI workflow triggers now include reform. Runtime lock adds tldextract5.4.0 and
  requests-file3.0.1. Build packager validates its deletion target before replacing UI.

## Observability and limitations

Cannot identify focused tab, JS permission attempts/success, screen resolution,
canvas/WebGL execution or browser storage reads from proxy alone. Mark unavailable.
Sec-Fetch document/navigation identifies a most recently observed page only.
Referrer/Origin process association is approximate across same-host tabs.
Header presence is attempted before forwarding; upstream response permits an
observed transmission, not proof of receiver read/storage. Cookie values discarded.
Static form structure is not evidence of filled/submitted values. Compressed/
uninspected/unsupported HTML must remain unavailable. No hidden script injection.

Model cannot detect all malware, phishing on compromised legitimate hosts or
page-path content. Source corpus has HTTPS/source bias (about 46% forest importance).
No production labels/external or temporal validation, prior correction or guarantee.
Summaries are memory-only, bounded to 50, restart clears them; existing redacted
flow/rule persistence retained. No automatic blocking solely from model estimate.

## Validation

- Full scripts/test.ps1 gate passed: **179 backend tests passed,3 skipped**, Ruff
  lint/format, mypy core/inspection, ESLint, frontend tests and production build.
  Latest full-gate rerun also passed: **179 backend passed /3 skipped,18 frontend
  passed**, Ruff lint/format, mypy, ESLint and production build. The current-page
  history cap and origin-only model boundary regressions are included. The three
  skipped cases are existing Windows console-termination manual-acceptance tests;
  browser verification separately exercised real Windows CLI startup.
- Actual sklearn training and all32,289-row exported inference parity passed.
  Shipped model loads without training; corruption/schema/positive-class tested.
- Real reform browser and legacy browser checks both passed (details above).
- pip check: no broken requirements. npm runtime-only audit **0 vulnerabilities**.
  Full npm audit:9 moderate development-tool advisories via minimatch/ESLint/
  TypeScript-ESLint. No forced downgrade/major replacement. Dependency deprecation
  warnings remain (pytest-asyncio scope, Starlette/httpx, ldap3/pyasn1).
- Local wheel build passed. Package includes trained model/checksum/reports/
  attribution and compiled UI, with no dataset/database. Isolated --target install
  imported the wheel package (not editable source); actual inference, application
  startup, authenticated model status, rejected missing token and dashboard serving
  passed without retraining. See package-report.json. A mistyped initial package
  name produced an unrelated ignored wheel, never installed or part of delivery.
- CI triggers include reform; remote Actions result is not claimed verified. All
  stated passing gates were actually run locally in this isolated worktree.

## Commands

From THIS worktree, separate venv (Python3.13 here, project >=3.12):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "backend[dev,browser,ml]"
npm --prefix frontend ci
.\.venv\Scripts\python.exe -m sentriflow.ml.train --dataset .runtime/datasets/phiusiil-verified.zip
.\.venv\Scripts\python.exe -I scripts/build.py
.\.venv\Scripts\python.exe -I -m sentriflow run
.\scripts\test.ps1
```

See **docs/ml-model.md** for official download command/hash, schema definitions,
licensing, reproducibility and calibration limits. Clone users do NOT need to
train: artifact is included by setuptools package data `data/**/*`.
Added runtime dependency tldextract>=5.4,<6; sklearn remains training-only extra.
Do not use original checkout editable environment, private browsing data or secrets.

## Completed / remaining / next actions

Completed: safe synchronization, recoverable pushed checkpoints, licensed public
corpus inspection, leakage-controlled preparation, real model comparison/training/
calibration/evaluation/export, shipped artifact, live inference/privacy hooks,
authenticated API/WS integration, compact/expanded UI, real Edge checks, legacy
regression, full static/test/build gate and installed-wheel verification.

Implementation status: SUCCESS for the specified end-to-end local product scope.
No known failing gate, missing trained artifact, broken integration or push blocker.
The original checkout's user edits were preserved. Current worktree is separate;
run the new app from **SentriFlow-Reform**, not the unchanged merge checkout.

Ready-to-run here (dependencies and packaged UI already installed):

```powershell
cd D:\ITBx_Sem5\SentriFlow\SentriFlow-Reform
.\.venv\Scripts\python.exe -I -m sentriflow run
```

On a fresh clone run setup/build per README first; no model training is needed.
For continuation: read this file and docs/ml-model.md, verify current git status,
then choose only explicitly scoped follow-up improvements. Reproduce checks using
scripts/test.ps1, scripts/check-reform.py and scripts/check-browser.py. Exact final
results are in docs/evidence/reform/validation.json and linked evidence reports.

Limits deliberately not claimed complete: native Windows system-wide routing/CA
acceptance, production traffic accuracy, external/temporal datasets, focused-tab/
browser-API telemetry, long-running participant trials and OS always-on-top control.
These are explicitly disclosed product/evaluation limits, not fabricated features.
