import { useState } from "react";
import { useTrafficStore } from "../store/trafficStore";
import type { WebsiteEvidence } from "../api/types";
import { bytes } from "../lib/format";

const evidenceLabels: Record<string, string> = {
  browser_information: "Browser & device headers",
  cookies: "Outgoing cookies",
  cookie_response: "Incoming cookie instructions",
  forms: "Forms on this page",
  permissions: "Camera, microphone & location",
  fingerprinting: "Fingerprinting & screen details",
  browser_storage: "Browser storage",
};
const states: Record<WebsiteEvidence["state"], string> = {
  not_observed: "Not observed",
  access_attempt: "Attempt observed",
  transmission_observed: "Transmission observed",
  collection_observed: "Response observed",
  structure_observed: "Structure observed",
  unavailable: "Cannot observe",
};

function percent(value: number) {
  if (value >= 99.95) return ">99.9";
  if (value < 0.05) return "<0.1";
  return value.toFixed(1);
}

export default function WebsitePanel({
  compact = false,
  onExpand,
  onSettings,
}: {
  compact?: boolean;
  onExpand?: () => void;
  onSettings: () => void;
}) {
  const { snapshot, status } = useTrafficStore();
  const [selectedId, setSelectedId] = useState("");
  const sites = snapshot?.websites ?? [];
  const visibleSelectedId = sites.some((s) => s.id === selectedId)
    ? selectedId
    : "";
  const site = sites.find(
    (s) => s.id === (visibleSelectedId || snapshot?.current_website_id),
  );
  const analysis = site?.analysis;
  const ready =
    analysis?.state === "ready" && analysis.maliciousness_percentage !== null;
  const risk = ready ? analysis.risk_level : "unknown";
  const model = snapshot?.website_model;
  const recommendations = {
    low: "Lower phishing risk. Still check the address before sharing personal information.",
    medium:
      "Be cautious. Verify who owns this site before signing in or paying.",
    high: "Avoid entering passwords or payment details until you verify this site.",
    unknown:
      "An estimate needs a visible public website address. Keep normal browsing precautions.",
  };
  return (
    <section
      className={compact ? "website-view compact-website" : "website-view"}
    >
      {!compact && (
        <div className="website-tools">
          <label>
            Observed website
            <select
              aria-label="Observed website"
              value={visibleSelectedId}
              onChange={(e) => setSelectedId(e.target.value)}
            >
              <option value="">Follow latest observed page</option>
              {sites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.host} · {s.process_name} ·{" "}
                  {new Date(s.first_seen).toLocaleTimeString()}
                </option>
              ))}
            </select>
          </label>
          <span className="muted">
            Live summaries stay in memory for this session.
          </span>
        </div>
      )}
      <div
        className={`website-risk-card risk-${risk}`}
        aria-live="polite"
        aria-busy={analysis?.state === "analyzing"}
      >
        <div className="risk-topline">
          <span className="eyebrow">YOUR BROWSING COMPANION</span>
          <span className={`risk-badge ${risk}`}>
            {ready ? `${risk} risk` : "Awaiting evidence"}
          </span>
        </div>
        <div className="website-address">
          <span className="site-symbol" aria-hidden="true">
            ↗
          </span>
          <div>
            <small className="muted">
              {site?.identified_by === "page_navigation"
                ? "Latest observed page"
                : "Observed destination"}
            </small>
            <h2 className="break">{site?.host ?? "Waiting for a website"}</h2>
          </div>
        </div>
        <div className="risk-reading">
          <strong data-testid="website-percentage">
            {ready ? percent(analysis.maliciousness_percentage!) : "—"}
            <span>{ready ? "%" : ""}</span>
          </strong>
          <div>
            <b>
              {analysis?.state === "analyzing"
                ? "Analyzing address…"
                : ready
                  ? "Estimated phishing likelihood"
                  : "No estimate yet"}
            </b>
            <small>
              {" "}
              {ready
                ? "From the trained model · processed locally"
                : status !== "Live"
                  ? "Reconnect to the local guardian"
                  : "Browse with traffic routed through SentriFlow"}
            </small>
          </div>
        </div>
        {ready && (
          <div
            className="risk-meter"
            role="meter"
            aria-label="Estimated phishing likelihood"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={analysis.maliciousness_percentage!}
          >
            <span style={{ width: `${analysis.maliciousness_percentage}%` }} />
          </div>
        )}
        <p className="risk-recommendation">{recommendations[risk]}</p>
        {ready && (
          <ul className="risk-reasons">
            {analysis.reasons.slice(0, 3).map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        )}
        {!ready && (
          <p className="muted risk-empty">
            {analysis?.reason ??
              (!model?.available && model?.reason
                ? model.reason
                : "Only traffic visible to this device's proxy can appear here. HTTPS needs the local certificate trusted by your browser.")}
          </p>
        )}
        <p className="risk-caveat">
          {ready
            ? "An address-based estimate, not a safety guarantee. Permissions and page behavior are separate evidence."
            : "Your focused browser tab cannot be identified from network traffic alone."}
        </p>
        {site && (
          <small className="muted">
            Observed {new Date(site.updated_at).toLocaleTimeString()} ·{" "}
            {site.process_name}
            {status !== "Live" ? " · Connection lost, result may be stale" : ""}
          </small>
        )}
        {compact && (
          <button className="primary expand-risk" onClick={onExpand}>
            Explore details <span aria-hidden="true">↗</span>
          </button>
        )}
      </div>
      {!site && (
        <div className="website-start">
          <strong>Make your browsing visible</strong>
          <p className="muted">
            Start the guardian, review browser routing and trust the local
            certificate in Settings. Apps that bypass the proxy cannot be
            monitored.
          </p>
          <button onClick={onSettings}>Review capture settings</button>
        </div>
      )}
      {!compact && site && (
        <>
          <div className="website-stats">
            <div>
              <strong>{site.requests}</strong>
              <span>Observed requests</span>
            </div>
            <div>
              <strong>{site.third_party_requests}</strong>
              <span>Related third-party requests</span>
            </div>
            <div>
              <strong>{site.blocked_requests}</strong>
              <span>Blocked by your controls</span>
            </div>
            <div>
              <strong>{bytes(site.bytes_down)}</strong>
              <span>Received payload</span>
            </div>
          </div>
          <section className="website-section">
            <div className="section-intro">
              <span className="eyebrow">WHAT WE CAN ACTUALLY SEE</span>
              <h2>Your data, with the evidence</h2>
              <p className="muted">
                An attempt is different from a completed transfer. A response
                does not prove that the recipient read or stored your data.
              </p>
            </div>
            <div className="evidence-grid">
              {Object.entries(site.evidence).map(([key, evidence]) => (
                <article className="evidence-card" key={key}>
                  <div>
                    <h3>{evidenceLabels[key] ?? key}</h3>
                    <span className={`evidence-state state-${evidence.state}`}>
                      {states[evidence.state]}
                    </span>
                  </div>
                  <p>{evidence.detail}</p>
                  {evidence.state === "structure_observed" && (
                    <dl className="form-facts">
                      <div>
                        <dt>Forms</dt>
                        <dd>{evidence.forms}</dd>
                      </div>
                      <div>
                        <dt>Password fields</dt>
                        <dd>{evidence.password_fields}</dd>
                      </div>
                      <div>
                        <dt>Email fields</dt>
                        <dd>{evidence.email_fields}</dd>
                      </div>
                    </dl>
                  )}
                  {evidence.partial && (
                    <small className="accent">
                      Partial HTML sample; additional forms may exist.
                    </small>
                  )}
                  {!!evidence.external_form_domains?.length && (
                    <p className="break">
                      External form destinations:{" "}
                      {evidence.external_form_domains.join(", ")}
                    </p>
                  )}
                </article>
              ))}
            </div>
          </section>
          <section className="website-section destinations">
            <h2>Other destinations</h2>
            <p className="muted">
              Related third-party requests use the page's referrer or origin,
              when present. A missing referrer limits attribution.
            </p>
            {site.external_domains.length ? (
              <ul>
                {site.external_domains.map((host) => (
                  <li key={host} className="break">
                    {host}
                  </li>
                ))}
              </ul>
            ) : (
              <p>
                No third-party destinations attributed to this page yet. This
                does not prove none were contacted.
              </p>
            )}
            <p className="muted">
              {site.redirects} redirects observed
              {site.redirect_domains.length
                ? ` · Destinations: ${site.redirect_domains.join(", ")}`
                : ""}
            </p>
          </section>
          <details className="website-section model-details">
            <summary>How this estimate is made</summary>
            <p>
              {analysis?.caution ??
                "No usable model result for this destination."}
            </p>
            <p className="muted">
              The model uses domain structure and the observed HTTP(S) scheme.
              It does not know domain age, reputation, malware content,
              passwords or browser permissions. HTTPS alone does not mean
              trustworthy.
            </p>
            <p className="muted">{analysis?.explanation_method}</p>
            {analysis?.features && (
              <dl className="feature-list">
                {Object.entries(analysis.features).map(([name, value]) => (
                  <div key={name}>
                    <dt>{name.replaceAll("_", " ")}</dt>
                    <dd>{Number(value.toFixed(3))}</dd>
                  </div>
                ))}
              </dl>
            )}
            <small className="muted">
              Model: {analysis?.model_id ?? "unavailable"} ·{" "}
              {model?.calibration ?? "No"} calibration on a separate
              reference-corpus split. Low &lt;30%, medium 30–70%, high ≥70%.
            </small>
          </details>
          <p className="muted association-note">
            {site.association_note} TLS status: {site.tls_status}. Website
            summaries are estimates and do not automatically block traffic.
          </p>
        </>
      )}
    </section>
  );
}
