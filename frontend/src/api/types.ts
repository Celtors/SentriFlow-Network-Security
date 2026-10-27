// Mirrors backend/src/sentriflow/core/models.py and api/schemas.py.
export type Verdict = 'allow' | 'block' | 'halt'
export type Action = 'allow' | 'block'
export type Scope = 'once' | 'always'

export interface Finding {
  type: string
  label: string
  severity: string
  masked_sample: string
  location: string
}

export interface Flow {
  id: string
  ts: string
  pid: number | null
  process_name: string
  exe_path: string | null
  method: string
  scheme: string
  host: string
  port: number
  path_masked: string
  bytes_up: number
  bytes_down: number
  tls_status: 'inspected' | 'pinned' | 'passthrough'
  verdict: Verdict
  verdict_source: string
  matched_rule_id: string | null
  country_code: string | null
  findings: Finding[]
}

export interface Halt {
  id: string
  flow: Flow
  deadline: string
}

export interface Rule {
  id: string
  created_at: string
  process_match: string | null
  host_match: string | null
  action: Action
  note: string
}

export interface Alert {
  id: string
  flow_id: string
  ts: string
  type: string
  severity: string
  pattern_label: string
  masked_sample: string
}

export interface Score {
  score: number
  breakdown: Record<string, number>
  weights: Record<string, number>
  formula: string
}

export interface SpeedTick {
  interval_seconds: number
  processes: {
    process_name: string
    bytes_up: number
    bytes_down: number
    upload_bps: number
    download_bps: number
  }[]
}

export interface SystemStatus {
  proxy_running?: boolean
  system_proxy_enabled?: boolean
  pending_halts?: Halt[]
  message?: string
  tls_status?: string
}

export interface EventData {
  'flow.started': Flow
  'flow.completed': Flow
  'halt.requested': Halt
  'halt.resolved': { id: string; action: Action; source: string; rule_id: string | null }
  'alert.created': Alert
  'score.updated': Score
  'speed.tick': SpeedTick
  'system.status': SystemStatus
}

export type ServerEvent = {
  [K in keyof EventData]: { type: K; ts: string; data: EventData[K] }
}[keyof EventData]

export interface HaltCommand {
  type: 'halt.decide'
  data: { id: string; action: Action; scope: Scope }
}
