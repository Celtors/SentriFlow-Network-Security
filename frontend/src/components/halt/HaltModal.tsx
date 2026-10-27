import { useEffect, useRef, useState } from "react";
import { api } from "../../api/client";
import type { Flow, Snapshot } from "../../api/types";
import { bytes, patternLabel } from "../../lib/format";
import { useTrafficStore } from "../../store/trafficStore";
import { useHaltStore } from "../../store/haltStore";

export default function HaltModal({
  flow,
  count,
}: {
  flow: Flow;
  count: number;
}) {
  const [remember, setRemember] = useState(false),
    [remaining, setRemaining] = useState(() =>
      Math.max(0, Math.ceil((Date.parse(flow.deadline!) - Date.now()) / 1000)),
    ),
    [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const timer = setInterval(
      () =>
        setRemaining(
          Math.max(
            0,
            Math.ceil((Date.parse(flow.deadline!) - Date.now()) / 1000),
          ),
        ),
      250,
    );
    return () => clearInterval(timer);
  }, [flow.deadline]);
  async function decide(action: "allow" | "block") {
    setBusy(true);
    setError("");
    try {
      await api(`/halts/${flow.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ action, scope: remember ? "always" : "once" }),
      });
      useHaltStore.getState().remove(flow.id);
      const snapshot = await api<Snapshot>("/snapshot");
      useTrafficStore.getState().setSnapshot(snapshot);
      useHaltStore.getState().replace(snapshot.pending);
    } catch (error) {
      setError((error as Error).message);
      useTrafficStore.getState().setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="overlay">
      <div
        className="halt-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="halt-title"
        ref={panel}
        onKeyDown={(event) => {
          if (event.key !== "Tab") return;
          const controls = panel.current?.querySelectorAll<HTMLElement>(
            "button:not(:disabled), input:not(:disabled)",
          );
          if (!controls?.length) return;
          const first = controls[0],
            last = controls[controls.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }}
      >
        <div className="eyebrow accent">
          OUTBOUND TRANSFER PAUSED · {count} IN QUEUE
        </div>
        <h2 id="halt-title">This transfer needs your decision.</h2>
        <p>
          <strong>{flow.process_name}</strong> is attempting to send{" "}
          <strong>{bytes(flow.bytes_up)}</strong> to{" "}
          <strong className="break">{flow.host}</strong>.
        </p>
        <div className="findings">
          {flow.findings.map((finding, i) => (
            <div key={i}>
              <strong>{patternLabel(finding.label)}</strong>
              <small>
                {finding.location} · {finding.masked_sample}
              </small>
            </div>
          ))}
        </div>
        <p className="muted">
          {remaining
            ? `Automatically blocked in ${remaining}s if unanswered.`
            : "Deadline reached. Waiting for server confirmation…"}
        </p>
        <label className="check">
          <input
            type="checkbox"
            checked={remember}
            disabled={!flow.process_key}
            onChange={(e) => setRemember(e.target.checked)}
          />
          Remember for this process and exact host
        </label>
        {!flow.process_key && (
          <small className="muted">
            Unknown process: one-time decision only.
          </small>
        )}
        {remember && flow.tls_status !== "inspected" && (
          <p className="muted">
            This request was not fully inspected. Allow is available only as a
            one-time decision.
          </p>
        )}
        {error && (
          <p className="warning" role="alert">
            {error}
          </p>
        )}
        <div className="actions">
          <button
            className="primary"
            disabled={busy || remaining === 0}
            onClick={() => void decide("block")}
          >
            Block transfer
          </button>
          <button
            disabled={
              busy ||
              remaining === 0 ||
              (remember && flow.tls_status !== "inspected")
            }
            onClick={() => void decide("allow")}
          >
            Allow transfer
          </button>
        </div>
      </div>
    </div>
  );
}
