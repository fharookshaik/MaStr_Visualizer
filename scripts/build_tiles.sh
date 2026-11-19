#!/usr/bin/env bash
# MIT License
# Copyright (c) 2026 MaStR Visualizer contributors
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PARQUET="$ROOT/public/data/units.parquet"
OUTPUT="$ROOT/public/data/map.pmtiles"
TEMP_CSV="$(mktemp "${TMPDIR:-/tmp}/mastr-units.XXXXXX")"
TEMP_GEOJSON="$(mktemp "${TMPDIR:-/tmp}/mastr-units.XXXXXX")"
CLUSTER_CSV="$ROOT/public/data/map-clusters.csv"
CLUSTER_GEOJSON="$ROOT/public/data/map-clusters.geojson"
TEMP_DETAIL="$OUTPUT.detail.mbtiles"
TEMP_CLUSTERS="$OUTPUT.clusters.mbtiles"
TEMP_DETAIL_PM="$OUTPUT.detail.pmtiles"
TEMP_CLUSTER_PM="$OUTPUT.clusters.pmtiles"
TEMP_MERGED="$OUTPUT.merged.pmtiles"

cleanup() {
  rm -f "$TEMP_CSV" "$TEMP_GEOJSON" "$CLUSTER_CSV" "$CLUSTER_GEOJSON" \
    "$TEMP_DETAIL" "$TEMP_CLUSTERS" "$TEMP_DETAIL_PM" "$TEMP_CLUSTER_PM" "$TEMP_MERGED"
}
trap cleanup EXIT

if [[ ! -f "$PARQUET" ]]; then
  printf 'Missing %s; run uv run scripts/pipeline.py first.\n' "$PARQUET" >&2
  exit 1
fi

for tool in duckdb tippecanoe pmtiles; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    printf 'Required command not found: %s\n' "$tool" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$OUTPUT")"
duckdb -no-agent -c ".read scripts/build_clusters.sql"
duckdb -no-agent -c "COPY (SELECT mastr_id, tech_type, capacity_mw, status, lat, lon, municipality_name, state FROM '$PARQUET' WHERE lat IS NOT NULL AND lon IS NOT NULL) TO '$TEMP_CSV' (HEADER, DELIMITER ',');"
uv run "$ROOT/scripts/csv_to_geojson.py" "$TEMP_CSV" > "$TEMP_GEOJSON"
uv run "$ROOT/scripts/csv_to_geojson.py" "$CLUSTER_CSV" --lon-field grid_lon --lat-field grid_lat --properties unit_count,capacity_mw,tech_type,status,state > "$CLUSTER_GEOJSON"

# Detail points are read directly from the zoom-8+ PMTiles layer; only the
# pre-aggregated cluster cells are loaded client-side below zoom 8.
tippecanoe --quiet --output="$TEMP_DETAIL" --force --layer=units --drop-densest-as-needed --extend-zooms-if-still-dropping --minimum-zoom=8 --maximum-zoom=14 "$TEMP_GEOJSON"
tippecanoe --quiet --output="$TEMP_CLUSTERS" --force --layer=unit_clusters --no-feature-limit --minimum-zoom=0 --maximum-zoom=7 "$CLUSTER_GEOJSON"
pmtiles convert "$TEMP_DETAIL" "$TEMP_DETAIL_PM"
pmtiles convert "$TEMP_CLUSTERS" "$TEMP_CLUSTER_PM"
pmtiles merge "$TEMP_DETAIL_PM" "$TEMP_CLUSTER_PM" "$TEMP_MERGED"
mv "$TEMP_MERGED" "$OUTPUT"
pmtiles verify "$OUTPUT"
printf 'Wrote %s\n' "$OUTPUT"
