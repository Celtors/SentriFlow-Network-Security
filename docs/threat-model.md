# Threat boundary and known limits

- Remote web pages are untrusted. API commands need a per-run token, accepted Host/Origin and loopback peer. Null/foreign Origins are rejected. WS tokens are sent in the first frame, not logged URLs.
- Another process running as the same user, administrator access, a compromised dashboard and browser extensions with local access are outside the protection boundary. Executable path hashing is a rule identity, not signed-binary authentication.
- Only routed HTTP(S) is captured. Proxy-ignoring apps, QUIC, kernel/non-web traffic and mobile devices are outside scope. WebSocket forwarding is blocked until frame inspection exists.
- Body inspection is bounded to 256 KB. UTF-8 text/JSON/form/XML, bounded gzip/deflate, and simple non-file multipart fields are supported. Unsupported content, binary/files, Brotli and truncated input prompt as incomplete. Pattern matching can have false positives/negatives.
- Saved Allow rules deliberately authorize later inspected traffic for the process/host, including detected PII. Tracker auto-block and saved Block override them. Unknown-process rules are forbidden; incomplete Allow is once only.
- Raw request paths/queries, headers, payloads and matched values never reach SQLite or API flow events. Hosts, sizes and process metadata can still be sensitive. Session pattern values are not persisted or echoed.
- CA private keys must never be shared. Install trust only with explicit consent, remove by this CA's thumbprint and retain the public certificate until removal. Upstream certificate verification remains active. A failed TLS handshake does not establish its exact cause.
- System routing is opt-in. Recovery journal + watchdog are implemented; real machine crash-recovery testing is still required. External proxy edits preserve the journal for manual recovery rather than overwriting the new settings.
- Local DB history is capped at 10,000 resolved flows with cascading alerts. Privacy score is a disclosed ratio of blocked observed risks, not a guarantee of safety.
- No remote feeds are fetched automatically. The included tracker seed is not comprehensive. Review provenance/license and parser limitations before importing third-party lists.
