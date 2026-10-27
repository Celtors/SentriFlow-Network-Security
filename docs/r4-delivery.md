# R4 delivery

Merged runtime/contracts: see [merge-r4.md](merge-r4.md). The branch-specific history and evidence below are preserved from R4's original checkout.

27 October 2026, Asia/Jakarta. This work extends the current `backend/src/sentriflow` scaffold and preserves its ports, contracts and black/papaya-orange theme. Existing unrelated working-tree changes and the deletion of the root README are preserved.

## Deliverables against the tracker

| ID | Result |
| --- | --- |
| S10 frontend and WebSocket | Existing React/Zustand live client retained, with current backend contract. No separate mock-only dashboard introduced. |
| S11 live traffic | Existing streaming rates retained; both upload and download rates shown per app. Traffic search includes recorded reasons/findings, with redacted request detail, observed destination IP and country when known. |
| S12 Halt and rules | Existing once/always queue and rule editing retained. A failed decision is visible inside the prompt; remembered uninspected Allow is disabled with an explanation. |
| S13 alerts and privacy score | High/medium severity filtering, alert-to-request detail, disclosed score numerator/denominator and scope. No fabricated initial score or raw PII display. |
| S14 offline map | Leaflet vectors, bundled 177-country Natural Earth shapes, local DB-IP Lite country lookup, observed-IP aggregation, country filter/table, private/unobserved/unmatched counts and attribution. |
| P03 cover | Team Senklok, title and supplied member names in `proposal/cover.json`, used by the HTML/PDF exporter. Only the institution explicitly confirmed in the source is printed. |
| P08 diagrams | All five actual Mermaid sources exported to **SVG and PNG** under `proposal/diagrams/exported/`. Includes actual API, Halt, entities, architecture and user actions. Reserved schema is identified in the prose rather than presented as implemented functionality. |
| P13 assembled draft | English [Markdown](proposal/FPH_Senklok.md), local [HTML](proposal/FPH_Senklok.html), and [A4 PDF working draft](proposal/FPH_Senklok_DRAFT.pdf). **13 pages total**, including cover and references. Real dashboard/Halt/map screenshots included. |

The PDF remains a working draft. Real survey/interview evidence, official competition-guide confirmation and independent team review are still required before final submission. No survey findings, quotes, affiliation details, field KPIs or submission confirmation were invented.

## Run and reproduce

Current local frontend build and MMDB have been prepared:

```powershell
.\scripts\run.ps1
# Open http://127.0.0.1:8787 and paste the terminal token.
```

For another checkout, prepare the offline assets explicitly, then build:

```powershell
.\.venv\Scripts\python.exe scripts/prepare-map-data.py --month 2026-10
.\scripts\build.ps1
```

This manual command downloads public map data; the running guardian never downloads it automatically. Country shapes are committed, while `*.mmdb` stays ignored. The default lookup path is `backend/src/sentriflow/data/geoip/dbip-country-lite.mmdb`; override it using `SENTRIFLOW_GEOIP_DATABASE`. Restart after replacing a database. Provenance, edition, license and hashes: [map-data.json](map-data.json) and [third-party notices](../THIRD_PARTY_NOTICES.md).

To rebuild all five diagram sets and the PDF using locally installed Microsoft Edge:

```powershell
npm ci --prefix docs/proposal/tools
.\.venv\Scripts\python.exe -m pip install -e "backend[browser]"
.\.venv\Scripts\python.exe scripts/export-proposal.py
```

The exporter blocks external requests, verifies all document images load, and records PDF hash and page count in [export-report.json](proposal/export-report.json). Cover metadata and proposal Markdown are the editable sources; generated HTML/PDF/SVG/PNG should be rebuilt together.

## Verification and evidence

- **48 backend tests passed**, including new missing/corrupt database, private-IP exclusion, no-hostname lookup, observed-IP recording and aggregation tests.
- **8 frontend tests passed**, including new traffic details, severity filter, country accounting, and failed/uninspected Halt decision tests.
- Ruff, formatting, strict mypy on pure layers, ESLint and TypeScript/Vite build passed. Proposal renderer install reports zero dependency advisories after updating Mermaid to 12.2.
- Real Edge check passed request details, high-priority alerts, remembered rule editing/deletion, settings, streaming rates, offline map and mobile width. `--public-map-check` made one explicit non-personal HTTP request to example.com through the proxy; its observed IP mapped to a country. **Zero external browser requests** were made by dashboard/map assets.
- [Measurement JSON](evidence/local-demo-report.json), [map screenshot](evidence/map.png), [mobile map](evidence/mobile-map.png), [alerts](evidence/alerts.png), [dashboard](evidence/dashboard.png) and [Halt](evidence/halt.png) are actual local artifacts. Three dummy PII requests had named attribution and displayed all seeded labels. This remains a small controlled sample.
- PDF verified with `pdfinfo`: 13 A4 pages. Cover and diagram pages were visually inspected. No external request was made during export.

## Boundaries

Country lookup uses an actual upstream socket IP or a literal destination IP; it never resolves recorded hostnames just to fill the map. Requests blocked before connecting may therefore remain unplotted. Local/private and old captures without observed-IP metadata remain explicit unknowns. Country estimates do not locate the recipient/person/company. Low-resolution country shapes omit some small territories; matched countries always remain in the accessible table.

The CA trust store, Windows proxy and firewall were not changed during these tests. Real OS notification delivery, comprehensive app attribution/PII precision, crash restoration and participant research remain acceptance work. No commit, push, release tag or competition submission was performed.
