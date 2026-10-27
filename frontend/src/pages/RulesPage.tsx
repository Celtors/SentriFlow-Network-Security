import { useState } from "react";
import { api } from "../api/client";
import { useTrafficStore } from "../store/trafficStore";
import type { Snapshot } from "../api/types";

export default function RulesPage() {
  const snapshot = useTrafficStore((state) => state.snapshot);
  const [busy, setBusy] = useState(false),
    [label, setLabel] = useState(""),
    [pattern, setPattern] = useState("");
  async function act(path: string, method: string, body?: object) {
    setBusy(true);
    try {
      await api(path, {
        method,
        body: body ? JSON.stringify(body) : undefined,
      });
      useTrafficStore.getState().setSnapshot(await api<Snapshot>("/snapshot"));
      setPattern("");
    } catch (error) {
      useTrafficStore.getState().setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel">
        <h2>Remembered decisions</h2>
        <p className="muted caption">
          Matches an executable identity and exact destination host. A saved
          Allow may authorize future detected PII for that combination.
        </p>
        {snapshot?.rules.map((rule) => (
          <div className="list-row" key={rule.id}>
            <div>
              <strong>{rule.process_name}</strong>
              <small>{rule.host_match}</small>
            </div>
            <select
              aria-label={`Action for ${rule.host_match}`}
              disabled={busy}
              value={rule.action}
              onChange={(e) => {
                const { process_match, process_name, host_match, note } = rule;
                void act("/rules", "POST", {
                  process_match,
                  process_name,
                  host_match,
                  note,
                  action: e.target.value,
                });
              }}
            >
              <option value="allow">Allow</option>
              <option value="block">Block</option>
            </select>
            <button
              disabled={busy}
              onClick={() => void act(`/rules/${rule.id}`, "DELETE")}
            >
              Delete
            </button>
          </div>
        ))}
        {!snapshot?.rules.length && (
          <div className="empty">
            No saved rules. Remember a Halt decision to create one.
          </div>
        )}
      </section>
      <section className="panel">
        <h2>Sensitive strings</h2>
        <p className="muted caption">
          Literal matching, up to 20 strings. Values stay in memory only and are
          cleared when SentriFlow stops.
        </p>
        <form
          className="pattern-form"
          onSubmit={(e) => {
            e.preventDefault();
            void act("/patterns", "POST", {
              label,
              pattern,
              is_regex: false,
              enabled: true,
            });
          }}
        >
          <label>
            Pattern label
            <input
              required
              pattern="[a-zA-Z0-9 _-]+"
              maxLength={64}
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="Project secret"
            />
          </label>
          <label>
            Sensitive string
            <input
              type="password"
              autoComplete="off"
              required
              maxLength={256}
              value={pattern}
              onChange={(e) => setPattern(e.target.value)}
            />
          </label>
          <button className="primary" disabled={busy}>
            Add string
          </button>
        </form>
        {snapshot?.patterns.map((p) => (
          <div className="list-row" key={p.id}>
            <div>
              <strong>{p.label}</strong>
              <small>[redacted] · session only</small>
            </div>
            <button
              disabled={busy}
              onClick={() => void act(`/patterns/${p.id}`, "DELETE")}
            >
              Delete
            </button>
          </div>
        ))}
      </section>
    </>
  );
}
