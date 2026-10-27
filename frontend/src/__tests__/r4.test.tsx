// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import TrafficPage from "../pages/TrafficPage";
import AlertsPage from "../pages/AlertsPage";
import MapPage from "../pages/MapPage";
import HaltModal from "../components/halt/HaltModal";
import { useTrafficStore } from "../store/trafficStore";
import { api } from "../api/client";
import type { Flow, Snapshot } from "../api/types";

vi.mock("../api/client", () => ({ api: vi.fn() }));
vi.mock("../components/map/DestinationMap", () => ({
  default: () => <div>Local country vectors</div>,
}));
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  useTrafficStore.getState().reset();
});

const flow: Flow = {
  id: "test",
  ts: "2026-10-27T00:00:00Z",
  updated_at: "",
  pid: 1,
  process_name: "demo.exe",
  process_key: "a".repeat(64),
  method: "POST",
  scheme: "https",
  host: "example.test",
  port: 443,
  bytes_up: 83,
  bytes_down: 0,
  tls_status: "not_inspected",
  verdict: "block",
  verdict_source: "user",
  state: "completed",
  reason: "User blocked transfer",
  findings: [
    {
      label: "email",
      type: "pii",
      location: "body",
      masked_sample: "[redacted]",
    },
  ],
  deadline: new Date(Date.now() + 30000).toISOString(),
  status_code: 403,
};
const snapshot = {
  flows: [flow],
  alerts: [
    {
      id: "alert",
      flow_id: "test",
      ts: flow.ts,
      type: "pii",
      severity: "high",
      pattern_label: "email",
      masked_sample: "[redacted]",
      host: "example.test",
      process_name: "demo.exe",
    },
  ],
} as Snapshot;

it("opens a redacted flow detail and filters traffic by the recorded reason", () => {
  useTrafficStore.getState().setSnapshot(snapshot);
  render(<TrafficPage />);
  fireEvent.change(screen.getByLabelText("Search traffic"), {
    target: { value: "User blocked" },
  });
  fireEvent.click(
    screen.getByRole("button", { name: "View request to example.test" }),
  );
  expect(screen.getByRole("dialog")).toBeTruthy();
  expect(
    screen.getByText(
      "URL paths, queries, headers, and raw request bodies are omitted from history.",
      { exact: false },
    ),
  ).toBeTruthy();
  fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("filters alerts by severity without discarding high-priority evidence", () => {
  useTrafficStore.getState().setSnapshot(snapshot);
  render(<AlertsPage />);
  expect(screen.getByText("high", { exact: true })).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Alert severity"), {
    target: { value: "medium" },
  });
  expect(screen.getByText("No alerts match this severity.")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Alert severity"), {
    target: { value: "high" },
  });
  expect(screen.getByRole("button", { name: "View request" })).toBeTruthy();
});

it("shows offline country results and accounts for unplotted requests", async () => {
  vi.mocked(api).mockResolvedValue({
    available: true,
    destinations: [
      {
        country_code: "US",
        country_name: "United States",
        requests: 2,
        blocked: 1,
        bytes_up: 83,
        bytes_down: 0,
      },
    ],
    total_requests: 3,
    unknown: { no_observed_ip: 0, local_or_private_ip: 1, not_in_database: 0 },
  });
  render(<MapPage />);
  expect(await screen.findByText("United States (US)")).toBeTruthy();
  expect(api).toHaveBeenCalledWith("/geo/destinations");
  expect(screen.getByText("IP Geolocation by DB-IP")).toBeTruthy();
  expect(
    screen.getByText("Not plotted:", { exact: false }).textContent,
  ).toContain("1 local/private");
});

it("keeps a failed decision visible inside the Halt prompt and prevents remembered uninspected Allow", async () => {
  vi.mocked(api).mockRejectedValue(new Error("Decision deadline has passed"));
  render(<HaltModal flow={flow} count={1} />);
  fireEvent.click(screen.getByRole("checkbox"));
  expect(
    (
      screen.getByRole("button", {
        name: "Allow transfer",
      }) as HTMLButtonElement
    ).disabled,
  ).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Block transfer" }));
  await waitFor(() =>
    expect(screen.getByRole("alert").textContent).toContain(
      "Decision deadline has passed",
    ),
  );
});
