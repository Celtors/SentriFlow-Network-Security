import { useState } from "react";
import { sessionToken } from "./api/client";
import { useLiveTraffic } from "./hooks/useLiveTraffic";
import { useHaltQueue } from "./hooks/useHaltQueue";
import { useTrafficStore } from "./store/trafficStore";
import { useHaltStore } from "./store/haltStore";
import DashboardPage from "./pages/DashboardPage";
import TrafficPage from "./pages/TrafficPage";
import RulesPage from "./pages/RulesPage";
import AlertsPage from "./pages/AlertsPage";
import SettingsPage from "./pages/SettingsPage";
import BlocklistPage from "./pages/BlocklistPage";
import MapPage from "./pages/MapPage";
import HaltModal from "./components/halt/HaltModal";
import "./App.css";

const tabs = [
  "Overview",
  "Traffic",
  "Rules",
  "Alerts",
  "Blocklists",
  "Map",
  "Settings",
] as const;
type Tab = (typeof tabs)[number];
export default function App() {
  const [token, setToken] = useState(sessionToken),
    [draft, setDraft] = useState(""),
    [tab, setTab] = useState<Tab>("Overview");
  const { snapshot, status, error } = useTrafficStore();
  const pending = useHaltQueue();
  useLiveTraffic(token);
  function logout() {
    sessionStorage.removeItem("sentriflow-token");
    setToken("");
    useTrafficStore.getState().reset();
    useHaltStore.getState().replace([]);
  }
  if (!token)
    return (
      <main className="login">
        <section className="login-card">
          <span className="brand-mark">S</span>
          <div className="eyebrow">LOCAL NETWORK PRIVACY GUARDIAN</div>
          <h1>
            Your traffic.
            <br />
            Your decision.
          </h1>
          <p className="muted">
            Connect to the guardian on this device using the session token
            printed in your terminal.
          </p>
          <form
            onSubmit={(event) => {
              event.preventDefault();
              sessionStorage.setItem("sentriflow-token", draft.trim());
              setToken(draft.trim());
              setDraft("");
            }}
          >
            <label htmlFor="session-token">Session token</label>
            <input
              id="session-token"
              type="password"
              required
              autoComplete="off"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Paste terminal token"
            />
            <button className="primary">Open dashboard</button>
          </form>
          <small className="muted">
            Run <code>python -m sentriflow run</code> first.
          </small>
        </section>
      </main>
    );
  const pages: Record<Tab, React.ReactNode> = {
    Overview: <DashboardPage />,
    Traffic: <TrafficPage />,
    Rules: <RulesPage />,
    Alerts: <AlertsPage />,
    Blocklists: <BlocklistPage />,
    Map: <MapPage />,
    Settings: <SettingsPage />,
  };
  const routed =
    snapshot?.system.system_proxy.enabled &&
    snapshot.system.system_proxy.server === snapshot.system.proxy_address;
  return (
    <div className="shell">
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("Overview");
          }}
        >
          <span className="brand-mark">S</span>SentriFlow<small>MVP</small>
        </a>
        <div className="eyebrow nav-label">WORKSPACE</div>
        <nav>
          {tabs.map((name, i) => (
            <button
              key={name}
              className={tab === name ? "nav-item selected" : "nav-item"}
              onClick={() => setTab(name)}
            >
              <span aria-hidden="true">
                {["O", "~", "=", "!", "#", "@", "*"][i]}
              </span>
              {name}
            </button>
          ))}
        </nav>
        <div className="local-card">
          <strong>
            <span className="dot" /> Local by design
          </strong>
          <p>Inspection and redacted history stay on your device.</p>
          <small>127.0.0.1 - HTTP / HTTPS</small>
        </div>
        <button className="text-button" onClick={logout}>
          Disconnect session
        </button>
      </aside>
      <div className="workspace">
        <header>
          <span className="muted">Workspace / {tab}</span>
          <span className={status === "Live" ? "accent" : "muted"}>
            <span className="dot" />{" "}
            {status === "Live" ? "Guardian connected" : status}
          </span>
        </header>
        <main className="content">
          <div className="page-heading">
            <div>
              <div className="eyebrow">YOUR DEVICE, IN FOCUS</div>
              <h1>{tab === "Overview" ? "Privacy overview" : tab}</h1>
              <p className="muted">
                Understand what leaves your device. Decide what gets through.
              </p>
            </div>
            <button
              onClick={() => {
                if (typeof Notification !== "undefined")
                  void Notification.requestPermission();
              }}
            >
              Enable notifications
            </button>
          </div>
          {error && (
            <div role="alert" className="warning">
              {error}
              <button onClick={() => useTrafficStore.getState().setError("")}>
                Dismiss
              </button>
            </div>
          )}
          {status !== "Live" && (
            <div className="warning">
              Live connection unavailable. Displayed history may be stale.
              Unanswered holds default to Block.
              <button onClick={logout}>Reconnect</button>
            </div>
          )}
          {snapshot && !routed && (
            <div className="capture-note">
              <strong>Browser routing is not pointing to SentriFlow.</strong>
              <p>
                Only explicitly configured clients appear here. To capture
                browser HTTPS, review routing and local CA consent in Settings.
              </p>
              <button onClick={() => setTab("Settings")}>
                Review capture settings
              </button>
            </div>
          )}
          {snapshot ? (
            pages[tab]
          ) : (
            <div className="panel empty">Waiting for the local guardian...</div>
          )}
          <footer>
            <span>
              <span className="dot" /> All processing on this device
            </span>
            <span>Senklok - SentriFlow v0.1</span>
          </footer>
        </main>
      </div>
      {pending[0] && status === "Live" && (
        <HaltModal
          key={pending[0].id}
          flow={pending[0]}
          count={pending.length}
        />
      )}
    </div>
  );
}
