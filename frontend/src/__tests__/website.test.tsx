// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import WebsitePanel from "../components/WebsitePanel";
import { useTrafficStore } from "../store/trafficStore";
import type { Snapshot, Website } from "../api/types";

afterEach(() => {
  cleanup();
  useTrafficStore.getState().reset();
});

const site: Website = {
  id: "observed-site",
  host: "example.com",
  scheme: "https",
  process_name: "Browser",
  process_key: "browser",
  identified_by: "page_navigation",
  first_seen: "2026-11-15T00:00:00Z",
  updated_at: "2026-11-15T00:00:00Z",
  requests: 3,
  completed_requests: 2,
  blocked_requests: 1,
  third_party_requests: 1,
  external_domains: ["cdn.example.net"],
  redirect_domains: [],
  redirects: 0,
  bytes_up: 100,
  bytes_down: 1024,
  tls_status: "inspected",
  association_note: "Observed page, not the focused browser tab.",
  analysis: {
    state: "ready",
    maliciousness_percentage: 42.3,
    risk_level: "medium",
    reasons: ["Domain length raises the model estimate."],
    features: { host_length: 11 },
    model_id: "test-model",
  },
  evidence: {
    permissions: {
      state: "unavailable",
      detail: "Browser permission requests cannot be observed.",
    },
    forms: {
      state: "structure_observed",
      detail: "Static HTML only.",
      forms: 1,
      password_fields: 1,
      email_fields: 0,
    },
  },
};
function load(website = site) {
  useTrafficStore.getState().setSnapshot({
    websites: [website],
    current_website_id: website.id,
    website_model: { available: true },
  } as Snapshot);
  useTrafficStore.getState().setStatus("Live");
}

it("displays actual supplied inference and progressively reveals details", () => {
  load();
  const expand = vi.fn();
  render(<WebsitePanel compact onExpand={expand} onSettings={vi.fn()} />);
  expect(screen.getByTestId("website-percentage").textContent).toBe("42.3%");
  expect(screen.getByText("medium risk")).toBeTruthy();
  expect(screen.queryByText("Camera, microphone & location")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Explore details/ }));
  expect(expand).toHaveBeenCalledOnce();
});

it("separates unknown browser access from observed form structure", () => {
  load();
  render(<WebsitePanel onSettings={vi.fn()} />);
  expect(screen.getByText("Cannot observe")).toBeTruthy();
  expect(screen.getByText("Structure observed")).toBeTruthy();
  expect(
    screen.getByText("Browser permission requests cannot be observed."),
  ).toBeTruthy();
  expect(screen.getByText("cdn.example.net")).toBeTruthy();
});

it.each(["analyzing", "unavailable", "error"] as const)(
  "does not fabricate a percentage when %s",
  (state) => {
    load({
      ...site,
      analysis: {
        state,
        maliciousness_percentage: null,
        risk_level: "unknown",
        reasons: [],
        reason: "No usable evidence",
      },
    });
    render(<WebsitePanel compact onSettings={vi.fn()} />);
    expect(screen.getByTestId("website-percentage").textContent).toBe("—");
    expect(screen.getByText("No usable evidence")).toBeTruthy();
  },
);

it("updates the compact view from live store events", () => {
  load();
  render(<WebsitePanel compact onSettings={vi.fn()} />);
  const second = { ...site, id: "second", host: "second.example.net" };
  const { unmount } = render(
    <button
      onClick={() => useTrafficStore.getState().website(second, second.id)}
    >
      Apply event
    </button>,
  );
  fireEvent.click(screen.getByText("Apply event"));
  expect(screen.getByRole("heading", { name: second.host })).toBeTruthy();
  expect(useTrafficStore.getState().snapshot?.websites).toHaveLength(2);
  unmount();
});

it("keeps the followed page when background summaries exceed the history cap", () => {
  load();
  for (let i = 0; i < 55; i += 1) {
    useTrafficStore
      .getState()
      .website({ ...site, id: `background-${i}` }, site.id);
  }
  const snapshot = useTrafficStore.getState().snapshot;
  expect(snapshot?.websites).toHaveLength(50);
  expect(
    snapshot?.websites?.some((s) => s.id === snapshot.current_website_id),
  ).toBe(true);
});
