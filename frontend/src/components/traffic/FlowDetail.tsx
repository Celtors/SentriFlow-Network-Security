import { useEffect, useRef } from "react";
import type { Flow } from "../../api/types";
import { bytes, patternLabel, time } from "../../lib/format";

export default function FlowDetail({
  flow,
  close,
}: {
  flow: Flow;
  close: () => void;
}) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => previous?.focus();
  }, []);
  return (
    <div className="overlay">
      <div
        className="halt-card flow-detail"
        role="dialog"
        aria-modal="true"
        aria-labelledby="flow-detail-title"
        ref={panel}
        onKeyDown={(event) => {
          if (event.key === "Escape") close();
          if (event.key === "Tab") {
            event.preventDefault();
            panel.current?.querySelector("button")?.focus();
          }
        }}
      >
        <div className="panel-heading">
          <h2 id="flow-detail-title">Request details</h2>
          <button onClick={close} aria-label="Close request details">
            Close
          </button>
        </div>
        <p className="break">
          <strong>{flow.process_name}</strong> → {flow.host}
        </p>
        <dl className="detail-grid">
          <dt>Decision</dt>
          <dd>
            {flow.verdict} · {flow.verdict_source}
          </dd>
          <dt>State</dt>
          <dd>{flow.state}</dd>
          <dt>Reason</dt>
          <dd>{flow.reason}</dd>
          <dt>Destination</dt>
          <dd className="break">
            {flow.scheme}://{flow.host}:{flow.port}
          </dd>
          <dt>Observed IP</dt>
          <dd>{flow.destination_ip || "Not observed"}</dd>
          <dt>Country estimate</dt>
          <dd>{flow.country_code || "Not mapped"}</dd>
          <dt>Process ID</dt>
          <dd>{flow.pid ?? "Unknown"}</dd>
          <dt>Request body</dt>
          <dd>{bytes(flow.bytes_up)}</dd>
          <dt>Received body</dt>
          <dd>{bytes(flow.bytes_down)}</dd>
          <dt>HTTP response</dt>
          <dd>{flow.status_code ?? "Not received"}</dd>
          <dt>Inspection</dt>
          <dd>{patternLabel(flow.tls_status)}</dd>
          <dt>Captured at</dt>
          <dd>{time(flow.ts)}</dd>
        </dl>
        <h3>Inspection findings</h3>
        <div className="findings">
          {flow.findings.length ? (
            flow.findings.map((finding, index) => (
              <div key={index}>
                <strong>{patternLabel(finding.label)}</strong>
                <small>
                  {finding.location} · {finding.masked_sample}
                </small>
              </div>
            ))
          ) : (
            <p className="muted">No pattern findings recorded.</p>
          )}
        </div>
        <p className="muted">
          URL paths, queries, headers, and raw request bodies are omitted from
          history. A permitted request can still fail before reaching its
          destination.
        </p>
      </div>
    </div>
  );
}
