import { useTrafficStore } from "../store/trafficStore";
import { patternLabel, time } from "../lib/format";
import { useState } from "react";
import FlowDetail from "../components/traffic/FlowDetail";

export default function AlertsPage() {
  const alerts = useTrafficStore((state) => state.snapshot?.alerts || []);
  const flows = useTrafficStore((state) => state.snapshot?.flows || []);
  const [severity, setSeverity] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const filtered = alerts.filter(
    (alert) => severity === "all" || alert.severity === severity,
  );
  const flow = flows.find((item) => item.id === selected);
  return (
    <section className="panel">
      <h2>Privacy alerts</h2>
      <p className="muted caption">
        Only labels and redacted samples are stored.
      </p>
      <div className="filters">
        <select
          aria-label="Alert severity"
          value={severity}
          onChange={(event) => setSeverity(event.target.value)}
        >
          <option value="all">All severities</option>
          <option value="high">High priority</option>
          <option value="medium">Medium priority</option>
          <option value="low">Low priority</option>
        </select>
      </div>
      {filtered.map((alert) => (
        <div className="list-row" key={alert.id}>
          <span className="alert-icon">!</span>
          <div>
            <strong>{patternLabel(alert.pattern_label)}</strong>
            <small>
              {alert.process_name} → {alert.host} · {time(alert.ts)}
            </small>
          </div>
          <span className="muted">{alert.masked_sample}</span>
          <span className={`severity severity-${alert.severity}`}>
            {alert.severity}
          </span>
          {flows.some((item) => item.id === alert.flow_id) && (
            <button onClick={() => setSelected(alert.flow_id)}>
              View request
            </button>
          )}
        </div>
      ))}
      {!filtered.length && (
        <div className="empty">
          {alerts.length
            ? "No alerts match this severity."
            : "No alerts recorded."}
        </div>
      )}
      {flow && <FlowDetail flow={flow} close={() => setSelected(null)} />}
    </section>
  );
}
