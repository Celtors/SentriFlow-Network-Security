# API contract implemented from the build plan

Local base: `http://127.0.0.1:8787/api`. Every API endpoint requires `Authorization: Bearer SESSION_TOKEN`. Loopback peer, Host and Origin checks apply. Browser Origins: HTTP localhost/127.0.0.1 on configured API port or 3000. No CORS access is granted. API docs/openapi endpoints are disabled.

| Method | Path | Result |
| --- | --- | --- |
| GET | `/health` | Liveness, proxy generation/routing/CA metadata |
| GET | `/snapshot` | Latest 200 flows, all pending, rules, public patterns, alerts, score, settings, processes, system metadata |
| GET | `/flows?limit=200&process=...&verdict=...` | Filtered history; limit 1–1000 |
| GET | `/processes` | Session payload totals and measured per-second rates |
| GET | `/halts/pending` | Pending Flow records with deadlines |
| POST | `/halts/{id}/decision` | `{action: allow|block, scope: once|always}`; 409 if expired/resolved |
| GET/POST | `/rules` | List or upsert exact process+host rule |
| DELETE | `/rules/{id}` | Delete existing rule; 204 or 404 |
| GET/POST | `/patterns` | Redacted listing or create session-only sensitive literal |
| PUT/DELETE | `/patterns/{id}` | Replace or delete an existing session pattern |
| GET | `/alerts` | Latest 200 redacted findings |
| GET | `/blocklist/status` | Source/count information and coverage note |
| GET | `/score` | Disclosed ratio and counts; null score when no resolved risks |
| GET | `/geo/destinations` | Offline country aggregates, database status and explicit unplotted counts |
| GET/PUT | `/settings` | Full replacement of inspection settings |
| GET | `/system/status` | Proxy/routing/CA metadata |
| POST | `/system/proxy` | `{enabled:true|false}`; enable requires running proxy |
| GET/POST/DELETE | `/system/ca` | Generated CA metadata, explicit consent installation, removal |

Decision `always` requires a known executable identity. Uninspected Allow must be `once`. Rules use `process_match` (SHA256 hex of executable path), `process_name`, normalized `host_match`, `action`, and optional `note`. No Unknown or wildcard rules. An exact host rule applies across paths and ports.

Pattern create/update: `{label,pattern,is_regex:false,enabled:true}`. At most 20 literals, each 1–256 characters. Values remain in memory; GET/public snapshots omit the secret. Regex mode is rejected instead of running untrusted backtracking patterns. This is a deliberate safe subset of the planning document.

Settings: `{inspection_enabled:true,halt_timeout_seconds:30,unknown_large_bytes:1000000,tracker_mode:"halt"}`. Timeout 2–120 s, threshold 1024–8,000,000 bytes, tracker mode halt/block. Missing values on PUT use defaults; changes apply to new requests.

## Flow model

`id`, `ts`, `updated_at`, `pid`, `process_name`, `process_key`, `method`, `scheme`, `host`, `port`, `path_masked`, `bytes_up`, `bytes_down`, `tls_status`, `verdict`, `verdict_source`, `state`, `reason`, `findings`, `deadline`, `status_code`, `country_code`.

States: started, held, completed, error. Verdicts: allow, block, halt. An allow verdict permits forwarding; it is not proof of successful delivery. `bytes_up` includes attempted body size even for blocked requests; measured upload rates count approved requests only. Streaming download bytes can advance while state remains started. No raw path/query, headers or body are exposed. `path_masked` is always `[omitted]`.

Findings expose label, type, location, and `[redacted]` sample only. TLS failures are `not_inspected`, without claiming that every failure was certificate pinning. Optional `destination_ip` holds an observed upstream peer or literal destination IP. `country_code` is populated by the local MMDB when available; private, unobserved and unmatched IPs stay null. Old stored flows remain readable with null defaults.

### Offline destination countries

`GET /api/geo/destinations` reads up to 10,000 retained flows. It returns `available`, `reason`, local database name/build epoch, `total_requests`, `destinations` and `unknown`. Each country contains `country_code`, `country_name`, `requests`, `blocked`, `bytes_up` (allowed payloads only) and `bytes_down`. Unknown counters are `no_observed_ip`, `local_or_private_ip` and `not_in_database`. Every retained request belongs to a country or one of these counters. No DNS or remote lookup is performed. Missing/corrupt local data returns unavailable with an explanation; it does not produce synthetic locations.

## WebSocket `/ws`

Connect with an allowed Origin. Send `{"token":"SESSION_TOKEN"}` in the first frame within five seconds. Missing/invalid token or forbidden Origin closes with 1008. Tokens never appear in URLs.

Envelope: `{type,ts,data}`. Events: `snapshot`, `flow.started`, `flow.completed`, `halt.requested`, `halt.resolved`, `speed.tick`, `alert.created`, `score.updated`, `system.status`, `settings.updated`, `rules.updated`, `patterns.updated`, `command.error`.

`speed.tick` contains per-process `bytes_up`, `bytes_down`, `upload_bps`, `download_bps`, and overall rates/elapsed seconds. It is emitted once a second from measured byte deltas. Download is counted by a response-stream callback; outbound request streaming remains disabled to preserve Halt-before-forward.

Client command: `{type:"halt.decide",data:{id,action,scope}}`; REST decisions are also supported. Invalid commands return a generic command.error. Queues are bounded to 128 events per client. An authoritative snapshot is sent after auth and periodically to repair missed events. Clients upsert flows by ID and resync on reconnect rather than assuming an uninterrupted audit stream.
