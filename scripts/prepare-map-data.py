"""Explicit development-time downloads; the running application never fetches map data."""

import argparse
import gzip
import hashlib
import json
import re
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHAPES = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_110m_admin_0_countries.geojson"
)


def download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "SentriFlow-map-setup/0.1"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read(35_000_001)
    if len(data) > 35_000_000:
        raise ValueError("Download exceeds the expected country-data size")
    return data


def rounded(value):
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return round(value, 3) if isinstance(value, float) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--month", required=True, help="DB-IP edition, e.g. 2026-10")
    args = parser.parse_args()
    if not re.fullmatch(r"20\d{2}-(?:0[1-9]|1[0-2])", args.month):
        parser.error("Month must be YYYY-MM")
    original = download(SHAPES)
    source = json.loads(original)
    features = []
    for feature in source["features"]:
        props = feature["properties"]
        code = props.get("ISO_A2_EH") or props.get("ISO_A2")
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "code": code,
                    "name": props.get("NAME_EN") or props["ADMIN"],
                },
                "geometry": rounded(feature["geometry"]),
            }
        )
    target = ROOT / "frontend/public/geo/world-countries.geojson"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {"type": "FeatureCollection", "features": features}, separators=(",", ":")
        ),
        encoding="utf-8",
    )
    url = f"https://download.db-ip.com/free/dbip-country-lite-{args.month}.mmdb.gz"
    compressed = download(url)
    database = gzip.decompress(compressed)
    if len(database) > 40_000_000:
        raise ValueError("Decompressed database exceeds country-data bound")
    database_path = ROOT / "backend/src/sentriflow/data/geoip/dbip-country-lite.mmdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    import geoip2.database

    temporary = database_path.with_suffix(".download")
    try:
        temporary.write_bytes(database)
        with geoip2.database.Reader(str(temporary)) as reader:
            if "country" not in reader.metadata().database_type.lower():
                raise ValueError("Expected a country MMDB")
        temporary.replace(database_path)
    finally:
        temporary.unlink(missing_ok=True)
    manifest = {
        "retrieved_at": datetime.now(UTC).isoformat(),
        "shapes": {
            "source": SHAPES,
            "license": "Public domain (Natural Earth)",
            "changes": "Retained country code/name; rounded coordinates to 3 decimals",
            "upstream_sha256": hashlib.sha256(original).hexdigest(),
            "artifact_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "countries": len(features),
        },
        "geoip": {
            "source": url,
            "edition": args.month,
            "license": "CC BY 4.0",
            "attribution": "IP Geolocation by DB-IP",
            "url": "https://db-ip.com",
            "sha256": hashlib.sha256(database).hexdigest(),
            "bytes": len(database),
        },
    }
    (ROOT / "docs/map-data.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(
        f"Prepared {len(features)} country shapes and {len(database):,} bytes of local GeoIP data."
    )


if __name__ == "__main__":
    main()
