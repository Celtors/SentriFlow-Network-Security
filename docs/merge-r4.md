# R4 merge integration

The R4 branch introduced a complete prototype backend as well as the dashboard. Its initial
frame WebSocket auth, synchronous repositories, database JSON shape and runtime settings
differed from the already merged R1/R2/R3 implementation. The merge uses one application
runtime and database, preserving R1's standalone spike and R3's security/privacy and blocklist
work while integrating the R4 UI, offline country map, streaming metrics and proposal assets.

Contract decisions:

- `application.Runtime` remains the composition root; `runtime.py` aliases it. The integrated
  proxy/API runner owns lifecycle and the per-data-directory session lock; `launcher.py`
  delegates to it. The standalone R1 spike remains available.
- REST accepts the existing session header/Bearer token. WebSocket authenticates in the
  `sentriflow` subprotocol handshake. The UI supports the printed URL fragment and manual
  login. It fetches `/snapshot` after connecting and unwraps canonical Halt envelopes.
- Shared settings use `large_upload_bytes` and `tracker_policy`. CA install requires
  `{confirmed:true}`. Rule editing uses `PUT /rules/{id}` rather than creating duplicate IDs.
- New remembered rules use the executable identity when known. Legacy name/domain/wildcard
  rules remain readable. Uninspected requests cannot create an always-Allow rule.
- Existing masked history and rules upgrade through migrations 001 and 002. An incompatible
  R4 prototype JSON database is rejected before migration: preserve its directory and select
  a fresh `--data-dir` for the merged app. It is never overwritten or silently reinterpreted.
- Pattern definitions retain the existing local persistence/regex support; snapshots omit
  their values. The UI accurately labels them as stored locally. The existing transparent
  weighted privacy-score formula is displayed instead of the other branch's ratio formula.
- Outgoing requests remain buffered for inspection. Response chunks update session counters
  and rates before completion. Observed IPs feed the offline MMDB map; no hostname enrichment,
  remote IP service, online tiles or automatic data download is introduced.

The root README is retained as the merged entry point. R4's proposal sources, draft PDF,
diagram exports, historical screenshots and original measurement JSON remain preserved.
Branch handoff/status documents describe their original checkouts; contract details in
[api.md](api.md), [architecture.md](architecture.md) and this note describe the merged app.
The draft proposal/diagrams should be regenerated against these final contracts before
submission. No generated historical evidence is presented as a fresh Windows acceptance run.

Validation includes the existing R1/R2/R3 tests plus R4's real HTTP/HTTPS, streaming and offline
GeoIP cases, with added v1 migration and dashboard snapshot/rule/settings checks. The rendered
dashboard also completed three local dummy Halt cycles, remembered/edited/deleted a rule,
saved settings, showed download rates before completion, opened details/alerts, and rendered
the offline vector map at desktop/mobile widths. The merge rehearsal made **zero external
browser requests** and no system proxy, trust-store or firewall changes. Its generated
screenshots/report are under the ignored `.runtime/r4-merge-evidence/` directory.

To reproduce the browser check after installing `backend[browser]` and building the UI:

```powershell
.\scripts\build.ps1
.\.venv\Scripts\python.exe -I scripts/check-browser.py --evidence-dir .runtime/r4-merge-evidence
```

On a Linux developer machine with Chrome installed, add
`--browser-path /usr/bin/google-chrome`. The optional `--public-map-check` is unnecessary
for the offline rehearsal and was not used for this merge.
