# Integrated implementation status

Updated 27 October 2026 (Asia/Jakarta), after integrating R1, R2, R3 and R4 on the merged
repository. This is the current status; the individual role handoffs and earlier measurements
remain historical evidence. The implementation follows `SentriFlow_Build_Plan.md` and the
named assignments in the tracker.

| Area | Integrated behavior |
| --- | --- |
| Routing / interception | Embedded loopback mitmproxy, source-address/source-port attribution, metadata capture, per-install CA, explicit Windows routing/trust and restore/watchdog adapters |
| Runtime / decisions | One asyncio runtime for API and proxy; independent Halt futures, deadline/default Block, once/always rules, shared schema and application-owned signal cleanup |
| Inspection / data | Bounded PII, Luhn and custom literal/regex inspection; masked persistence; SQLite WAL and v1-to-v2 migrations; validated local blocklists and cache invalidation |
| Dashboard | R4 React/Zustand/Recharts UI, live streaming rates, traffic detail/search, Halt queue, remembered rules, alerts, settings and browser notification permission |
| Live state | Token-authenticated WS handshake, initial authoritative snapshot followed by queued events, reconnect restoration, cross-client configuration notifications, stale-response protection |
| Geography | Observed/literal IPs only, local MMDB country lookup, bundled Leaflet vectors, explicit missing/private/unmatched accounting; no DNS enrichment or online tiles |
| Lifecycle / commands | Session ownership shared by launch/seed/reset; imports inside the running session's startup; normal shutdown restores routing before closing services, database and lock |
| Build / docs | One cross-platform dashboard packager used by PowerShell; configurable dev API target; visible dev login token; current API/status docs and regenerated proposal diagrams/PDF |

Run `.\scripts\setup.ps1`, `.\scripts\build.ps1`, then `.\scripts\run.ps1` on Windows.
Linux commands, the combined check procedure and evidence are in [integration.md](integration.md).
The runtime defaults remain proxy 8080, API/dashboard 8787 and Vite 3000.

Validation: **163 backend tests and 11 frontend tests passed**, with lint, formatting,
core/inspection type checks and the production build. The browser sample detected all seeded
labels and attributed 4/4 local requests. DOM-click-to-response timing was at most 131.2 ms;
automation roundtrip including Playwright waiting reached 1115.41 ms. Both timings, and an
earlier loaded-host run, are retained. These are small local measurements.

Current automated/browser evidence is in [evidence/integration/validation.json](evidence/integration/validation.json).
The fresh local browser rehearsal exercises dummy decisions, remembered-rule editing/deletion,
settings, streaming, details/alerts, desktop/mobile map rendering, a held request surviving
reload, and rule changes from a second API client. It does not mutate real OS proxy/trust or
firewall settings. Historical Windows backend evidence remains in `evidence/kpis-windows.json`.

Native Windows browser attribution over a representative session, real registry restoration
after normal/forced exit, trust-store acceptance, pinned-app/QUIC compatibility and long-run
stability remain manual acceptance. The country MMDB and production feeds must be installed
explicitly; none is fetched at runtime. Anomaly/ML, native notification/QUIC helpers and the
backup recording remain deferred. No release, deployment or submission is implied.

The proposal sources and working-draft PDF now describe the integrated contracts, including
schema v2, persistent local patterns, weighted score and WS subprotocol auth. User validation,
official-rule confirmation and final independent review are still needed before submission.
