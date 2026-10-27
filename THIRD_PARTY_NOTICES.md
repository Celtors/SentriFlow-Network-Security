# Third-party and data notices

Python and JavaScript dependencies retain their original licenses; inspect installed package metadata and `frontend/package-lock.json` when distributing a release. This file is not a completed distribution license audit.

The bundled runtime domain seed contains only demonstration domains: tracker.sentriflow.test, doubleclick.net and google-analytics.com. No full StevenBlack/EasyPrivacy dataset is bundled. The importer supports a documented subset and does not claim full Adblock syntax compatibility.

## Offline map data (R4)

- Country shapes: Natural Earth v5.1.2, public domain. Source: https://github.com/nvkelso/natural-earth-vector/tree/v5.1.2/geojson and terms: https://www.naturalearthdata.com/about/terms-of-use/. The bundled GeoJSON retains country code/name and rounds coordinates to three decimals. Natural Earth's boundary conventions are cartographic data, not claims by this project.
- Country estimates: DB-IP IP to Country Lite, October 2026 edition, CC BY 4.0. Source and terms: https://db-ip.com/db/download/ip-to-country-lite and https://creativecommons.org/licenses/by/4.0/. Attribution: **IP Geolocation by DB-IP**, https://db-ip.com. That link is displayed on the map page. Lite coverage/accuracy is limited. The MMDB is downloaded locally and ignored by Git; include this notice and attribution if packaging a build that contains it. No data changes are made to the downloaded MMDB.
- Download provenance, edition and SHA-256 hashes: `docs/map-data.json`. Manual preparation script: `scripts/prepare-map-data.py`. There are no automatic runtime downloads or external map tiles.
- Leaflet 1.9.4 uses the BSD-2-Clause license; see the installed package LICENSE. Mermaid (MIT) and Markdown-it (MIT) are isolated proposal-build tools under `docs/proposal/tools`; they are not dashboard runtime dependencies.

The scaffold's original asset files remain in the repository; the implemented dashboard does not load remote fonts, map tiles, telemetry or cloud model APIs. Third-party notices must be completed before external packaging/publication.
