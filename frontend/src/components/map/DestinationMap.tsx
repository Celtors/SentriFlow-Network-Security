import { useEffect, useRef, useState } from "react";
import * as L from "leaflet";
import type { FeatureCollection, Geometry } from "geojson";
import type { GeoCountry } from "../../api/types";
import "leaflet/dist/leaflet.css";

type CountryShapes = FeatureCollection<
  Geometry,
  { code: string; name: string }
>;

export default function DestinationMap({
  countries,
  selected,
  onSelect,
}: {
  countries: GeoCountry[];
  selected: string | null;
  onSelect: (code: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [shapes, setShapes] = useState<CountryShapes | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const abort = new AbortController();
    fetch("/geo/world-countries.geojson", { signal: abort.signal })
      .then((response) => {
        if (!response.ok)
          throw new Error(
            "Country shapes are unavailable. Rebuild after preparing map data.",
          );
        return response.json();
      })
      .then(setShapes)
      .catch((reason) => {
        if (!abort.signal.aborted) setError(reason.message);
      });
    return () => abort.abort();
  }, []);
  const map = useRef<L.Map | null>(null);
  useEffect(() => {
    if (!container.current || !shapes) return;
    const instance = L.map(container.current, {
      scrollWheelZoom: false,
      minZoom: 1,
      maxZoom: 6,
      maxBounds: [
        [-85, -200],
        [85, 200],
      ],
      zoomControl: true,
    });
    map.current = instance;
    instance.fitBounds(
      [
        [-60, -180],
        [82, 180],
      ],
      { padding: [8, 8] },
    );
    instance.attributionControl.setPrefix(false);
    instance.attributionControl.addAttribution(
      'Made with <a href="https://www.naturalearthdata.com" target="_blank" rel="noreferrer">Natural Earth</a>',
    );
    const resize = new ResizeObserver(() => instance.invalidateSize());
    resize.observe(container.current);
    return () => {
      resize.disconnect();
      instance.remove();
      map.current = null;
    };
  }, [shapes]);
  useEffect(() => {
    if (!map.current || !shapes) return;
    const rows = new Map(
      countries.map((country) => [country.country_code, country]),
    );
    const layer = L.geoJSON(shapes, {
      style: (feature) => {
        const count = rows.get(feature?.properties.code)?.requests || 0;
        return {
          color: selected === feature?.properties.code ? "#fff" : "#5b5147",
          weight: selected === feature?.properties.code ? 2 : 0.7,
          fillColor: count ? "#ff8700" : "#282521",
          fillOpacity: count
            ? Math.min(0.95, 0.4 + Math.log10(count + 1) * 0.2)
            : 0.85,
        };
      },
      onEachFeature: (feature, countryLayer) => {
        const count = rows.get(feature.properties.code)?.requests || 0;
        const tooltip = document.createElement("span");
        tooltip.textContent = `${feature.properties.name}: ${count} captured requests`;
        countryLayer.bindTooltip(tooltip, { sticky: true });
        countryLayer.on("click", () => onSelect(feature.properties.code));
      },
    }).addTo(map.current);
    return () => {
      layer.remove();
    };
  }, [shapes, countries, selected, onSelect]);
  return (
    <>
      <div
        ref={container}
        className="destination-map"
        role="img"
        aria-label="Offline world map highlighting countries of observed destination IP addresses"
      />
      {error && (
        <p role="alert" className="warning">
          {error}
        </p>
      )}
      {!shapes && !error && (
        <p className="muted">Loading bundled country shapes…</p>
      )}
    </>
  );
}
