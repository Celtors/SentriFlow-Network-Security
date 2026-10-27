import { useState } from "react";
import { useTrafficStore } from "../store/trafficStore";
import { bytes, patternLabel, time } from "../lib/format";
import FlowDetail from "../components/traffic/FlowDetail";

export default function TrafficPage({
  compact = false,
}: {
  compact?: boolean;
}) {
  const flows = useTrafficStore((state) => state.snapshot?.flows || []);
  const [query, setQuery] = useState(""),
    [verdict, setVerdict] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const selectedFlow = flows.find((flow) => flow.id === selected);
  const filtered = flows.filter(
    (flow) =>
      `${flow.host} ${flow.process_name} ${flow.method} ${flow.reason} ${flow.findings.map((f) => f.label).join(" ")}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (verdict === "all" || flow.verdict === verdict),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>{compact ? "Recent traffic" : "Captured traffic"}</h2>
        <small className="muted">{filtered.length} requests</small>
      </div>
      <div className="filters">
        <input
          aria-label="Search traffic"
          placeholder="Search application or destination…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          aria-label="Verdict filter"
          value={verdict}
          onChange={(e) => setVerdict(e.target.value)}
        >
          <option value="all">All verdicts</option>
          <option value="allow">Allowed</option>
          <option value="block">Blocked</option>
          <option value="halt">Held</option>
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>APPLICATION</th>
              <th>DESTINATION</th>
              <th>PAYLOAD</th>
              <th>VERDICT</th>
              <th>TIME</th>
            </tr>
          </thead>
          <tbody>
            {filtered.slice(0, compact ? 8 : 200).map((flow) => (
              <tr key={flow.id}>
                <td>
                  <strong>{flow.process_name}</strong>
                  <small>
                    {flow.pid ? `PID ${flow.pid}` : "Attribution unavailable"}
                  </small>
                </td>
                <td>
                  <button
                    className="destination-button"
                    aria-label={`View request to ${flow.host}`}
                    onClick={() => setSelected(flow.id)}
                  >
                    {flow.host}
                  </button>
                  <small>
                    {flow.method} · {flow.tls_status.replaceAll("_", " ")}
                    <br />
                    {flow.findings
                      .map((f) => patternLabel(f.label))
                      .join(", ") || flow.reason}
                  </small>
                </td>
                <td>
                  {bytes(flow.bytes_up)} ↑
                  <small>{bytes(flow.bytes_down)} ↓</small>
                </td>
                <td>
                  <span className={`badge verdict-${flow.verdict}`}>
                    {flow.state === "error" ? "error" : flow.verdict}
                  </span>
                </td>
                <td className="muted">{time(flow.ts)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!filtered.length && (
        <div className="empty">
          <strong>No captured traffic yet</strong>
          <p>
            Connect a test client to proxy 127.0.0.1:8080. Opening the dashboard
            does not configure your browser.
          </p>
        </div>
      )}
      {selectedFlow && (
        <FlowDetail flow={selectedFlow} close={() => setSelected(null)} />
      )}
    </section>
  );
}
