# Local inspection and consent

SentriFlow is for monitoring the operator's own device. All request inspection, rules and
history are local. System routing and current-user CA trust are explicit operations.
Installing the per-install CA permits HTTPS inspection by this proxy until the CA is removed.

Raw URLs, headers and bodies are used only in memory during request inspection. Public events
and SQLite flow/alert records contain host metadata, process identity, byte counts, verdicts,
labels and fully redacted match samples. Paths are redacted. Custom string/regex definitions
are retained so they can match future requests; they may themselves be sensitive. The runtime
directory and CA key directory have restricted permissions. Proxy dump files are not enabled.

The API token is random per process, kept in memory and printed in a local launch URL fragment.
REST requires that token; REST and WebSocket verify Host and Origin. The map endpoint currently
reports unavailable. No external map tiles, telemetry, model API or silent intel updates run.

`DELETE /api/flows` clears metadata and related alerts while preserving rules/patterns.
`sentriflow reset --confirm`, while stopped, clears the database. It does not revoke CA trust.
Use `remove-ca` before deleting CA files. See [Windows setup](windows-setup.md) for recovery.
