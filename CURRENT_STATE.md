# CURRENT STATE ? reform

Updated: 15 November 2026 (Asia/Jakarta). Milestone: trained and evaluated ML model.

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
  Remote reform head was verified after each push. Next commit is model milestone.

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

## Model, data, artifacts ? COMPLETE and verified

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
  Display low<30/medium30?<70/high>=70; fixed policy, not tuned on test.
  Explanations rerun model replacing each feature with training median; local
  sensitivity only, not causal/additive or invented browser-behavior reasons.
- Sanity probes: YouTube home and watch path identical 4.9%, Google/GitHub 4.4%;
  these are unlabelled smoke examples, not additional accuracy measurements.

## Integration currently IN PROGRESS, not claimed complete

Working tree changes for next milestone (outside this model commit):
- `website/service.py`: bounded live summaries, actual transient request inference,
  navigation metadata vs background destination distinction, referrer/Origin host
  association, explicit missing evidence, redacted header presence/HTML forms.
- `website/observations.py`: bounded identity/gzip/deflate streaming HTML tee,
  static forms/types/external action host only, original bytes returned unchanged.
- Runtime/proxy hooks, authenticated /api/websites, /api/websites/{id},
  /api/model/status, snapshot fields and website.updated events being wired.
- React WebsitePanel and black/papaya compact-first App, expanded evidence,
  preserved old pages and popup button being implemented. UI lint/build pass.
- Next required work: meaningful website/live/proxy/privacy tests, HTML disabled
  inspection/caps/error coverage, integration fixes, UI state tests, real browser
  verification including actual live inference and legacy traffic/Halt/regressions.

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
page-path content. Source corpus has HTTPS/source bias (~46% forest importance).
No production labels/external or temporal validation, prior correction or guarantee.
Summaries planned memory-only bounded50, restart clears them; existing redacted
flow/rule persistence retained. No automatic blocking solely from model estimate.

## Validation so far

- Baseline before implementation: 160 backend passed/3 skipped, 11 frontend passed,
  frontend build passed. Latest integrated regression: 165 passed/3 skipped before
  feature-schema correction (not final validation).
- Current ML-only tests: **7 passed**, actual shipped artifact included. Ruff
  ML checks need rerun after formatting fix before this milestone commit.
- UI TypeScript/build/ESLint pass on in-progress compact/expanded implementation.
- npm ci reports9 moderate advisories; inspect actual packages and safe fixes before
  final. No force upgrades. Existing dependency deprecation warnings documented.
- Genuine full application/browser/expanded-detail verification remains pending.

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

## Precise next checkpoint

Push trained artifact/model card/schema2 fixes with this state. Then finish live
monitoring tests and integration; commit/push. Finish compact UI tests and real
browser smoke; commit/push. Run full gate and privacy/security/startup/export/
package checks, fix issues, update README/integration/current state and push final.
Record exact successful commits, test outcomes and any real blocker. No blocker
currently prevents local implementation or pushing to origin/reform.
