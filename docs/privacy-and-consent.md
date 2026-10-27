# Privacy and consent

SentriFlow is intended for the owner's authorized device and test clients. Inspection is local. Use dummy data for demonstrations and tests; do not capture another person's traffic without authorization.

Two device changes are explicit user actions: enabling Windows browser proxy routing and trusting the generated local CA. The dashboard explains both, and CA installation requires a consent checkbox. CLI installation requires `install-ca --confirm`. Automated verification did not perform these changes.

The database retains redacted labels and metadata, not full URLs, raw headers, bodies or matched personal values. Hosts/process names and timing can still reveal activity; keep local data private. Sensitive custom strings live in session memory and disappear on restart. No cloud inference, analytics, external fonts, map tiles or automatic feed refresh is used.

The offline map also stores the observed destination IP (or a literal IP requested by the client) and an optional country estimate inside the existing flow metadata. These are activity metadata and can be sensitive. The map reads a local MMDB and bundled country shapes without sending captured IPs to an external service or making additional DNS queries. A small explicit example.com request was used only in the optional public-map acceptance check; application runtime performs no such test automatically.

Restore routing from Settings or `restore-proxy` when finished. Remove CA trust with `remove-ca` before deleting CA files. The watchdog attempts recovery after process death; external proxy changes are preserved for manual review. There is no claim of legal certification or complete traffic coverage.
