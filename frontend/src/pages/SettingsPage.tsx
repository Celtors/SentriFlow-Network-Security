import { useState } from "react";
import { api } from "../api/client";
import type { Settings, Snapshot } from "../api/types";
import { useTrafficStore } from "../store/trafficStore";

export default function SettingsPage() {
  const snapshot = useTrafficStore((state) => state.snapshot);
  const [draft, setDraft] = useState<Settings | null>(null),
    [busy, setBusy] = useState(false),
    [consent, setConsent] = useState(false);
  if (!snapshot) return null;
  const settings = draft || snapshot.settings,
    system = snapshot.system;
  async function act(path: string, method: string, body?: object) {
    setBusy(true);
    try {
      await api(path, {
        method,
        body: body ? JSON.stringify(body) : undefined,
      });
      useTrafficStore.getState().setSnapshot(await api<Snapshot>("/snapshot"));
    } catch (error) {
      useTrafficStore.getState().setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <section className="panel settings">
        <h2>Inspection controls</h2>
        <p className="muted caption">
          Changes affect new requests. Existing Halt deadlines remain unchanged.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void act("/settings", "PUT", settings);
          }}
        >
          <label className="check">
            <input
              type="checkbox"
              checked={settings.inspection_enabled}
              onChange={(e) =>
                setDraft({ ...settings, inspection_enabled: e.target.checked })
              }
            />
            Inspect request URL, headers and supported text bodies
          </label>
          <label>
            Halt timeout (seconds)
            <input
              type="number"
              min={2}
              max={120}
              required
              value={settings.halt_timeout_seconds}
              onChange={(e) =>
                setDraft({
                  ...settings,
                  halt_timeout_seconds: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Unknown process upload threshold (bytes)
            <input
              type="number"
              min={1024}
              max={8000000}
              required
              value={settings.large_upload_bytes}
              onChange={(e) =>
                setDraft({
                  ...settings,
                  large_upload_bytes: Number(e.target.value),
                })
              }
            />
          </label>
          <label>
            Tracker action
            <select
              aria-label="Tracker action"
              value={settings.tracker_policy}
              onChange={(e) =>
                setDraft({
                  ...settings,
                  tracker_policy: e.target.value as Settings["tracker_policy"],
                })
              }
            >
              <option value="ask">Ask me; default Block</option>
              <option value="block">Automatically block</option>
              <option value="alert">Alert only</option>
            </select>
          </label>
          <button className="primary" disabled={busy}>
            Save settings
          </button>
        </form>
      </section>
      <section className="panel settings">
        <h2>Browser routing</h2>
        <p className="muted caption">
          SentriFlow captures clients routed to {system.proxy_address}. Enabling
          this changes the current user's Windows proxy. It is restored on
          normal stop; after a forced crash, run restore-proxy. Applications
          that ignore this proxy remain outside capture.
        </p>
        <div className="list-row">
          <div>
            <strong>
              {system.system_proxy.enabled
                ? "Windows proxy enabled"
                : "Windows proxy disabled"}
            </strong>
            <small>
              {system.system_proxy.server || "No server configured"}
            </small>
          </div>
          <button
            disabled={
              busy ||
              !system.system_proxy.available ||
              !system.proxy_running ||
              system.system_proxy.recovery_pending
            }
            onClick={() => void act("/system/proxy", "POST", { enabled: true })}
          >
            Enable browser routing
          </button>
          <button
            disabled={busy || !system.system_proxy.recovery_pending}
            onClick={() =>
              void act("/system/proxy", "POST", { enabled: false })
            }
          >
            Restore proxy
          </button>
        </div>
      </section>
      <section className="panel settings">
        <h2>HTTPS certificate consent</h2>
        <p className="muted caption">
          Trusting the local CA lets SentriFlow decrypt HTTPS in compatible
          clients on this device. Install only when you choose to inspect HTTPS;
          remove trust when finished. Certificate pinning may prevent
          inspection. Trust status is not automatically checked.
        </p>
        <p className="muted break">
          {system.ca.generated
            ? `Generated public certificate: ${system.ca.public_certificate}`
            : "Start the interception proxy to generate a local CA."}
        </p>
        <label className="check">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
          />
          I consent to installing this local CA in my Windows user trust store.
        </label>
        <div className="actions">
          <button
            className="primary"
            disabled={busy || !consent || !system.ca.generated}
            onClick={() => void act("/system/ca", "POST", { confirmed: true })}
          >
            Install local CA
          </button>
          <button
            disabled={busy || !system.ca.generated}
            onClick={() => void act("/system/ca", "DELETE")}
          >
            Remove local CA trust
          </button>
        </div>
      </section>
    </>
  );
}
