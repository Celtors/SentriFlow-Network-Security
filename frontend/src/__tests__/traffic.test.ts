import { beforeEach, expect, it } from "vitest";
import { useTrafficStore } from "../store/trafficStore";
import { useHaltStore } from "../store/haltStore";
import type { Flow, Snapshot } from "../api/types";

beforeEach(() => {
  useTrafficStore.getState().reset();
  useHaltStore.getState().replace([]);
});

const flow: Flow = {
  id: "f1",
  ts: "2026-10-27T00:00:00Z",
  updated_at: "2026-10-27T00:00:00Z",
  pid: null,
  process_name: "Unknown",
  process_key: null,
  method: "POST",
  scheme: "https",
  host: "example.test",
  port: 443,
  bytes_up: 100,
  bytes_down: 0,
  tls_status: "inspected",
  verdict: "halt",
  verdict_source: "inspection",
  state: "held",
  reason: "PII",
  findings: [],
  deadline: null,
  status_code: null,
};
export const fixture: Snapshot = {
  flows: [],
  pending: [],
  rules: [],
  patterns: [],
  alerts: [],
  settings: {
    inspection_enabled: true,
    halt_timeout_seconds: 30,
    unknown_large_bytes: 1000000,
    tracker_mode: "halt",
  },
  score: { score: null, risky_resolved: 0, risky_blocked: 0, formula: "ratio" },
  blocklist: [],
  system: {
    proxy_running: true,
    proxy_address: "127.0.0.1:8080",
    capture_scope: "explicit",
    system_proxy: { available: true, enabled: false, recovery_pending: false },
    ca: {
      generated: false,
      public_certificate: "",
      thumbprint: null,
      trust_status: "not_checked",
    },
  },
  processes: [],
};

it("updates a held flow without duplicating its history entry", () => {
  useTrafficStore.getState().setSnapshot(fixture);
  useTrafficStore.getState().upsert(flow);
  useTrafficStore
    .getState()
    .upsert({ ...flow, state: "completed", verdict: "block" });
  expect(useTrafficStore.getState().snapshot?.flows).toHaveLength(1);
  expect(useTrafficStore.getState().snapshot?.flows[0].verdict).toBe("block");
});
it("consumes measured speed ticks and clears rates at idle", () => {
  useTrafficStore
    .getState()
    .speed(
      { upload_bps: 0, download_bps: 4096, elapsed: 1, processes: [] },
      flow.ts,
    );
  useTrafficStore
    .getState()
    .speed(
      { upload_bps: 0, download_bps: 0, elapsed: 1, processes: [] },
      flow.ts,
    );
  expect(useTrafficStore.getState().rates.map((r) => r.download)).toEqual([
    4096, 0,
  ]);
});
it("tracks concurrent holds independently and clears the resolved request", () => {
  useHaltStore.getState().add(flow);
  useHaltStore.getState().add({ ...flow, id: "f2" });
  useHaltStore.getState().remove("f1");
  expect(useHaltStore.getState().pending.map((f) => f.id)).toEqual(["f2"]);
});
