import { useTrafficStore } from "../store/trafficStore";

export default function BlocklistPage() {
  const sources = useTrafficStore((state) => state.snapshot?.blocklist || []);
  return (
    <section className="panel">
      <h2>Local domain blocklists</h2>
      <p className="muted caption">
        The bundled seed demonstrates matching and is not a comprehensive
        tracker database. No feed is fetched automatically.
      </p>
      {sources.map((source) => (
        <div className="list-row" key={source.source}>
          <div>
            <strong>{source.source}</strong>
            <small>Domain and subdomain matching</small>
          </div>
          <span>{source.count} domains</span>
        </div>
      ))}
      <p className="muted caption">
        Import a reviewed local hosts/domain file using{" "}
        <code>python -m sentriflow run --import-blocklist PATH</code>. Simple
        ||domain^ rules are supported; unsupported Adblock modifiers are skipped
        and reported.
      </p>
    </section>
  );
}
