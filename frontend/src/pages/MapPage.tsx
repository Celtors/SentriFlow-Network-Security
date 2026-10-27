import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { GeoDestinations } from "../api/types";
import DestinationMap from "../components/map/DestinationMap";
import { bytes } from "../lib/format";

export default function MapPage() {
  const [data, setData] = useState<GeoDestinations | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const select = useCallback(
    (code: string) => setSelected((old) => (old === code ? null : code)),
    [],
  );
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const next = await api<GeoDestinations>("/geo/destinations");
        if (active) {
          setData(next);
          setError("");
        }
      } catch (reason) {
        if (active) setError((reason as Error).message);
      }
    };
    void refresh();
    const timer = setInterval(() => void refresh(), 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);
  const countries = data?.destinations || [];
  const visible = selected
    ? countries.filter((row) => row.country_code === selected)
    : countries;
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Destination countries</h2>
        <small className="muted">Offline · refreshes every 5 seconds</small>
      </div>
      <p className="muted caption">
        Country-level estimates from observed public destination IPs. A country
        is not the location of the person or company receiving your data.
      </p>
      {error && (
        <p role="alert" className="warning">
          {error} Previously loaded data may be stale.
        </p>
      )}
      {data && !data.available && (
        <p className="warning">
          {data.reason}. Install a local country database and restart the
          guardian to enable lookup.
        </p>
      )}
      <DestinationMap
        countries={countries}
        selected={selected}
        onSelect={select}
      />
      <div className="map-summary">
        <span>
          <i className="map-key" />
          Observed destination country
        </span>
        <span>
          {countries.length} countries · {data?.total_requests ?? 0} retained
          requests
        </span>
      </div>
      {data && (
        <p className="muted caption">
          Not plotted: {data.unknown.no_observed_ip} without an observed IP,{" "}
          {data.unknown.local_or_private_ip} local/private,{" "}
          {data.unknown.not_in_database} without a database match. Requests
          blocked before connecting may have no destination IP.
        </p>
      )}
      {selected && (
        <button className="text-button" onClick={() => setSelected(null)}>
          Clear country filter ({selected})
        </button>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>COUNTRY</th>
              <th>REQUESTS</th>
              <th>BLOCKED</th>
              <th>SENT / RECEIVED</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.country_code}>
                <td>
                  <button
                    className="text-button"
                    onClick={() => select(row.country_code)}
                  >
                    {row.country_name} ({row.country_code})
                  </button>
                </td>
                <td>{row.requests}</td>
                <td>{row.blocked}</td>
                <td>
                  {bytes(row.bytes_up)} / {bytes(row.bytes_down)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!visible.length && (
        <div className="empty">
          {selected
            ? "No captured requests mapped to this country."
            : "No public destination countries have been observed yet. Local demo traffic stays unplotted."}
        </div>
      )}
      <p className="map-credit">
        Country estimates:{" "}
        <a href="https://db-ip.com" target="_blank" rel="noreferrer">
          IP Geolocation by DB-IP
        </a>{" "}
        (CC BY 4.0). Map: Natural Earth, public domain. All lookups and map
        rendering happen on this device; no online tiles or IP lookup requests.
      </p>
    </section>
  );
}
