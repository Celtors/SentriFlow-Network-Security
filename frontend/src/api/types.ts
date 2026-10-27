export type Verdict = "allow" | "block" | "halt";
export interface Finding {
  label: string;
  type: string;
  location: string;
  masked_sample: string;
}
export interface Flow {
  id: string;
  ts: string;
  updated_at: string;
  pid: number | null;
  process_name: string;
  process_key: string | null;
  method: string;
  scheme: string;
  host: string;
  port: number;
  bytes_up: number;
  bytes_down: number;
  tls_status: string;
  verdict: Verdict;
  verdict_source: string;
  state: "started" | "held" | "completed" | "error";
  reason: string;
  findings: Finding[];
  deadline: string | null;
  status_code: number | null;
  destination_ip?: string | null;
  country_code?: string | null;
}
export interface Rule {
  id: string;
  process_match: string | null;
  process_name: string | null;
  host_match: string | null;
  action: "allow" | "block";
  note: string;
}
export interface Pattern {
  id: string;
  label: string;
  enabled: boolean;
  is_regex: boolean;
}
export interface Alert {
  id: string;
  flow_id: string;
  ts: string;
  type: string;
  severity: string;
  pattern_label: string;
  masked_sample: string;
  host: string;
  process_name: string;
}
export interface Settings {
  inspection_enabled: boolean;
  halt_timeout_seconds: number;
  large_upload_bytes: number;
  tracker_policy: "ask" | "block" | "alert";
}
export interface ProcessStats {
  process_key: string | null;
  process_name: string;
  bytes_up: number;
  bytes_down: number;
  upload_bps: number;
  download_bps: number;
}
export interface SystemStatus {
  proxy_running: boolean;
  proxy_address: string;
  capture_scope: string;
  system_proxy: {
    available: boolean;
    enabled?: boolean;
    server?: string | null;
    recovery_pending: boolean;
  };
  ca: {
    generated: boolean;
    public_certificate: string;
    thumbprint: string | null;
    trust_status: string;
  };
}
export interface Snapshot {
  flows: Flow[];
  pending: Flow[];
  rules: Rule[];
  patterns: Pattern[];
  alerts: Alert[];
  settings: Settings;
  score: {
    score: number | null;
    risky_resolved: number;
    risky_blocked: number;
    formula: string;
    breakdown?: Record<string, number>;
    weights?: Record<string, number>;
  };
  blocklist: { source: string; count: number }[];
  system: SystemStatus;
  processes: ProcessStats[];
}
export interface SpeedTick {
  upload_bps: number;
  download_bps: number;
  processes: ProcessStats[];
  elapsed: number;
}
export interface Event {
  type: string;
  ts: string;
  data: unknown;
}
export interface Rate {
  time: string;
  upload: number;
  download: number;
}

export interface GeoCountry {
  country_code: string;
  country_name: string;
  requests: number;
  blocked: number;
  bytes_up: number;
  bytes_down: number;
}
export interface GeoDestinations {
  available: boolean;
  reason: string;
  database: string;
  build_epoch: number | null;
  destinations: GeoCountry[];
  total_requests: number;
  unknown: {
    no_observed_ip: number;
    local_or_private_ip: number;
    not_in_database: number;
  };
}
