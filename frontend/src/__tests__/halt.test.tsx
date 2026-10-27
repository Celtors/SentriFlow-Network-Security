// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import HaltModal from "../components/halt/HaltModal";
import { api } from "../api/client";

vi.mock("../api/client", () => ({
  api: vi.fn().mockResolvedValue({ pending: [], flows: [] }),
}));

it("allows only a once decision for unknown processes and sends Block to the API", async () => {
  const { unmount } = render(
    <HaltModal
      count={1}
      flow={{
        id: "held",
        ts: "",
        updated_at: "",
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
        findings: [
          {
            label: "email",
            location: "body",
            type: "pii",
            masked_sample: "[redacted]",
          },
        ],
        deadline: new Date(Date.now() + 30000).toISOString(),
        status_code: null,
      }}
    />,
  );
  expect((screen.getByRole("checkbox") as HTMLInputElement).disabled).toBe(
    true,
  );
  expect(screen.getByText("[redacted]", { exact: false })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Block transfer" }));
  await waitFor(() =>
    expect(api).toHaveBeenCalledWith("/halts/held/decision", {
      method: "POST",
      body: JSON.stringify({ action: "block", scope: "once" }),
    }),
  );
  unmount();
});
