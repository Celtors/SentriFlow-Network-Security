# Status against specifications and the existing build plan

Merged runtime/contracts: see [merge-r4.md](merge-r4.md). The branch-specific history and evidence below are preserved from R4's original checkout.

Updated 27 October 2026. The current baseline is branch `dev`, initially at `711dba2` (`feat: initiating repo structure`). It provided the folder/contract plan, one CLI placeholder, one smoke test and a Vite starter; the substantive backend modules and most frontend modules were empty. This work fills that scaffold. The earlier separate implementation in the sibling copy is not the application used here.

## Implemented core

| Scope | Evidence and limits |
| --- | --- |
| S01 environment/structure | Existing `backend/src/sentriflow` preserved; package/CLI, scripts, CI and checks work locally. Clean teammate setup is pending. |
| S02 proxy and CA | Embedded in-process mitmproxy, loopback, unique CA, explicit consent installation/removal. Explicit Windows proxy enable, durable snapshot/restore and hidden crash watchdog implemented. Actual OS mutation not exercised by automated checks. |
| S03–S04 capture and process mapping | Planned Flow model and WS events, psutil endpoint match, short bounded cache. 3/3 attribution in local demo; representative 90% target unmeasured. |
| S05 storage | SQLite WAL/schema v1, repositories, redacted flow/alert records, rules/settings, retention and restart recovery. Reserved schema for patterns/baseline is not a claim that those extensions are persisted. |
| S06 REST/WS | API/dashboard 8787, proxy 8080, Vite 3000; planned `/api` routes and `/ws` events, token/Origin/Host/peer checks. |
| S07 blocklist | Hosts/plain domains plus simple `||domain^` subset, normalization/subdomain tests, explicit CLI import. Demo seed only; full licensed feed and complete EasyPrivacy grammar remain. |
| S08 PII | Email, Indonesian-phone heuristic, Luhn card candidates, session-sensitive literals. Supported bounded text/JSON/form/XML, gzip/deflate and simple multipart fields. Unsupported/Brotli/files/truncated content is incomplete and prompts. Regex literals are intentionally not supported. |
| S09 Halt | Real before-forward Future/deadline, once/always decisions, saved-rule precedence, unknown-large upload check, timeout/shutdown/capacity Block, persistence failure cleanup. |
| S10–S12 frontend | Actual React/Zustand/Recharts dashboard, filterable traffic, pending modal/countdown, rule action editing/deletion, sensitive literals, routing/CA controls, reconnect/resync. Black/papaya orange palette retained. |
| S11 live rates | Response chunk counters and one-second per-process `speed.tick`, tested before stream completion. Payload rates only, not all-device bandwidth. Outbound request streaming remains disabled for inspection. |
| S13 alerts/score | Redacted findings and disclosed blocked-risk ratio, no starting score without observations. |
| S17–S18 tests/demo | Domain/API/real HTTP/HTTPS/streaming tests, frontend tests, local dummy origin/form, actual Edge check/screenshots/report. |

## Partial and pending work

- S14 offline map: implemented by R4 with local DB-IP Lite MMDB, bundled Natural Earth shapes and Leaflet. Aggregation uses observed/literal destination IPs; unknown/private/unmatched counts remain visible. No external IP lookup, DNS enrichment or map tiles. See [R4 delivery](r4-delivery.md).
- S15 TLS/pinning/QUIC: failure metadata is honest about uninspected traffic; exact cause is not inferred. Real pinned-app matrix and reversible QUIC helper implementation/demo validation remain. No firewall changes were made.
- S16 anomaly/ML: scaffold remains reserved; no trained model or behavioral baseline is claimed.
- S19 integration: local core demo works; clean Windows 11, long-run load, broad app coverage and real crash restoration remain acceptance work.
- S20 measurement: actual small local report/screenshots exist; representative KPIs, rehearsal and backup video do not.
- S21 release: setup/check scripts and documentation exist; no release tag, freeze, remote CI, PR or push was performed.
- Notifications: permission-based browser notification fallback is implemented for background held events; OS delivery/focus behavior needs manual validation.
- CLI `reset` explicitly refuses deletion rather than silently deleting local data or leaving a trusted CA without removal information.

## Proposal work

The English full-proposal draft, consistent cover and five Mermaid diagrams are populated under `docs/proposal`. R4 exported all diagrams to SVG/PNG and assembled a 13-page A4 PDF working draft with genuine screenshots. References describe the implementation and link primary technical/data documentation. A validation kit is prepared; no participant contact, survey outcomes, quotes or field KPI evidence were invented. Official competition guide, current deadline, page/rubric confirmation, independent peer review, final revision and submission remain.

The concept's numerical IBM 2026 and PP 33/2026 claims were not independently validated and are not repeated as facts. The spreadsheet's dates and task owners are planning inputs, not constraints on implementation or authority to submit externally.

## Next steps

1. Run [Windows setup](windows-setup.md) on the intended Windows 11 machine; manually accept routing/CA only when desired and test restore after normal stop/forced kill.
2. Measure attribution and detector precision across representative apps/fixtures, then stabilize before adding extensions.
3. Import a reviewed/licensed blocklist and assess parser coverage; assess geographic coverage/accuracy and add baseline only if core remains reliable.
4. Obtain official competition rules, collect consented validation, finalize proposal/figures, rehearse and record backup video.

The user's existing deletion of root README.md was left intact. Start with `backend/README.md` and `docs/windows-setup.md`. Git changes remain uncommitted in this working tree.
