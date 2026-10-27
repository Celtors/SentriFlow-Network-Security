CREATE TABLE IF NOT EXISTS flows (
    id TEXT PRIMARY KEY, ts TEXT NOT NULL, pid INTEGER, process_name TEXT NOT NULL,
    exe_path TEXT, method TEXT NOT NULL, scheme TEXT NOT NULL, host TEXT NOT NULL,
    port INTEGER NOT NULL, path_masked TEXT NOT NULL, bytes_up INTEGER NOT NULL,
    bytes_down INTEGER NOT NULL, tls_status TEXT NOT NULL, verdict TEXT NOT NULL,
    verdict_source TEXT NOT NULL, matched_rule_id TEXT, country_code TEXT,
    findings_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS flows_ts ON flows(ts);
CREATE INDEX IF NOT EXISTS flows_process ON flows(process_name);
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY, created_at TEXT NOT NULL, process_match TEXT, host_match TEXT,
    action TEXT NOT NULL CHECK(action IN ('allow','block')), note TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY, flow_id TEXT NOT NULL REFERENCES flows(id) ON DELETE CASCADE,
    ts TEXT NOT NULL, type TEXT NOT NULL, severity TEXT NOT NULL,
    pattern_label TEXT NOT NULL, masked_sample TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS alerts_ts ON alerts(ts);
CREATE TABLE IF NOT EXISTS blocklist_domains (
    domain TEXT PRIMARY KEY, source TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS custom_patterns (
    id TEXT PRIMARY KEY, label TEXT NOT NULL, pattern TEXT NOT NULL,
    is_regex INTEGER NOT NULL, enabled INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS score_events (
    id TEXT PRIMARY KEY, ts TEXT NOT NULL, delta INTEGER NOT NULL, reason TEXT NOT NULL,
    flow_id TEXT REFERENCES flows(id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS process_baseline (
    process_name TEXT PRIMARY KEY, hosts_seen TEXT NOT NULL,
    avg_bytes_up REAL NOT NULL, first_seen TEXT NOT NULL
);
