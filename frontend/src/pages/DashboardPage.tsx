import { useTrafficStore } from "../store/trafficStore";
import { useHaltQueue } from "../hooks/useHaltQueue";
import { bytes } from "../lib/format";
import SpeedChart from "../components/traffic/SpeedChart";
import TrafficPage from "./TrafficPage";

export default function DashboardPage() {
  const snapshot = useTrafficStore((state) => state.snapshot);
  const pending = useHaltQueue();
  if (!snapshot) return null;
  return (
    <>
      <div className="metrics">
        <div className="metric">
          <span>PRIVACY SCORE</span>
          <strong>
            {snapshot.score.score ?? "—"}
            <small>{snapshot.score.score === null ? "" : "/100"}</small>
          </strong>
          <small className="muted">
            {snapshot.score.risky_blocked} of {snapshot.score.risky_resolved}{" "}
            risky requests blocked
          </small>
        </div>
        <div className="metric">
          <span>CAPTURED REQUESTS</span>
          <strong>{snapshot.flows.length}</strong>
          <small className="muted">Most recent 200 requests</small>
        </div>
        <div className="metric">
          <span>BLOCKED TRANSFERS</span>
          <strong className="accent">
            {snapshot.flows.filter((f) => f.verdict === "block").length}
          </strong>
          <small className="muted">In recent history</small>
        </div>
        <div className="metric">
          <span>AWAITING DECISION</span>
          <strong className="accent">{pending.length}</strong>
          <small className="muted">No answer means Block</small>
        </div>
      </div>
      <div className="overview-grid">
        <SpeedChart />
        <section className="panel">
          <div className="panel-heading">
            <h2>Applications</h2>
            <small className="muted">This session</small>
          </div>
          {snapshot.processes.map((p, i) => (
            <div className="list-row" key={p.process_key || i}>
              <div className="app-icon">{p.process_name[0]}</div>
              <div>
                <strong>{p.process_name}</strong>
                <small>
                  {bytes(p.bytes_up)} sent · {bytes(p.bytes_down)} received
                </small>
              </div>
              <span className="app-rates">
                <span>{bytes(p.upload_bps)}/s ↑</span>
                <span>{bytes(p.download_bps)}/s ↓</span>
              </span>
            </div>
          ))}
          {!snapshot.processes.length && (
            <div className="empty">No approved payload traffic yet.</div>
          )}
        </section>
      </div>
      <p className="score-note">
        {snapshot.score.formula}. This describes observed decisions over
        retained history, not total device safety.
      </p>
      <details className="score-breakdown">
        <summary>How this score is calculated</summary>
        <p>
          {snapshot.score.risky_blocked} risky requests blocked /{" "}
          {snapshot.score.risky_resolved} risky requests resolved. Risky
          requests include PII patterns, trackers, incomplete inspection and
          unusual upload size. Only retained observed requests count; traffic
          bypassing the proxy is outside this score.
        </p>
      </details>
      <TrafficPage compact />
    </>
  );
}
