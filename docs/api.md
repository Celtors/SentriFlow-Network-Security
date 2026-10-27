# Backend API contract, v1

API: `http://127.0.0.1:8787`. Proxy: `http://127.0.0.1:8080`. Vite: `:3000`.
Every REST endpoint below requires `X-SentriFlow-Token: <per-run token>` or
`Authorization: Bearer <token>`. The CLI prints the token in the launch URL fragment,
which is not transmitted in HTTP requests. The frontend saves it in tab session storage
and removes it from the fragment after reading it. The login form also accepts that token.

Host must be `127.0.0.1` or `localhost` with the configured API port or dev port 3000.
Browser Origin must exactly match one of those HTTP origins. Missing Origin is permitted
for token-authenticated nonbrowser REST clients. WebSockets always require Origin.
No CORS permission is granted. Tokens are never accepted in query parameters.

| Method | Path under `/api` | Request / response |
| --- | --- | --- |
| GET | `/health` | `{status, proxy_running, system_proxy_enabled, ca_generated, pending_halts}` |
| GET | `/snapshot` | Latest 200 flows, all pending flows/deadlines, public patterns, rules, alerts, settings, score, session processes and system metadata |
| GET | `/flows` | `Flow[]`; filters `process`, `verdict`, ISO `since`, `limit` (1–1000), `offset` |
| DELETE | `/flows` | 204; clears history, related alerts and score events; retains rules/patterns |
| GET | `/processes` | Session process totals and measured `upload_bps`/`download_bps`, including streaming transfers |
| GET | `/halts/pending` | `Halt[]`, including masked flow and deadline |
| POST | `/halts/{id}/decision` | `{action:allow|block, scope:once|always}` → Decision |
| GET | `/rules` | `Rule[]` |
| POST | `/rules` | `{process_match?,host_match?,action,note?}` → 201 Rule |
| PUT | `/rules/{id}` | Same input → Rule; 404 for missing ID |
| DELETE | `/rules/{id}` | 204; 404 for missing ID |
| GET | `/patterns` | `CustomPattern[]` |
| POST | `/patterns` | `{label,pattern,is_regex?,enabled?,id?}` → 201 CustomPattern |
| PUT | `/patterns/{id}` | Same fields; path ID is authoritative |
| DELETE | `/patterns/{id}` | 204 |
| GET | `/alerts` | `Alert[]`; `limit`, `offset` |
| GET | `/blocklist/status` | `{sources:[{source,count,enabled}],automatic_updates:false}` |
| GET | `/score` | `{score,breakdown,weights,formula}` |
| GET | `/geo/destinations` | Local MMDB status, country aggregates and explicit unplotted counts; no DNS or remote lookup |
| GET, PUT | `/settings` | inspection toggle, timeout, upload threshold and tracker policy |
| POST | `/system/proxy` | `{enabled:boolean}`; Windows only, listener must be running before enable |
| GET | `/system/ca` | `{generated,trusted,thumbprint,supported}` |
| POST | `/system/ca` | `{confirmed:true}`; explicit current-user trust |
| DELETE | `/system/ca` | Remove this installation's CA from current-user trust by thumbprint |

`PUT /settings` accepts any subset of `inspection_enabled`, `halt_timeout_seconds` (0.05–300),
`large_upload_bytes` (1–1 GiB), `tracker_policy` (`ask`, `block`, `alert`). Unknown keys fail
validation. Listener ports and data paths cannot change through this route.

Rules require a host or process. `process_match` accepts an executable-path SHA256 identity
or a legacy case-insensitive process name. New remembered rules use the executable identity
when available and include a display `process_name`; old name/domain rules remain valid.
`host_match` is exact unless it begins `*.`. Wildcards require a subdomain
and do not match the apex. Specificity order is process+host, then exact host over wildcard,
then longer host pattern. Block wins a specificity tie; remaining ties use recency and ID.
Saved allow rules override inspection and tracker policy, so the UI should make their scope clear.

Response codes: 401 missing/invalid token, 403 untrusted Host/Origin, 409 expired/already
resolved Halt or failed OS action, 422 invalid input, 501 unavailable Windows routing.
The interception listener itself returns 403 for Block, or 503 if inspection fails.
An API decision response confirms the future was resolved; `flow.completed` confirms handling.

Public schemas are defined in `backend/src/sentriflow/core/models.py` and mirrored in
`frontend/src/api/types.ts`. All IDs are strings, timestamps ISO 8601 UTC, byte counts integers.
Flow fields: `id,ts,updated_at,pid,process_name,process_key,exe_path,method,scheme,host,port,
path_masked,bytes_up,bytes_down,tls_status,verdict,verdict_source,matched_rule_id,country_code,
destination_ip,state,reason,deadline,status_code,findings`.
Finding: `{type,label,severity,masked_sample,location}`. Halt: `{id,flow,deadline}`.
No public object contains raw request headers or bodies.

Connect to `/ws` with browser subprotocols `['sentriflow', token]`; the server selects
`sentriflow`. Invalid Host, Origin or token closes with 1008. A lagging subscriber closes
with 1013. Messages above 4096 bytes are rejected. Browser example:

```ts
const ws = new WebSocket('ws://127.0.0.1:8787/ws', ['sentriflow', token])
ws.send(JSON.stringify({
  type: 'halt.decide', data: { id: haltId, action: 'block', scope: 'always' }
}))
```

Every server event has `{type,ts,data}`. Types: `flow.started`, `flow.completed`,
`halt.requested`, `halt.resolved`, `alert.created`, `score.updated`, `speed.tick`,
`system.status`, `rules.updated`, `patterns.updated`, `settings.updated`. Initial `system.status`
includes `pending_halts`, `proxy_running` and an authoritative dashboard `snapshot`.
Fetch `/halts/pending`, `/flows` and `/score` on connection/reconnection to reconcile state.
Decisions are not automatically replayed across reconnects. Unanswered holds still time out.

`speed.tick` is `{interval_seconds,elapsed,upload_bps,download_bps,processes:[{process_key,
process_name,bytes_up,bytes_down,upload_bps,download_bps}]}`. Request bytes count on approval;
response bytes count as chunks arrive, before completion. Zero interval deltas produce idle
rates. Traffic bypassing the proxy and protocol overhead are excluded. Outgoing request
bodies remain buffered for inspection and Halt-before-forward.

The dashboard initializes from the first WebSocket status snapshot, then refreshes `/snapshot`
after state/configuration events. The subscription precedes the snapshot; queued events follow it. It unwraps the canonical `halt.requested` `{id,flow,deadline}` envelope into a held
flow for display. `/halts/pending` keeps that canonical envelope for existing REST clients.
Its settings use `large_upload_bytes` and `tracker_policy`; CA installation sends
`{confirmed:true}`. Rule editing uses `PUT /rules/{id}` and preserves the rule ID.

`/geo/destinations` covers at most 10,000 retained requests. It returns `available`, `reason`,
`database`, `build_epoch`, `destinations`, `total_requests`, and `unknown` counters for
`no_observed_ip`, `local_or_private_ip`, and `not_in_database`. Each country has code/name,
request/blocked counts and allowed-upload/received byte totals. Missing/corrupt MMDB data
is reported as unavailable; private or unobserved IPs are never fabricated or DNS-enriched.
